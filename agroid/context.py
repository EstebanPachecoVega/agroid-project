"""Contexto por turno y por sesión.

Se usan ``contextvars`` en lugar de variables globales para que dos sesiones
puedan ejecutarse en hilos distintos sin mezclar memoria ni datos recordados.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

CURRENT_SESSION: ContextVar[str] = ContextVar("agroid_session", default="demo")
CURRENT_TURN_STATE: ContextVar[Any] = ContextVar("agroid_turn_state", default=None)
CURRENT_CALLBACKS: ContextVar[Any] = ContextVar("agroid_callbacks", default=None)
CURRENT_LLM: ContextVar[Any] = ContextVar("agroid_llm", default=None)
CURRENT_TOOL_CONTEXT: ContextVar[Any] = ContextVar(
    "agroid_tool_context", default=None
)


@dataclass
class ToolContext:
    """Límites y contadores de herramientas dentro de un turno."""

    session_id: str = "demo"
    trace_id: str = ""
    max_writes: int = 3
    writes: int = 0
    blocked: bool = False
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def guard_write(self, tool_name: str) -> str | None:
        """Devuelve un mensaje de error si se superó el límite de escrituras.

        No incrementa el contador: eso ocurre en :meth:`confirm_write` solo
        cuando la escritura se ejecuta realmente.
        """
        if self.writes >= self.max_writes:
            self.blocked = True
            return (
                f"Error: límite de {self.max_writes} escrituras por turno "
                f"alcanzado. No se ejecutó {tool_name}. Divide la solicitud "
                "en varios turnos."
            )
        return None

    def confirm_write(self) -> None:
        self.writes += 1

    def record(self, tool_name: str, args: Any, status: str) -> None:
        self.tool_calls.append(
            {"tool": tool_name, "args": args, "status": status}
        )


def get_session_id() -> str:
    return CURRENT_SESSION.get()


def set_session_id(session_id: str) -> Token[str]:
    return CURRENT_SESSION.set(session_id or "demo")


def get_turn_state() -> Any:
    return CURRENT_TURN_STATE.get()


def set_turn_state(state: Any) -> Token[Any]:
    return CURRENT_TURN_STATE.set(state)


def get_callbacks() -> Any:
    return CURRENT_CALLBACKS.get()


def set_callbacks(callbacks: Any) -> Token[Any]:
    return CURRENT_CALLBACKS.set(callbacks)


def get_llm() -> Any:
    return CURRENT_LLM.get()


def set_llm(llm: Any) -> Token[Any]:
    return CURRENT_LLM.set(llm)


def get_tool_context() -> ToolContext:
    ctx = CURRENT_TOOL_CONTEXT.get()
    if ctx is None:
        ctx = ToolContext(session_id=get_session_id())
        CURRENT_TOOL_CONTEXT.set(ctx)
    return ctx


def set_tool_context(ctx: ToolContext) -> Token[Any]:
    return CURRENT_TOOL_CONTEXT.set(ctx)


def reset_token(var: ContextVar[Any], token: Token[Any]) -> None:
    try:
        var.reset(token)
    except (ValueError, LookupError):  # pragma: no cover - contexto ya cerrado
        pass
