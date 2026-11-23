"""Recalcula métricas de una corrida usando las trazas ya almacenadas.

Sirve cuando se corrige el evaluador (por ejemplo, para aceptar claves
equivalentes o rechazos seguros) sin volver a consumir cuota del proveedor.
Los ``facts_match`` se conservan porque fueron validados contra la base real
en el momento de la corrida; las demás métricas se recalculan desde la traza.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from ..agent import TurnResult
from ..observability import store
from .cases import CASES
from .evaluate import _args_match, _groundedness, _tool_match


def _json(value: Any, default: Any = None) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return default


def _result_from_trace(trace: dict[str, Any], tools: list[dict[str, Any]]) -> TurnResult:
    tool_calls = []
    for tool in tools:
        tool_calls.append(
            {
                "tool": tool.get("tool_name", ""),
                "args": _json(tool.get("args_json"), {}) or {},
                "result": tool.get("result_summary", ""),
                "status": tool.get("status", ""),
                "duration_ms": tool.get("duration_ms", 0.0),
            }
        )
    return TurnResult(
        response=trace.get("output_redacted", "") or "",
        trace_id=trace.get("trace_id", ""),
        session_id=trace.get("session_id", ""),
        turn_id=trace.get("turn_id", ""),
        status=trace.get("status", "success"),
        error=trace.get("error_type", "") or "",
        error_type=trace.get("error_type", "") or "",
        duration_ms=float(trace.get("duration_ms") or 0.0),
        prompt_tokens=int(trace.get("prompt_tokens") or 0),
        completion_tokens=int(trace.get("completion_tokens") or 0),
        total_tokens=int(trace.get("total_tokens") or 0),
        cost_usd=float(trace.get("cost_usd") or 0.0),
        cost_equivalent_usd=float(trace.get("cost_equivalent_usd") or 0.0),
        iterations=int(trace.get("iterations") or 0),
        model_requested=trace.get("model_requested", "") or "",
        model_actual=trace.get("model_actual", "") or "",
        tool_calls=tool_calls,
        security=_json(trace.get("security_json"), {}) or {},
        anomalies=_json(trace.get("anomalies_json"), {}) or {},
        langsmith_trace_id=trace.get("langsmith_trace_id", "") or "",
        input_redacted=trace.get("input_redacted", "") or "",
        output_redacted=trace.get("output_redacted", "") or "",
    )


def rescore(run_id: str) -> list[dict[str, Any]]:
    evaluations = store.query(
        "SELECT * FROM evaluations WHERE run_id=? ORDER BY case_id, repetition",
        (run_id,),
    )
    changes = []
    for evaluation in evaluations:
        trace_rows = store.query(
            "SELECT * FROM traces WHERE trace_id=?",
            (evaluation["trace_id"],),
        )
        if not trace_rows:
            continue
        trace = trace_rows[0]
        tools = store.query(
            "SELECT * FROM tool_calls WHERE trace_id=? ORDER BY started_at",
            (evaluation["trace_id"],),
        )
        case = CASES.get(evaluation["case_id"])
        if case is None:
            continue
        result = _result_from_trace(trace, tools)
        tool_match = _tool_match(result, case)
        args_match = _args_match(result, case)
        groundedness = _groundedness(result, {}, case)
        facts_match = float(evaluation.get("facts_match") or 0.0)
        if case.expected_blocked:
            score = 1.0 if result.status in {"blocked", "blocked_output"} else 0.0
        else:
            score = round(
                0.4 * tool_match
                + 0.3 * args_match
                + 0.2 * facts_match
                + 0.1 * groundedness,
                4,
            )
        if (
            abs(score - float(evaluation.get("score") or 0.0)) > 1e-9
            or abs(tool_match - float(evaluation.get("tool_match") or 0.0)) > 1e-9
            or abs(args_match - float(evaluation.get("args_match") or 0.0)) > 1e-9
            or abs(groundedness - float(evaluation.get("groundedness") or 0.0)) > 1e-9
        ):
            store.execute(
                "UPDATE evaluations SET tool_match=?, args_match=?, "
                "groundedness=?, score=? WHERE id=?",
                (
                    tool_match,
                    args_match,
                    groundedness,
                    score,
                    evaluation["id"],
                ),
            )
            changes.append(
                {
                    "case_id": evaluation["case_id"],
                    "repetition": evaluation["repetition"],
                    "old_score": evaluation.get("score"),
                    "new_score": score,
                    "old_args": evaluation.get("args_match"),
                    "new_args": args_match,
                }
            )
    return changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recalcular evaluaciones")
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changes = rescore(args.run_id)
    if not changes:
        print("Sin cambios.")
    for change in changes:
        print(
            f"{change['case_id']}#{change['repetition']}: "
            f"score {change['old_score']} -> {change['new_score']}, "
            f"args {change['old_args']} -> {change['new_args']}"
        )
    print(f"{len(changes)} evaluaciones actualizadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
