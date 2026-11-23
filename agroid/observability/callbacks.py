"""Callback de LangChain que alimenta logs JSON, SQLite y métricas.

Captura llamadas LLM, herramientas y acciones ReAct. LangSmith aporta el árbol
completo; este callback produce los agregados que el dashboard necesita y
detecta repeticiones de acciones (posibles bucles).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from ..config import get_settings
from ..security.pii import redact
from . import store
from .logging import get_logger, truncate
from .tracing import (
    LLMCall,
    ToolCall,
    TurnState,
    record_span,
    utc_now,
)


def _preview(value: Any, limit: int = 500) -> str:
    return truncate(redact(str(value)).text, limit)


def _text_from_response(response: Any) -> str:
    try:
        generation = response.generations[0][0]
        message = getattr(generation, "message", None)
        if message is not None and getattr(message, "content", None):
            content = message.content
            if isinstance(content, list):
                return " ".join(
                    str(part.get("text", part))
                    if isinstance(part, dict)
                    else str(part)
                    for part in content
                )
            return str(content)
        return str(getattr(generation, "text", "") or "")
    except Exception:  # pragma: no cover - defensivo
        return ""


def _usage_from_response(
    response: Any, prompt_chars: int, output_text: str
) -> dict[str, Any]:
    prompt = completion = total = None
    finish_reason = ""
    model_actual = ""

    llm_output = getattr(response, "llm_output", None) or {}
    for key in ("token_usage", "usage", "usage_metadata"):
        value = llm_output.get(key)
        if isinstance(value, dict):
            prompt = prompt or value.get("prompt_tokens") or value.get("input_tokens")
            completion = completion or value.get(
                "completion_tokens"
            ) or value.get("output_tokens")
            total = total or value.get("total_tokens")
    model_actual = (
        llm_output.get("model_name")
        or llm_output.get("model")
        or llm_output.get("model_id")
        or ""
    )

    try:
        generation = response.generations[0][0]
        message = getattr(generation, "message", None)
        if message is not None:
            metadata = getattr(message, "response_metadata", {}) or {}
            usage = getattr(message, "usage_metadata", None) or {}
            if isinstance(usage, dict):
                prompt = prompt or usage.get("input_tokens")
                completion = completion or usage.get("output_tokens")
                total = total or usage.get("total_tokens")
            model_actual = (
                model_actual
                or metadata.get("model_name")
                or metadata.get("model")
                or metadata.get("model_id")
                or ""
            )
            finish_reason = (
                metadata.get("finish_reason")
                or metadata.get("stop_reason")
                or finish_reason
            )
        generation_info = getattr(generation, "generation_info", None) or {}
        finish_reason = finish_reason or generation_info.get(
            "finish_reason", ""
        )
    except Exception:  # pragma: no cover - defensivo
        pass

    estimated = False
    if prompt is None:
        prompt = max(1, prompt_chars // 4)
        estimated = True
    if completion is None:
        completion = max(1, len(output_text) // 4)
        estimated = True
    if total is None:
        total = int(prompt or 0) + int(completion or 0)

    return {
        "prompt_tokens": int(prompt or 0),
        "completion_tokens": int(completion or 0),
        "total_tokens": int(total or 0),
        "model_actual": model_actual,
        "finish_reason": finish_reason,
        "estimated": estimated,
    }


class AgroidCallbackHandler(BaseCallbackHandler):
    """Callback por turno. No debe lanzar excepciones hacia LangChain."""

    ignore_chain = True
    ignore_retriever = False

    def __init__(self, state: TurnState) -> None:
        self.state = state
        self.settings = get_settings()
        self.logger = get_logger()
        self.llm_requests = 0
        self._llm_start: dict[str, tuple[float, str, int]] = {}
        self._tool_start: dict[str, tuple[float, str, str, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        tags: Any = None,
        metadata: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            prompt_chars = 0
            for message in messages or []:
                for item in message if isinstance(message, list) else [message]:
                    prompt_chars += len(str(getattr(item, "content", item)))
            with self._lock:
                self._llm_start[str(run_id)] = (
                    perf_counter(),
                    utc_now(),
                    prompt_chars,
                )
                self.llm_requests += 1
        except Exception:  # pragma: no cover
            pass

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        tags: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            run_key = str(run_id)
            start_perf, started_at, prompt_chars = self._llm_start.pop(
                run_key, (perf_counter(), utc_now(), 0)
            )
            latency_ms = round((perf_counter() - start_perf) * 1000, 2)
            output_text = _text_from_response(response)
            usage = _usage_from_response(response, prompt_chars, output_text)
            model_actual = usage["model_actual"] or self.state.model_requested
            cost = self.settings.cost_for(
                model_actual,
                usage["prompt_tokens"],
                usage["completion_tokens"],
            )
            tokens_per_second = (
                round(usage["completion_tokens"] / (latency_ms / 1000), 2)
                if latency_ms > 0
                else None
            )
            parent = (
                str(parent_run_id)
                if parent_run_id and str(parent_run_id) in self.state.span_ids
                else self.state.root_span_id
            )
            call = LLMCall(
                span_id=run_key,
                parent_span_id=parent,
                model_requested=self.state.model_requested,
                model_actual=model_actual,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
                cost_usd=float(cost["cost_usd"]),
                cost_equivalent_usd=float(cost["cost_equivalent_usd"]),
                latency_ms=latency_ms,
                status="success",
                finish_reason=usage["finish_reason"],
                estimated_tokens=bool(usage["estimated"]),
                started_at=started_at,
                ended_at=utc_now(),
                attributes={
                    "completion_preview": _preview(output_text),
                    "prompt_chars": prompt_chars,
                    "cost_estimated": cost["cost_estimated"],
                    "reference_model": cost["reference_model"],
                },
            )
            self.state.add_llm(call)
            store.insert_llm_call(call.row(self.state.trace_id))
            record_span(
                self.state,
                name=f"llm.{model_actual}",
                kind="llm",
                started_at=started_at,
                ended_at=call.ended_at,
                duration_ms=latency_ms,
                parent_span_id=parent,
                status="success",
                attributes={
                    "model_actual": model_actual,
                    "prompt_tokens": usage["prompt_tokens"],
                    "completion_tokens": usage["completion_tokens"],
                    "estimated_tokens": usage["estimated"],
                },
                langsmith_run_id=run_key,
                span_id=run_key,
            )
            self.logger.log(
                "llm.call",
                trace_id=self.state.trace_id,
                session_id=self.state.session_id,
                langsmith_trace_id=self.state.langsmith_trace_id,
                span_id=run_key,
                parent_span_id=parent,
                model_requested=self.state.model_requested,
                model_actual=model_actual,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
                total_tokens=usage["total_tokens"],
                cost_usd=cost["cost_usd"],
                cost_equivalent_usd=cost["cost_equivalent_usd"],
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second,
                estimated_tokens=usage["estimated"],
                status="success",
            )
        except Exception as exc:  # pragma: no cover - observabilidad defensiva
            try:
                self.logger.log(
                    "llm.call.error",
                    level="ERROR",
                    trace_id=self.state.trace_id,
                    error=f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        tags: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            run_key = str(run_id)
            start_perf, started_at, _ = self._llm_start.pop(
                run_key, (perf_counter(), utc_now(), 0)
            )
            latency_ms = round((perf_counter() - start_perf) * 1000, 2)
            parent = (
                str(parent_run_id)
                if parent_run_id and str(parent_run_id) in self.state.span_ids
                else self.state.root_span_id
            )
            record_span(
                self.state,
                name="llm.error",
                kind="llm",
                started_at=started_at,
                ended_at=utc_now(),
                duration_ms=latency_ms,
                parent_span_id=parent,
                status="error",
                attributes={
                    "error": f"{type(error).__name__}: {error}",
                },
                langsmith_run_id=run_key,
                span_id=run_key,
            )
            self.state.error_type = type(error).__name__
            self.logger.log(
                "llm.error",
                level="ERROR",
                trace_id=self.state.trace_id,
                session_id=self.state.session_id,
                span_id=run_key,
                error=f"{type(error).__name__}: {error}",
                latency_ms=latency_ms,
            )
        except Exception:  # pragma: no cover
            pass

    # ------------------------------------------------------------------
    # Herramientas
    # ------------------------------------------------------------------
    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        inputs: dict[str, Any] | None = None,
        tags: Any = None,
        metadata: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            name = (
                (serialized or {}).get("name")
                or kwargs.get("name")
                or "herramienta"
            )
            args = inputs if inputs is not None else input_str
            with self._lock:
                self._tool_start[str(run_id)] = (
                    perf_counter(),
                    utc_now(),
                    str(name),
                    args,
                )
        except Exception:  # pragma: no cover
            pass

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        tags: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            run_key = str(run_id)
            start_perf, started_at, name, args = self._tool_start.pop(
                run_key, (perf_counter(), utc_now(), "herramienta", None)
            )
            duration_ms = round((perf_counter() - start_perf) * 1000, 2)
            text = str(output)
            status = (
                "error"
                if text.strip().lower().startswith(("error", "⚠"))
                else "success"
            )
            parent = (
                str(parent_run_id)
                if parent_run_id and str(parent_run_id) in self.state.span_ids
                else self.state.root_span_id
            )
            call = ToolCall(
                span_id=run_key,
                parent_span_id=parent,
                tool_name=name,
                args=args,
                result_summary=_preview(text, 800),
                status=status,
                duration_ms=duration_ms,
                started_at=started_at,
                ended_at=utc_now(),
                attributes={"result_chars": len(text)},
            )
            self.state.add_tool(call)
            store.insert_tool_call(call.row(self.state.trace_id))
            record_span(
                self.state,
                name=f"tool.{name}",
                kind="tool",
                started_at=started_at,
                ended_at=call.ended_at,
                duration_ms=duration_ms,
                parent_span_id=parent,
                status=status,
                attributes={"tool": name, "result_chars": len(text)},
                langsmith_run_id=run_key,
                span_id=run_key,
            )
            self.logger.log(
                "tool.call",
                trace_id=self.state.trace_id,
                session_id=self.state.session_id,
                span_id=run_key,
                parent_span_id=parent,
                tool=name,
                args=_preview(args),
                result=_preview(text, 300),
                status=status,
                duration_ms=duration_ms,
            )
        except Exception:  # pragma: no cover
            pass

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        tags: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            run_key = str(run_id)
            start_perf, started_at, name, args = self._tool_start.pop(
                run_key, (perf_counter(), utc_now(), "herramienta", None)
            )
            duration_ms = round((perf_counter() - start_perf) * 1000, 2)
            parent = (
                str(parent_run_id)
                if parent_run_id and str(parent_run_id) in self.state.span_ids
                else self.state.root_span_id
            )
            call = ToolCall(
                span_id=run_key,
                parent_span_id=parent,
                tool_name=name,
                args=args,
                result_summary=f"{type(error).__name__}: {error}",
                status="error",
                duration_ms=duration_ms,
                error_type=type(error).__name__,
                started_at=started_at,
                ended_at=utc_now(),
            )
            self.state.add_tool(call)
            store.insert_tool_call(call.row(self.state.trace_id))
            record_span(
                self.state,
                name=f"tool.{name}.error",
                kind="tool",
                started_at=started_at,
                ended_at=call.ended_at,
                duration_ms=duration_ms,
                parent_span_id=parent,
                status="error",
                attributes={"tool": name, "error": str(error)},
                langsmith_run_id=run_key,
                span_id=run_key,
            )
            self.logger.log(
                "tool.error",
                level="ERROR",
                trace_id=self.state.trace_id,
                session_id=self.state.session_id,
                tool=name,
                error=f"{type(error).__name__}: {error}",
                duration_ms=duration_ms,
            )
        except Exception:  # pragma: no cover
            pass

    # ------------------------------------------------------------------
    # Agente
    # ------------------------------------------------------------------
    def on_agent_action(
        self,
        action: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            self.state.iterations += 1
            repeated = self.state.note_action(
                getattr(action, "tool", ""), getattr(action, "tool_input", {})
            )
            self.logger.log(
                "agent.action",
                trace_id=self.state.trace_id,
                session_id=self.state.session_id,
                iteration=self.state.iterations,
                tool=getattr(action, "tool", ""),
                tool_input=_preview(getattr(action, "tool_input", {})),
                repeated=repeated,
            )
        except Exception:  # pragma: no cover
            pass

    def on_agent_finish(
        self,
        finish: Any,
        *,
        run_id: Any,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        try:
            output = ""
            if hasattr(finish, "return_values"):
                output = str(finish.return_values.get("output", ""))
            self.logger.log(
                "agent.finish",
                trace_id=self.state.trace_id,
                session_id=self.state.session_id,
                iterations=self.state.iterations,
                output_preview=_preview(output),
            )
        except Exception:  # pragma: no cover
            pass
