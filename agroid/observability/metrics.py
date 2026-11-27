"""Agregaciones para el dashboard y el informe.

Las funciones son tolerantes a tablas vacías: el tablero debe abrir incluso
antes de la primera corrida real.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import store


def safe_frame(name: str, path: str | Path | None = None) -> pd.DataFrame:
    try:
        return store.table(name, path=path)
    except Exception:
        return pd.DataFrame()


def load_frames(path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    return {
        "traces": safe_frame("traces", path),
        "spans": safe_frame("spans", path),
        "llm_calls": safe_frame("llm_calls", path),
        "tool_calls": safe_frame("tool_calls", path),
        "evaluations": safe_frame("evaluations", path),
        "security_events": safe_frame("security_events", path),
        "manual_integrity": safe_frame("manual_integrity", path),
        "runs": safe_frame("runs", path),
        "langsmith_runs": safe_frame("langsmith_runs", path),
        "ttft": safe_frame("ttft_measurements", path),
    }


def _series(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def percentile(values: Any, p: float) -> float | None:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if series.empty:
        return None
    return float(np.percentile(series, p))


def kpis(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    traces = frames.get("traces", pd.DataFrame())
    llm = frames.get("llm_calls", pd.DataFrame())
    if traces.empty:
        return {
            "traces": 0,
            "success_rate": None,
            "error_rate": None,
            "blocked_rate": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "cost_equivalent_usd": 0.0,
            "avg_tokens": None,
            "model_switches": 0,
        }

    total = len(traces)
    status = traces.get("status", pd.Series(dtype="object")).fillna("")
    success = int((status == "success").sum())
    errors = int((~status.isin(["success", "blocked"])).sum())
    blocked = int((status == "blocked").sum())
    latency = _series(traces, "duration_ms")
    total_tokens = int(_series(traces, "total_tokens").sum())

    switches = 0
    if not llm.empty and "model_actual" in llm.columns:
        switches = int(
            llm.groupby("trace_id")["model_actual"]
            .nunique()
            .gt(1)
            .sum()
        )

    return {
        "traces": total,
        "success_rate": round(success / total, 4) if total else None,
        "error_rate": round(errors / total, 4) if total else None,
        "blocked_rate": round(blocked / total, 4) if total else None,
        "latency_p50_ms": percentile(latency, 50),
        "latency_p95_ms": percentile(latency, 95),
        "total_tokens": total_tokens,
        "cost_usd": float(_series(traces, "cost_usd").sum()),
        "cost_equivalent_usd": float(
            _series(traces, "cost_equivalent_usd").sum()
        ),
        "avg_tokens": round(total_tokens / total, 1) if total else None,
        "model_switches": switches,
        "replan_rate": round(
            float(
                pd.to_numeric(
                    traces.get("replan_count", pd.Series(dtype="float64")),
                    errors="coerce",
                ).fillna(0).gt(0).mean()
            ),
            4,
        ) if "replan_count" in traces.columns else None,
        "citation_coverage": round(
            float(
                pd.to_numeric(
                    traces.get("citation_coverage", pd.Series(dtype="float64")),
                    errors="coerce",
                ).dropna().mean()
            ),
            4,
        ) if "citation_coverage" in traces.columns else None,
    }


def latency_by_kind(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    spans = frames.get("spans", pd.DataFrame())
    if spans.empty:
        return pd.DataFrame(columns=["kind", "p50_ms", "p95_ms", "count"])
    rows = []
    for kind, group in spans.groupby("kind"):
        duration = pd.to_numeric(group["duration_ms"], errors="coerce").dropna()
        rows.append(
            {
                "kind": kind,
                "count": len(duration),
                "p50_ms": percentile(duration, 50),
                "p95_ms": percentile(duration, 95),
                "max_ms": float(duration.max()) if not duration.empty else None,
            }
        )
    return pd.DataFrame(rows).sort_values("p95_ms", ascending=False)


def tool_frequency(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tools = frames.get("tool_calls", pd.DataFrame())
    if tools.empty:
        return pd.DataFrame(columns=["tool_name", "count", "error_rate", "p95_ms"])
    rows = []
    for name, group in tools.groupby("tool_name"):
        errors = (group["status"] == "error").mean()
        duration = pd.to_numeric(group["duration_ms"], errors="coerce")
        rows.append(
            {
                "tool_name": name,
                "count": len(group),
                "error_rate": round(float(errors), 4),
                "p95_ms": percentile(duration, 95),
            }
        )
    return pd.DataFrame(rows).sort_values("count", ascending=False)


def error_breakdown(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    traces = frames.get("traces", pd.DataFrame())
    if traces.empty:
        return pd.DataFrame(columns=["error_type", "count"])
    errors = traces[~traces["status"].isin(["success", "blocked"])]
    if errors.empty:
        return pd.DataFrame(columns=["error_type", "count"])
    return (
        errors.groupby("error_type")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def parse_tool_sequence(row: pd.Series) -> list[str]:
    try:
        data = json.loads(row.get("tool_calls_json") or "[]")
        return [item.get("tool", "") for item in data if item.get("tool")]
    except Exception:
        return []


def jaccard(seq_a: list[str], seq_b: list[str]) -> float:
    if not seq_a and not seq_b:
        return 1.0
    set_a, set_b = set(seq_a), set(seq_b)
    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else 1.0


def consistency_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    traces = frames.get("traces", pd.DataFrame())
    if traces.empty or "experiment_group" not in traces.columns:
        return pd.DataFrame(
            columns=["group", "cases", "tool_consistency", "facts_match"]
        )
    group_column = "experiment_group"
    if "consistency_group" in traces.columns and (
        traces["consistency_group"].fillna("").astype(str).str.len().gt(0).any()
    ):
        group_column = "consistency_group"
    subset_all = traces[
        traces[group_column].fillna("").astype(str).str.len() > 0
    ]
    rows = []
    for group, subset in subset_all.groupby(group_column):
        sequences = [parse_tool_sequence(row) for _, row in subset.iterrows()]
        pair_scores = []
        for i in range(len(sequences)):
            for j in range(i + 1, len(sequences)):
                pair_scores.append(jaccard(sequences[i], sequences[j]))
        rows.append(
            {
                "group": group,
                "cases": len(subset),
                "tool_consistency": round(
                    float(np.mean(pair_scores)), 4
                )
                if pair_scores
                else None,
            }
        )
    return pd.DataFrame(rows)


def evaluations_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    evaluations = frames.get("evaluations", pd.DataFrame())
    if evaluations.empty:
        return pd.DataFrame(
            columns=[
                "experiment_group",
                "cases",
                "tool_match",
                "args_match",
                "facts_match",
                "groundedness",
                "score",
            ]
        )
    numeric = [
        "tool_match",
        "args_match",
        "facts_match",
        "groundedness",
        "score",
        "citation_coverage",
    ]
    for column in numeric:
        if column not in evaluations.columns:
            evaluations[column] = 0.0
    grouped = (
        evaluations.groupby("experiment_group")[numeric]
        .mean(numeric_only=True)
        .reset_index()
    )
    counts = (
        evaluations.groupby("experiment_group")
        .size()
        .reset_index(name="cases")
    )
    return grouped.merge(counts, on="experiment_group", how="left")


def cost_projection(frames: dict[str, pd.DataFrame], per: int = 1000) -> dict[str, Any]:
    traces = frames.get("traces", pd.DataFrame())
    if traces.empty:
        return {
            "avg_cost_per_trace": 0.0,
            "avg_equivalent_per_trace": 0.0,
            "projected_equivalent": 0.0,
            "duplicate_input_rate": 0.0,
        }
    actual = _series(traces, "cost_usd")
    equivalent = _series(traces, "cost_equivalent_usd")
    avg_actual = float(actual.mean()) if not actual.empty else 0.0
    avg_equiv = float(equivalent.mean()) if not equivalent.empty else 0.0
    inputs = traces.get("input_redacted", pd.Series(dtype="object")).dropna()
    duplicate_rate = (
        float(1 - inputs.nunique() / len(inputs)) if len(inputs) else 0.0
    )
    return {
        "avg_cost_per_trace": round(avg_actual, 8),
        "avg_equivalent_per_trace": round(avg_equiv, 8),
        "projected_equivalent": round(avg_equiv * per, 4),
        "duplicate_input_rate": round(duplicate_rate, 4),
    }


def security_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    events = frames.get("security_events", pd.DataFrame())
    if events.empty:
        return pd.DataFrame(columns=["event_type", "severity", "count"])
    return (
        events.groupby(["event_type", "severity"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def model_usage(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    llm = frames.get("llm_calls", pd.DataFrame())
    if llm.empty:
        return pd.DataFrame(
            columns=["model_actual", "calls", "prompt_tokens", "completion_tokens"]
        )
    grouped = (
        llm.groupby("model_actual")
        .agg(
            calls=("span_id", "count"),
            prompt_tokens=("prompt_tokens", "sum"),
            completion_tokens=("completion_tokens", "sum"),
        )
        .reset_index()
    )
    return grouped.sort_values("calls", ascending=False)


def _parse_json_list(value: Any) -> list[Any]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def rag_source_mix(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Cuenta fragmentos internos y externos recuperados por turno."""
    traces = frames.get("traces", pd.DataFrame())
    rows: list[dict[str, Any]] = []
    if traces.empty or "rag_sources_json" not in traces.columns:
        return pd.DataFrame(columns=["source_type", "fragments", "traces"])
    for _, row in traces.iterrows():
        sources = _parse_json_list(row.get("rag_sources_json"))
        counts = {"interno": 0, "externo": 0}
        for source in sources:
            if isinstance(source, dict):
                key = str(source.get("source_type", "interno"))
                counts[key] = counts.get(key, 0) + 1
            else:
                # Las trazas importadas guardan solo el identificador
                # (``["E05", "M01"]``); el prefijo permite inferir el tipo.
                fragment_id = str(source).strip().upper()
                key = "externo" if fragment_id.startswith("E") else "interno"
                counts[key] = counts.get(key, 0) + 1
        if sources:
            rows.append(
                {
                    "source_type": "interno",
                    "fragments": counts.get("interno", 0),
                }
            )
            rows.append(
                {
                    "source_type": "externo",
                    "fragments": counts.get("externo", 0),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["source_type", "fragments", "traces"])
    frame = pd.DataFrame(rows)
    return (
        frame.groupby("source_type")
        .agg(fragments=("fragments", "sum"), traces=("fragments", "count"))
        .reset_index()
    )


def citation_summary(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    evaluations = frames.get("evaluations", pd.DataFrame())
    traces = frames.get("traces", pd.DataFrame())
    values: list[float] = []
    if not evaluations.empty and "citation_coverage" in evaluations.columns:
        values = [
            float(value)
            for value in pd.to_numeric(
                evaluations["citation_coverage"], errors="coerce"
            ).dropna()
        ]
    if not values and not traces.empty and "citation_coverage" in traces.columns:
        values = [
            float(value)
            for value in pd.to_numeric(
                traces["citation_coverage"], errors="coerce"
            ).dropna()
        ]
    return {
        "cases": len(values),
        "mean": round(float(np.mean(values)), 4) if values else None,
        "min": round(float(np.min(values)), 4) if values else None,
        "max": round(float(np.max(values)), 4) if values else None,
    }


def prompt_version_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    evaluations = frames.get("evaluations", pd.DataFrame())
    if evaluations.empty or "mode" not in evaluations.columns:
        return pd.DataFrame(
            columns=["prompt_version", "cases", "score", "citation_coverage"]
        )
    traces = frames.get("traces", pd.DataFrame())
    version_by_trace = {}
    if not traces.empty and "prompt_version" in traces.columns:
        version_by_trace = dict(
            zip(traces["trace_id"], traces["prompt_version"])
        )
    data = evaluations.copy()
    data["prompt_version"] = data["trace_id"].map(version_by_trace).fillna("v2")
    numeric = [
        column
        for column in ("score", "citation_coverage", "groundedness")
        if column in data.columns
    ]
    if not numeric:
        return pd.DataFrame()
    grouped = (
        data.groupby("prompt_version")[numeric]
        .mean(numeric_only=True)
        .reset_index()
    )
    counts = (
        data.groupby("prompt_version").size().reset_index(name="cases")
    )
    return grouped.merge(counts, on="prompt_version", how="left")


def planning_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    evaluations = frames.get("evaluations", pd.DataFrame())
    if evaluations.empty or "mode" not in evaluations.columns:
        return pd.DataFrame(
            columns=["mode", "cases", "score", "replan_rate", "tool_match"]
        )
    data = evaluations.copy()
    data["mode"] = data["mode"].fillna("react")
    numeric = [
        column
        for column in ("score", "tool_match", "args_match", "groundedness")
        if column in data.columns
    ]
    grouped = (
        data.groupby("mode")[numeric]
        .mean(numeric_only=True)
        .reset_index()
    )
    counts = data.groupby("mode").size().reset_index(name="cases")
    if "replan_count" in data.columns:
        replans = (
            data.assign(
                replanned=pd.to_numeric(
                    data["replan_count"], errors="coerce"
                ).fillna(0).gt(0)
            )
            .groupby("mode")["replanned"]
            .mean()
            .reset_index(name="replan_rate")
        )
        grouped = grouped.merge(replans, on="mode", how="left")
    return grouped.merge(counts, on="mode", how="left")
