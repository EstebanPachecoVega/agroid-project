"""Consolida las corridas reales en CSV, JSON y un informe de resultados.

Uso:
    python -m agroid.benchmarks.results
    python -m agroid.benchmarks.results --out docs/evidencias
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..observability import metrics, store
from ..security.pii import redact_obj

REAL_RUNS = [
    ("real-router-20261119", "Router libre", "router"),
    ("real-pinned-20261119", "Modelo fijado (ling)", "pinned"),
    ("real-pinned-n01", "Comparación N01 fijado", "compare"),
    ("real-consistency-20261123b", "Consistencia", "consistency"),
    ("real-bias-20261123", "Sesgo", "bias"),
    ("real-postfix-20261123", "Post-fix", "post_fix"),
]

EXCLUDED_RUNS = [
    ("real-consistency-20261123", "Intento de consistencia con 429 del proveedor"),
]


def _mean(values: list[float]) -> float:
    return round(statistics.mean(values), 4) if values else 0.0


def _query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return store.query(sql, params)


def _load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run_id, label, suite in REAL_RUNS:
        data = _query(
            "SELECT e.*, t.status AS trace_status, t.duration_ms, "
            "t.total_tokens, t.cost_equivalent_usd, t.model_actual, "
            "t.tool_calls_json, t.output_redacted, t.started_at "
            "FROM evaluations e JOIN traces t ON e.trace_id=t.trace_id "
            "WHERE e.run_id=? ORDER BY e.case_id, e.repetition",
            (run_id,),
        )
        for row in data:
            rows.append(
                {
                    "run_id": run_id,
                    "suite": suite,
                    "run_label": label,
                    "case_id": row["case_id"],
                    "repetition": row["repetition"],
                    "trace_status": row["trace_status"],
                    "score": row["score"],
                    "tool_match": row["tool_match"],
                    "args_match": row["args_match"],
                    "facts_match": row["facts_match"],
                    "groundedness": row["groundedness"],
                    "duration_ms": row["duration_ms"],
                    "total_tokens": row["total_tokens"],
                    "cost_equivalent_usd": row["cost_equivalent_usd"],
                    "model_actual": row["model_actual"],
                    "trace_id": row["trace_id"],
                    "response_preview": (
                        row.get("output_redacted") or row.get("notes") or ""
                    ),
                    "tool_calls_json": row.get("tool_calls_json") or "[]",
                }
            )
    return rows


def _summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for run_id, label, suite in REAL_RUNS:
        subset = [row for row in rows if row["run_id"] == run_id]
        if not subset:
            continue
        traces = _query("SELECT * FROM traces WHERE run_id=?", (run_id,))
        models = set()
        switches = 0
        for trace in traces:
            actual = [
                item.strip()
                for item in str(trace.get("model_actual") or "").split(",")
                if item.strip()
            ]
            models.update(actual)
            if len(actual) > 1:
                switches += 1
        durations = [float(row["duration_ms"] or 0) for row in subset]
        summaries.append(
            {
                "run_id": run_id,
                "label": label,
                "suite": suite,
                "turns": len(subset),
                "success": sum(
                    1 for row in subset if row["trace_status"] == "success"
                ),
                "score": _mean([float(row["score"]) for row in subset]),
                "tool_match": _mean(
                    [float(row["tool_match"]) for row in subset]
                ),
                "args_match": _mean(
                    [float(row["args_match"]) for row in subset]
                ),
                "facts_match": _mean(
                    [float(row["facts_match"]) for row in subset]
                ),
                "groundedness": _mean(
                    [float(row["groundedness"]) for row in subset]
                ),
                "tokens": sum(int(row["total_tokens"] or 0) for row in subset),
                "latency_mean_s": round(_mean(durations) / 1000, 2),
                "latency_max_s": round(max(durations) / 1000, 2),
                "models": sorted(models),
                "model_switches": switches,
            }
        )
    return summaries


def _overall(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "turns": len(rows),
        "success": sum(1 for row in rows if row["trace_status"] == "success"),
        "score": _mean([float(row["score"]) for row in rows]),
        "tool_match": _mean([float(row["tool_match"]) for row in rows]),
        "args_match": _mean([float(row["args_match"]) for row in rows]),
        "facts_match": _mean([float(row["facts_match"]) for row in rows]),
        "groundedness": _mean([float(row["groundedness"]) for row in rows]),
        "tokens": sum(int(row["total_tokens"] or 0) for row in rows),
        "cost_equivalent_usd": round(
            sum(float(row["cost_equivalent_usd"] or 0) for row in rows), 6
        ),
    }


def _consistency() -> list[dict[str, Any]]:
    rows = _query(
        "SELECT e.consistency_group, t.tool_calls_json "
        "FROM evaluations e JOIN traces t ON e.trace_id=t.trace_id "
        "WHERE e.run_id='real-consistency-20261123b'"
    )
    groups: dict[str, list[list[str]]] = {}
    for row in rows:
        group = row.get("consistency_group") or ""
        groups.setdefault(group, []).append(
            metrics.parse_tool_sequence(
                {"tool_calls_json": row.get("tool_calls_json") or "[]"}
            )
        )
    result = []
    for group, sequences in sorted(groups.items()):
        scores = []
        for index in range(len(sequences)):
            for other in range(index + 1, len(sequences)):
                scores.append(metrics.jaccard(sequences[index], sequences[other]))
        result.append(
            {
                "group": group,
                "cases": len(sequences),
                "tool_consistency": _mean(scores),
            }
        )
    return result


def _bias() -> list[dict[str, Any]]:
    rows = _query(
        "SELECT e.case_id, e.score, t.tool_calls_json, t.duration_ms "
        "FROM evaluations e JOIN traces t ON e.trace_id=t.trace_id "
        "WHERE e.run_id='real-bias-20261123' ORDER BY e.case_id"
    )
    result = []
    for row in rows:
        sequence = metrics.parse_tool_sequence(
            {"tool_calls_json": row.get("tool_calls_json") or "[]"}
        )
        result.append(
            {
                "case_id": row["case_id"],
                "tools": sequence,
                "score": row["score"],
                "latency_s": round(float(row["duration_ms"] or 0) / 1000, 2),
            }
        )
    return result


def _ttft() -> dict[str, Any]:
    rows = _query(
        "SELECT * FROM ttft_measurements WHERE status='success' "
        "ORDER BY measured_at"
    )
    failed = _query(
        "SELECT COUNT(*) AS n FROM ttft_measurements WHERE status='error'"
    )
    if not rows:
        return {"samples": 0, "failed": 0}
    ttft = [float(row["ttft_ms"]) for row in rows if row["ttft_ms"]]
    throughput = [
        float(row["tokens_per_second"])
        for row in rows
        if row["tokens_per_second"]
    ]
    ms_token = [
        float(row["ms_per_token"]) for row in rows if row["ms_per_token"]
    ]
    return {
        "samples": len(rows),
        "failed": int(failed[0]["n"]) if failed else 0,
        "model": rows[0]["model"],
        "ttft_min_ms": round(min(ttft), 2) if ttft else None,
        "ttft_max_ms": round(max(ttft), 2) if ttft else None,
        "ttft_mean_ms": round(_mean(ttft), 2) if ttft else None,
        "tokens_per_second_min": round(min(throughput), 2) if throughput else None,
        "tokens_per_second_max": round(max(throughput), 2) if throughput else None,
        "ms_per_token_min": round(min(ms_token), 2) if ms_token else None,
        "ms_per_token_max": round(max(ms_token), 2) if ms_token else None,
    }


def _load_test(evidence_dir: Path) -> dict[str, Any]:
    files = sorted(evidence_dir.glob("load_*.json"))
    if not files:
        return {}
    try:
        summary = json.loads(files[-1].read_text(encoding="utf-8")).get(
            "summary", {}
        )
        for key in ("p50_ms", "p95_ms", "p99_ms", "max_ms"):
            if summary.get(key) is not None:
                summary[key] = round(float(summary[key]), 0)
        return summary
    except Exception:
        return {}


def _incidents() -> list[dict[str, Any]]:
    rows = _query(
        "SELECT run_id, status, error_type, COUNT(*) AS n FROM traces "
        "WHERE status IN ('error','rate_limit') "
        "GROUP BY run_id, status, error_type ORDER BY n DESC"
    )
    for row in rows:
        if not row.get("run_id"):
            row["run_id"] = "(smoke / sin run_id)"
    return rows


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    columns = [
        "run_id",
        "suite",
        "case_id",
        "repetition",
        "trace_status",
        "score",
        "tool_match",
        "args_match",
        "facts_match",
        "groundedness",
        "duration_ms",
        "total_tokens",
        "cost_equivalent_usd",
        "model_actual",
        "trace_id",
        "response_preview",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})


def _fmt(value: float | None, digits: int = 3) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _write_markdown(
    path: Path,
    summaries: list[dict[str, Any]],
    overall: dict[str, Any],
    consistency: list[dict[str, Any]],
    bias: list[dict[str, Any]],
    ttft: dict[str, Any],
    load: dict[str, Any],
    incidents: list[dict[str, Any]],
) -> None:
    lines = [
        "# Resultados consolidados — EP3 Observabilidad",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Este documento resume las corridas reales y la evidencia visual. "
        "Los datos por turno están en `resultados_turnos.csv` y "
        "`resultados_consolidados.json`.",
        "",
        "## Resumen por corrida",
        "",
        "| Corrida | Turnos | Éxito | Score | Tool | Args | Facts | Grounded | Tokens | Latencia media | Modelos |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['label']} | {item['turns']} | "
            f"{item['success']}/{item['turns']} | {_fmt(item['score'])} | "
            f"{_fmt(item['tool_match'])} | {_fmt(item['args_match'])} | "
            f"{_fmt(item['facts_match'])} | {_fmt(item['groundedness'])} | "
            f"{item['tokens']:,} | {item['latency_mean_s']:.1f} s | "
            f"{len(item['models'])} |"
        )
    lines.extend(
        [
            "",
            "## Total real",
            "",
            "| Turnos | Éxito | Score | Tool | Args | Facts | Grounded | Tokens | Costo equiv. |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            f"| {overall['turns']} | {overall['success']}/{overall['turns']} | "
            f"{_fmt(overall['score'])} | {_fmt(overall['tool_match'])} | "
            f"{_fmt(overall['args_match'])} | {_fmt(overall['facts_match'])} | "
            f"{_fmt(overall['groundedness'])} | {overall['tokens']:,} | "
            f"USD {overall['cost_equivalent_usd']:.6f} |",
            "",
            "## Consistencia real",
            "",
            "| Grupo | Casos | Jaccard de herramientas |",
            "|---|---:|---:|",
        ]
    )
    for item in consistency:
        lines.append(
            f"| {item['group']} | {item['cases']} | "
            f"{_fmt(item['tool_consistency'])} |"
        )
    lines.extend(
        [
            "",
            "## Sesgo: pares de nombres",
            "",
            "| Caso | Herramientas | Score | Latencia |",
            "|---|---|---:|---:|",
        ]
    )
    for item in bias:
        lines.append(
            f"| {item['case_id']} | {', '.join(item['tools']) or '-'} | "
            f"{_fmt(float(item['score']))} | {item['latency_s']:.2f} s |"
        )
    lines.extend(
        [
            "",
            "## TTFT real",
            "",
            "| Muestras | Fallidas | Modelo | TTFT min | TTFT max | tok/s min | tok/s max | ms/token |",
            "|---:|---:|---|---:|---:|---:|---:|---:|",
            f"| {ttft.get('samples', 0)} | {ttft.get('failed', 0)} | "
            f"{ttft.get('model', '-')} | {ttft.get('ttft_min_ms', '-')} ms | "
            f"{ttft.get('ttft_max_ms', '-')} ms | "
            f"{ttft.get('tokens_per_second_min', '-')} | "
            f"{ttft.get('tokens_per_second_max', '-')} | "
            f"{ttft.get('ms_per_token_min', '-')}–{ttft.get('ms_per_token_max', '-')} |",
            "",
            "## Carga simulada",
            "",
            f"- Solicitudes: {load.get('requests', '-')} "
            f"({load.get('workers', '-')} workers)",
            f"- Éxito: {load.get('success', '-')}; errores: "
            f"{load.get('exceptions', '-')}; tool errors: "
            f"{load.get('tool_errors', '-')}",
            f"- P50: {load.get('p50_ms', '-')} ms; "
            f"P95: {load.get('p95_ms', '-')} ms; "
            f"P99: {load.get('p99_ms', '-')} ms",
            "",
            "## Incidentes de proveedor",
            "",
            "| Run | Estado | Tipo | Turnos |",
            "|---|---|---|---:|",
        ]
    )
    for item in incidents:
        lines.append(
            f"| {item['run_id']} | {item['status']} | "
            f"{item['error_type']} | {item['n']} |"
        )
    lines.extend(
        [
            "",
            "El intento `real-consistency-20261123` se excluye del resumen porque "
            "sus seis turnos recibieron 429 del proveedor; la corrida válida es "
            "`real-consistency-20261123b`. La tabla de incidentes también incluye "
            "pruebas de humo y corridas auxiliares; los errores se conservan en SQLite.",
            "",
            "## Capturas del dashboard",
            "",
            "![Resumen](captura_dashboard_resumen.jpeg)",
            "",
            "![Rendimiento y TTFT](captura_dashboard_rendimiento.jpeg)",
            "",
            "![Calidad y consistencia](captura_dashboard_calidad.jpeg)",
            "",
            "![Costos y tokens](captura_dashboard_costos.jpeg)",
            "",
            "![Explorador de trazas real](captura_dashboard_traza_router.jpeg)",
            "",
            "![Seguridad](captura_dashboard_seguridad.jpeg)",
            "",
            "## Capturas de LangSmith",
            "",
            "![LangSmith Overview](captura_langsmith_01_overview.png)",
            "",
            "![LangSmith Tracing](captura_langsmith_02_tracing.png)",
            "",
            "![LangSmith Monitoring](captura_langsmith_03_monitoring.png)",
            "",
            "La captura de calidad usa los filtros `Solo corridas reales` y "
            "`Excluir intentos con error`; puede incluir corridas auxiliares. "
            "La tabla de consistencia de este documento usa la corrida canónica "
            "`real-consistency-20261123b` (6 casos).",
            "",
            "## Archivos",
            "",
            "- `resultados_turnos.csv`: una fila por turno evaluado.",
            "- `resultados_consolidados.json`: resumen, consistencia, sesgo, "
            "TTFT, carga e incidentes.",
            "- `RESULTADOS_CORRIDAS.md`: este documento.",
            "- `captura_dashboard_*.jpeg`: capturas del tablero.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate(evidence_dir: str | Path | None = None) -> dict[str, Any]:
    settings = get_settings()
    evidence = Path(evidence_dir) if evidence_dir else settings.evidence_dir
    evidence.mkdir(parents=True, exist_ok=True)
    store.init_store()

    rows = _load_rows()
    for row in rows:
        row["response_preview"] = redact_obj(str(row.get("response_preview") or ""))[:300]
    summaries = _summaries(rows)
    overall = _overall(rows)
    consistency = _consistency()
    bias = _bias()
    ttft = _ttft()
    load = _load_test(evidence)
    incidents = _incidents()

    csv_path = evidence / "resultados_turnos.csv"
    json_path = evidence / "resultados_consolidados.json"
    md_path = evidence / "RESULTADOS_CORRIDAS.md"
    _write_csv(rows, csv_path)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs": REAL_RUNS,
        "excluded_runs": EXCLUDED_RUNS,
        "summaries": summaries,
        "overall": overall,
        "consistency": consistency,
        "bias": bias,
        "ttft": ttft,
        "load": load,
        "incidents": incidents,
        "screenshots": [
            "captura_dashboard_resumen.jpeg",
            "captura_dashboard_rendimiento.jpeg",
            "captura_dashboard_calidad.jpeg",
            "captura_dashboard_costos.jpeg",
            "captura_dashboard_traza_router.jpeg",
            "captura_dashboard_seguridad.jpeg",
            "captura_langsmith_01_overview.png",
            "captura_langsmith_02_tracing.png",
            "captura_langsmith_03_monitoring.png",
        ],
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    _write_markdown(
        md_path, summaries, overall, consistency, bias, ttft, load, incidents
    )
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consolidar resultados EP3")
    parser.add_argument("--out", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = generate(args.out)
    print(json.dumps(payload["overall"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
