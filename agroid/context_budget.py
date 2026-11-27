"""Control de contexto y presupuesto de tokens.

El objetivo es que el agente no dependa de que el prompt "quepa": se calcula un
presupuesto aproximado, se recorta el historial y se seleccionan fragmentos
recuperados antes de construir la entrada. La estimación es deliberadamente
simple (caracteres / 4) porque no todos los proveedores entregan un tokenizador
local; se usa como cota operativa, no como facturación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .config import get_settings


def estimate_tokens(text: Any) -> int:
    """Estimación conservadora de tokens para español e inglés."""
    value = str(text or "")
    if not value:
        return 0
    return max(1, (len(value) + 3) // 4)


def estimate_messages_tokens(messages: Iterable[Any]) -> int:
    total = 0
    for message in messages or []:
        content = getattr(message, "content", message)
        total += estimate_tokens(content) + 4  # rol y delimitadores
    return total


def trim_text(text: Any, max_chars: int, marker: str = "…") -> str:
    value = str(text or "")
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    if max_chars <= len(marker):
        return value[:max_chars]
    return value[: max_chars - len(marker)] + marker


def trim_messages(
    messages: Iterable[Any],
    max_tokens: int,
    min_keep: int = 2,
) -> list[Any]:
    """Conserva los mensajes más recientes que caben en el presupuesto.

    ``min_keep`` evita dejar el historial vacío cuando el último mensaje ya
    supera el presupuesto; en ese caso se conserva igual y el llamador decide
    si recorta el texto.
    """
    items = list(messages or [])
    if not items or max_tokens <= 0:
        return []
    kept: list[Any] = []
    used = 0
    for message in reversed(items):
        content = getattr(message, "content", message)
        cost = estimate_tokens(content) + 4
        if kept and used + cost > max_tokens:
            break
        kept.append(message)
        used += cost
    kept.reverse()
    if len(kept) < min_keep:
        kept = items[-min_keep:]
    return kept


@dataclass
class ContextBudget:
    """Límites de contexto de un turno."""

    max_history_tokens: int = 1400
    max_input_chars: int = 2000
    max_output_tokens: int = 800
    max_context_chars: int = 3000
    max_context_items: int = 3
    reserved_tokens: int = 300
    report: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_settings(cls) -> "ContextBudget":
        settings = get_settings()
        return cls(
            max_input_chars=settings.max_input_chars,
            max_output_tokens=settings.max_output_tokens,
        )

    def prepare_input(self, text: str) -> str:
        trimmed = trim_text(text, self.max_input_chars)
        self.report["input_chars"] = len(str(text or ""))
        self.report["input_chars_used"] = len(trimmed)
        self.report["input_tokens_est"] = estimate_tokens(trimmed)
        return trimmed

    def prepare_history(self, messages: Iterable[Any]) -> list[Any]:
        original = list(messages or [])
        trimmed = trim_messages(original, self.max_history_tokens)
        self.report["history_messages_total"] = len(original)
        self.report["history_messages_used"] = len(trimmed)
        self.report["history_tokens_est"] = estimate_messages_tokens(trimmed)
        self.report["history_trimmed"] = len(trimmed) < len(original)
        return trimmed

    def prepare_hits(self, hits: Iterable[Any]) -> list[Any]:
        selected: list[Any] = []
        chars = 0
        for hit in hits or []:
            text = getattr(hit, "texto", None)
            if text is None and isinstance(hit, dict):
                text = hit.get("texto", "")
            text = str(text or "")
            if len(selected) >= self.max_context_items:
                break
            if selected and chars + len(text) > self.max_context_chars:
                continue
            selected.append(hit)
            chars += len(text)
        self.report["context_items"] = len(selected)
        self.report["context_chars"] = chars
        self.report["context_tokens_est"] = estimate_tokens(" ".join(
            str(getattr(hit, "texto", "")) for hit in selected
        ))
        return selected

    def total_tokens_est(self) -> int:
        return int(
            self.report.get("input_tokens_est", 0)
            + self.report.get("history_tokens_est", 0)
            + self.report.get("context_tokens_est", 0)
            + self.reserved_tokens
        )

    def as_dict(self) -> dict[str, Any]:
        data = dict(self.report)
        data.update(
            {
                "max_history_tokens": self.max_history_tokens,
                "max_input_chars": self.max_input_chars,
                "max_output_tokens": self.max_output_tokens,
                "max_context_chars": self.max_context_chars,
                "total_tokens_est": self.total_tokens_est(),
            }
        )
        return data


def build_context(
    query: str,
    hits: Iterable[Any],
    budget: ContextBudget | None = None,
) -> tuple[str, ContextBudget]:
    """Construye un bloque de contexto citado y devuelve el presupuesto usado."""
    budget = budget or ContextBudget.from_settings()
    selected = budget.prepare_hits(hits)
    lines = [f"Consulta: {trim_text(query, 500)}", "Fragmentos:"]
    for hit in selected:
        source = getattr(hit, "fragment_id", None) or (
            hit.get("id", "") if isinstance(hit, dict) else ""
        )
        text = getattr(hit, "texto", None) or (
            hit.get("texto", "") if isinstance(hit, dict) else ""
        )
        source_type = getattr(hit, "source_type", None) or (
            hit.get("source_type", "interno") if isinstance(hit, dict) else "interno"
        )
        title = getattr(hit, "title", "") or (
            hit.get("title", "") if isinstance(hit, dict) else ""
        )
        suffix = f" — {title}" if title else ""
        lines.append(f"[{source}] ({source_type}){suffix}\n{text}")
    return "\n\n".join(lines), budget
