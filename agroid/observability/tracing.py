"""Trazabilidad con LangSmith y estado local del turno.

LangSmith aporta el árbol nativo (trace_id, run_id, parent_run_id). El estado
local agrega los IDs de correlación que se escriben en JSONL y SQLite, además
de los agregados de tokens, costo y latencia que usa el dashboard.
"""

from __future__ import annotations

import functools
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, TypeVar

from ..config import get_settings

try:  # LangSmith es opcional en tiempo de ejecución
    from langsmith import traceable as _langsmith_traceable
    from langsmith.run_helpers import get_current_run_tree
except ImportError:  # pragma: no cover
    _langsmith_traceable = None
    get_current_run_tree = None

T = TypeVar("T")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_trace_id() -> str:
    """32 caracteres hexadecimales, compatible con el formato de trace_id OTel."""
    return uuid.uuid4().hex


def new_span_id() -> str:
    """16 caracteres hexadecimales, compatible con span_id OTel."""
    return uuid.uuid4().hex[:16]


def configure_tracing() -> bool:
    return get_settings().configure_langsmith()


def current_run_info() -> dict[str, Any]:
    """IDs de la ejecución activa de LangSmith, si el trazado está habilitado."""
    if get_current_run_tree is None:
        return {}
    try:
        run = get_current_run_tree()
    except Exception:  # pragma: no cover - defensivo
        return {}
    if run is None:
        return {}
    parent = getattr(run, "parent_run_id", None)
    return {
        "langsmith_trace_id": str(getattr(run, "trace_id", "") or ""),
        "langsmith_run_id": str(getattr(run, "id", "") or ""),
        "langsmith_parent_run_id": str(parent) if parent else None,
    }


def traceable(*decorator_args: Any, **decorator_kwargs: Any):
    """``@traceable`` que se desactiva limpiamente si no hay LangSmith.

    Acepta tanto ``@traceable`` como ``@traceable(name=..., run_type=...)``.
    Cuando está deshabilitado, elimina ``langsmith_extra`` para que el código
    llamado no reciba un kwarg inesperado.
    """

    enabled = get_settings().langsmith_enabled

    def decorate(function: Callable[..., T]) -> Callable[..., T]:
        if _langsmith_traceable is not None and enabled:
            return _langsmith_traceable(*decorator_args, **decorator_kwargs)(
                function
            )

        @functools.wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            kwargs.pop("langsmith_extra", None)
            return function(*args, **kwargs)

        return wrapper

    if (
        len(decorator_args) == 1
        and callable(decorator_args[0])
        and not decorator_kwargs
    ):
        return decorate(decorator_args[0])
    return decorate


@dataclass
class LLMCall:
    span_id: str
    parent_span_id: str | None
    model_requested: str
    model_actual: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    cost_equivalent_usd: float
    latency_ms: float
    status: str = "success"
    ttft_ms: float | None = None
    tokens_per_second: float | None = None
    finish_reason: str = ""
    estimated_tokens: bool = False
    started_at: str = ""
    ended_at: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def row(self, trace_id: str) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": trace_id,
            "parent_span_id": self.parent_span_id,
            "model_requested": self.model_requested,
            "model_actual": self.model_actual,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "cost_equivalent_usd": self.cost_equivalent_usd,
            "latency_ms": self.latency_ms,
            "ttft_ms": self.ttft_ms,
            "tokens_per_second": self.tokens_per_second,
            "finish_reason": self.finish_reason,
            "status": self.status,
            "estimated_tokens": 1 if self.estimated_tokens else 0,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "attributes_json": _json(self.attributes),
        }


@dataclass
class ToolCall:
    span_id: str
    parent_span_id: str | None
    tool_name: str
    args: Any
    result_summary: str
    status: str
    duration_ms: float
    error_type: str = ""
    started_at: str = ""
    ended_at: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def row(self, trace_id: str) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": trace_id,
            "parent_span_id": self.parent_span_id,
            "tool_name": self.tool_name,
            "args_json": _json(self.args),
            "result_summary": self.result_summary,
            "status": self.status,
            "error_type": self.error_type,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "attributes_json": _json(self.attributes),
        }


@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    kind: str
    started_at: str
    ended_at: str
    duration_ms: float
    status: str = "success"
    attributes: dict[str, Any] = field(default_factory=dict)
    langsmith_run_id: str | None = None

    def row(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes_json": _json(self.attributes),
            "langsmith_run_id": self.langsmith_run_id,
        }


def _json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)


@dataclass
class TurnState:
    trace_id: str
    session_id: str
    turn_id: str
    mode: str = "react"
    category: str = ""
    experiment_group: str = ""
    consistency_group: str = ""
    run_id: str = ""
    started_at: str = field(default_factory=utc_now)
    start_perf: float = field(default_factory=perf_counter)
    root_span_id: str = field(default_factory=new_span_id)
    input_redacted: str = ""
    output_redacted: str = ""
    status: str = "running"
    error: str = ""
    error_type: str = ""
    iterations: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)
    llm_calls: list[LLMCall] = field(default_factory=list)
    spans: list[Span] = field(default_factory=list)
    span_ids: set[str] = field(default_factory=set)
    model_requested: str = ""
    model_actuals: set[str] = field(default_factory=set)
    security: dict[str, Any] = field(default_factory=dict)
    anomalies: dict[str, Any] = field(default_factory=dict)
    langsmith_trace_id: str = ""
    langsmith_run_id: str = ""
    langsmith_parent_run_id: str | None = None
    repeated_actions: list[str] = field(default_factory=list)
    loop_detected: bool = False
    _action_keys: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.span_ids.add(self.root_span_id)

    @property
    def prompt_tokens(self) -> int:
        return sum(call.prompt_tokens for call in self.llm_calls)

    @property
    def completion_tokens(self) -> int:
        return sum(call.completion_tokens for call in self.llm_calls)

    @property
    def total_tokens(self) -> int:
        return sum(call.total_tokens for call in self.llm_calls)

    @property
    def cost_usd(self) -> float:
        return round(sum(call.cost_usd for call in self.llm_calls), 8)

    @property
    def cost_equivalent_usd(self) -> float:
        return round(sum(call.cost_equivalent_usd for call in self.llm_calls), 8)

    @property
    def model_actual(self) -> str:
        return ", ".join(sorted(self.model_actuals))

    def duration_ms(self) -> float:
        return round((perf_counter() - self.start_perf) * 1000, 2)

    def add_llm(self, call: LLMCall) -> None:
        self.llm_calls.append(call)
        self.span_ids.add(call.span_id)
        if call.model_actual:
            self.model_actuals.add(call.model_actual)

    def add_tool(self, call: ToolCall) -> None:
        self.tool_calls.append(call)
        self.span_ids.add(call.span_id)

    def add_span(self, span: Span) -> None:
        self.spans.append(span)
        self.span_ids.add(span.span_id)

    def note_action(self, tool: str, tool_input: Any) -> bool:
        """Registra una acción ReAct y detecta repeticiones idénticas."""
        key = f"{tool}:{_json(tool_input)}"
        if key in self._action_keys:
            self.loop_detected = True
            self.repeated_actions.append(key)
            return True
        self._action_keys.add(key)
        return False

    def trace_row(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "started_at": self.started_at,
            "ended_at": utc_now() if self.status != "running" else None,
            "duration_ms": self.duration_ms(),
            "mode": self.mode,
            "category": self.category,
            "experiment_group": self.experiment_group,
            "consistency_group": self.consistency_group,
            "input_redacted": self.input_redacted,
            "output_redacted": self.output_redacted,
            "status": self.status,
            "error_type": self.error_type,
            "iterations": self.iterations,
            "tool_calls_json": _json(
                [
                    {
                        "tool": call.tool_name,
                        "status": call.status,
                        "duration_ms": call.duration_ms,
                    }
                    for call in self.tool_calls
                ]
            ),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "cost_equivalent_usd": self.cost_equivalent_usd,
            "model_requested": self.model_requested,
            "model_actual": self.model_actual,
            "langsmith_trace_id": self.langsmith_trace_id,
            "langsmith_run_id": self.langsmith_run_id,
            "security_json": _json(self.security),
            "anomalies_json": _json(self.anomalies),
        }


def start_turn(
    session_id: str,
    mode: str = "react",
    category: str = "",
    experiment_group: str = "",
    consistency_group: str = "",
    run_id: str = "",
    input_redacted: str = "",
    model_requested: str = "",
) -> TurnState:
    state = TurnState(
        trace_id=new_trace_id(),
        session_id=session_id,
        turn_id=uuid.uuid4().hex[:12],
        mode=mode,
        category=category,
        experiment_group=experiment_group,
        consistency_group=consistency_group,
        run_id=run_id,
        input_redacted=input_redacted,
        model_requested=model_requested,
    )
    root = Span(
        span_id=state.root_span_id,
        trace_id=state.trace_id,
        parent_span_id=None,
        name="chat",
        kind="chain",
        started_at=state.started_at,
        ended_at=state.started_at,
        duration_ms=0.0,
        status="running",
        attributes={"session_id": session_id, "mode": mode},
    )
    state.add_span(root)
    try:
        from . import store

        store.insert_span(root.row())
    except Exception:  # pragma: no cover - observabilidad defensiva
        pass
    return state


def finish_turn(
    state: TurnState,
    status: str,
    output: str = "",
    error: str = "",
    error_type: str = "",
) -> TurnState:
    state.status = status
    state.output_redacted = output or ""
    state.error = error or ""
    state.error_type = error_type or state.error_type
    ended = utc_now()
    duration = state.duration_ms()
    for span in state.spans:
        if span.span_id == state.root_span_id:
            span.ended_at = ended
            span.duration_ms = duration
            span.status = status
            try:
                from . import store

                store.insert_span(span.row())
            except Exception:  # pragma: no cover
                pass
            break
    return state


def record_span(
    state: TurnState | None,
    name: str,
    kind: str,
    started_at: str,
    ended_at: str,
    duration_ms: float,
    parent_span_id: str | None = None,
    status: str = "success",
    attributes: dict[str, Any] | None = None,
    langsmith_run_id: str | None = None,
    span_id: str | None = None,
    allow_external_parent: bool = False,
) -> Span | None:
    if state is None:
        return None
    parent = parent_span_id
    if parent is None:
        parent = state.root_span_id
    if parent not in state.span_ids and not allow_external_parent:
        parent = state.root_span_id
    span = Span(
        span_id=span_id or new_span_id(),
        trace_id=state.trace_id,
        parent_span_id=parent,
        name=name,
        kind=kind,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=round(duration_ms, 2),
        status=status,
        attributes=attributes or {},
        langsmith_run_id=langsmith_run_id,
    )
    state.add_span(span)
    try:
        from . import store

        store.insert_span(span.row())
    except Exception:  # pragma: no cover - la observabilidad nunca debe romper el agente
        pass
    return span


def annotate_langsmith(state: TurnState) -> None:
    info = current_run_info()
    if info:
        state.langsmith_trace_id = info.get("langsmith_trace_id", "") or ""
        state.langsmith_run_id = info.get("langsmith_run_id", "") or ""
        state.langsmith_parent_run_id = info.get("langsmith_parent_run_id")
