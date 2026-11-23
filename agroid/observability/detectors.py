"""Detección de anomalías típicas de agentes probabilísticos.

No reemplaza la revisión humana: produce señales para el dashboard y para el
informe (bucles, saturación de iteraciones, deriva de contexto, cuellos de
botella y cambios de modelo).
"""

from __future__ import annotations

from typing import Any

from .tracing import TurnState


def detect_anomalies(
    state: TurnState,
    max_iterations: int = 8,
    slow_tool_ms: float = 2000.0,
    slow_retriever_ms: float = 1000.0,
    slow_llm_ms: float = 30000.0,
) -> dict[str, Any]:
    flags: dict[str, Any] = {
        "loop": bool(state.loop_detected),
        "max_iterations": state.iterations >= max_iterations,
        "model_switch": len(state.model_actuals) > 1,
        "tool_error": any(
            call.status == "error" for call in state.tool_calls
        ),
        "llm_error": any(call.status == "error" for call in state.llm_calls),
        "empty_output": not bool((state.output_redacted or "").strip()),
    }

    details: dict[str, Any] = {
        "iterations": state.iterations,
        "models": sorted(state.model_actuals),
        "repeated_actions": list(state.repeated_actions),
    }

    # Deriva de contexto: el prompt crece mucho entre la primera y la última
    # llamada del mismo turno sin que medie una ventana nueva de memoria.
    if len(state.llm_calls) >= 2:
        first = state.llm_calls[0].prompt_tokens
        last = state.llm_calls[-1].prompt_tokens
        threshold = max(first * 1.5, first + 500)
        flags["context_drift"] = last > threshold
        details["prompt_tokens_first"] = first
        details["prompt_tokens_last"] = last
        details["prompt_growth_ratio"] = round(last / max(1, first), 2)
    else:
        flags["context_drift"] = False

    slow_tools = [
        {
            "tool": call.tool_name,
            "duration_ms": call.duration_ms,
            "status": call.status,
        }
        for call in state.tool_calls
        if call.duration_ms >= slow_tool_ms
    ]
    slow_spans = [
        {
            "name": span.name,
            "kind": span.kind,
            "duration_ms": span.duration_ms,
        }
        for span in state.spans
        if (
            (span.kind == "retriever" and span.duration_ms >= slow_retriever_ms)
            or (span.kind == "llm" and span.duration_ms >= slow_llm_ms)
        )
    ]
    flags["slow_tool"] = bool(slow_tools)
    flags["slow_span"] = bool(slow_spans)
    details["slow_tools"] = slow_tools
    details["slow_spans"] = slow_spans

    if state.spans:
        bottleneck = max(state.spans, key=lambda span: span.duration_ms)
        details["bottleneck"] = {
            "span": bottleneck.name,
            "kind": bottleneck.kind,
            "duration_ms": bottleneck.duration_ms,
        }
        flags["bottleneck"] = bottleneck.duration_ms >= slow_tool_ms

    flags["any"] = any(
        value
        for key, value in flags.items()
        if key not in {"any"} and isinstance(value, bool)
    )
    details["flags"] = {
        key: value for key, value in flags.items() if isinstance(value, bool)
    }
    return {"flags": flags, "details": details}


def human_summary(anomalies: dict[str, Any]) -> list[str]:
    flags = anomalies.get("flags", {})
    details = anomalies.get("details", {})
    messages: list[str] = []
    if flags.get("loop"):
        messages.append(
            "Se repitió una acción idéntica: posible bucle de razonamiento."
        )
    if flags.get("max_iterations"):
        messages.append(
            f"Se alcanzó el máximo de iteraciones ({details.get('iterations')})."
        )
    if flags.get("context_drift"):
        messages.append(
            "El prompt creció de forma anómala dentro del turno: revisar "
            "deriva de contexto."
        )
    if flags.get("model_switch"):
        messages.append(
            "El enrutador cambió de modelo dentro del turno: "
            + ", ".join(details.get("models", []))
        )
    if flags.get("slow_tool"):
        messages.append("Hay herramientas lentas; revisar el cuello de botella.")
    if flags.get("tool_error") or flags.get("llm_error"):
        messages.append("El turno registró al menos un error de ejecución.")
    return messages
