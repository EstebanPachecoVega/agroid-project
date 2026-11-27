"""Memoria de sesión con ventana corta y resumen rodante.

La memoria corta conserva los últimos turnos; la memoria larga vive en SQLite
(``historial`` y ``datos``). Para flujos prolongados se agrega un resumen
extractivo en ``memoria_resumen`` que se inyecta en el prompt y evita perder
decisiones antiguas cuando la ventana se recorta.

No usa ``ConversationBufferWindowMemory`` (obsoleta en LangChain 1.x). La
interfaz ``load_memory_variables``/``save_context`` se mantiene para que el
agente y los tests existentes sigan funcionando.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from .context_budget import ContextBudget, estimate_tokens, trim_text
from .db import sql


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionMemory:
    """Memoria por ``session_id`` respaldada por SQLite."""

    def __init__(
        self,
        session_id: str,
        window: int = 5,
        max_history_tokens: int = 1400,
        summary_every: int = 6,
    ) -> None:
        self.session_id = session_id or "demo"
        self.window = max(1, int(window))
        self.max_history_tokens = max(200, int(max_history_tokens))
        self.summary_every = max(2, int(summary_every))
        self._messages: list[BaseMessage] | None = None
        self._summary: str | None = None
        self._lock = threading.Lock()
        self.last_context: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------
    def _load_messages(self) -> list[BaseMessage]:
        try:
            rows = sql(
                "SELECT rol, contenido FROM historial WHERE session_id=? "
                "ORDER BY id DESC LIMIT ?",
                (self.session_id, self.window * 2),
            )[::-1]
        except Exception:
            rows = []
        messages: list[BaseMessage] = []
        for row in rows:
            content = str(row.get("contenido", ""))
            if row.get("rol") == "humano":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        return messages

    def messages(self) -> list[BaseMessage]:
        if self._messages is None:
            self._messages = self._load_messages()
        budget = ContextBudget(max_history_tokens=self.max_history_tokens)
        trimmed = budget.prepare_history(self._messages)
        self.last_context = budget.as_dict()
        return trimmed

    def load_memory_variables(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"chat_history": self.messages()}

    def save_context(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
    ) -> None:
        """Actualiza la ventana en RAM; la persistencia la hace ``_save_turn``."""
        with self._lock:
            if self._messages is None:
                self._messages = self._load_messages()
            user = str(inputs.get("input", ""))
            assistant = str(outputs.get("output", ""))
            if user:
                self._messages.append(HumanMessage(content=user))
            if assistant:
                self._messages.append(AIMessage(content=assistant))
            self._messages = self._messages[-self.window * 2 :]

    # ------------------------------------------------------------------
    # Resumen
    # ------------------------------------------------------------------
    def _read_summary(self) -> str:
        try:
            rows = sql(
                "SELECT resumen FROM memoria_resumen WHERE session_id=?",
                (self.session_id,),
            )
        except Exception:
            rows = []
        return str(rows[0]["resumen"]) if rows else ""

    def _build_summary(self) -> str:
        try:
            rows = sql(
                "SELECT rol, contenido FROM historial WHERE session_id=? "
                "ORDER BY id DESC LIMIT ?",
                (self.session_id, max(12, self.window * 4)),
            )[::-1]
        except Exception:
            rows = []
        if not rows:
            return ""
        keywords = (
            "pedido",
            "stock",
            "déficit",
            "deficit",
            "producción",
            "produccion",
            "despach",
            "recordar",
            "recuerda",
            "cliente",
            "solo acepta",
            "prefiere",
            "no puedo",
            "error",
            "prioriza",
        )
        parts: list[str] = []
        for row in rows:
            text = " ".join(str(row.get("contenido", "")).split())
            if not text:
                continue
            lower = text.lower()
            if row.get("rol") == "humano":
                parts.append(f"U: {trim_text(text, 180)}")
            elif any(word in lower for word in keywords):
                parts.append(f"A: {trim_text(text, 180)}")
        # Prioriza los últimos hechos y limita el tamaño del resumen.
        summary = " | ".join(parts[-12:])
        summary = trim_text(summary, 900)
        if summary:
            sql(
                "INSERT OR REPLACE INTO memoria_resumen "
                "(session_id, resumen, updated_at, turnos) VALUES (?,?,?,?)",
                (self.session_id, summary, _now(), len(rows) // 2),
                escribir=True,
            )
        return summary

    def summary(self) -> str:
        if self._summary is None:
            self._summary = self._read_summary() or self._build_summary()
        return self._summary

    def maybe_update_summary(self) -> str:
        try:
            rows = sql(
                "SELECT COUNT(*) AS n FROM historial WHERE session_id=?",
                (self.session_id,),
            )
            turns = int(rows[0]["n"]) // 2 if rows else 0
        except Exception:
            turns = 0
        if turns >= self.summary_every and turns % self.summary_every == 0:
            self._summary = self._build_summary()
        return self.summary()

    def refresh(self) -> None:
        self._messages = None
        self._summary = None

    # ------------------------------------------------------------------
    # Diagnóstico
    # ------------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        messages = self.messages()
        summary = self.summary()
        return {
            "session_id": self.session_id,
            "window": self.window,
            "messages_in_window": len(messages),
            "summary_chars": len(summary),
            "summary_tokens_est": estimate_tokens(summary),
            "summary_preview": trim_text(summary, 240),
            "context": self.last_context,
        }


_MEMORIAS: dict[str, SessionMemory] = {}
_MEM_LOCK = threading.Lock()


def get_session_memory(session_id: str) -> SessionMemory:
    with _MEM_LOCK:
        memory = _MEMORIAS.get(session_id)
    if memory is None:
        memory = SessionMemory(session_id)
        with _MEM_LOCK:
            _MEMORIAS[session_id] = memory
    return memory


def reset_session_memories() -> None:
    with _MEM_LOCK:
        _MEMORIAS.clear()


def cached_sessions() -> int:
    with _MEM_LOCK:
        return len(_MEMORIAS)
