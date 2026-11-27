"""Consolida la evidencia EFT: suite real, RAG, prompts y planificación.

Uso:
    python docs/consolidar_resultados_eft.py
"""

from __future__ import annotations

import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agroid.observability import store  # noqa: E402

RUN_ID = "real-eft-20261127"
OUT = ROOT / "docs" / "evidencias_eft"


def mean(values):
    return round(statistics.mean(values), 4) if values else 0.0


def load_latest(prefix: str) -> dict:
    files = sorted(OUT.glob(f"{prefix}_*.json"))
    if not files:
        return {}
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    existing_path = OUT / "resultados_eft.json"
    existing = {}
    if existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    rows = store.query(
        "SELECT e.*, t.status AS trace_status, t.duration_ms, "
        "t.total_tokens, t.cost_equivalent_usd, t.model_actual, "
        "t.tool_calls_json, t.output_redacted, t.started_at "
        "FROM evaluations e JOIN traces t ON e.trace_id=t.trace_id "
        "WHERE e.run_id=? ORDER BY e.case_id",
        (RUN_ID,),
    )
    if not rows and existing.get("rows"):
        # La corrida real puede haberse generado antes de un --reset de la
        # suite simulada. En ese caso se conserva la evidencia ya consolidada.
        rows = existing["rows"]
        traces = existing.get("traces", [])
        overall = existing.get("overall", {})
    else:
        if not rows:
            print(f"No hay evaluaciones para {RUN_ID}")
            return 1
        traces = store.query(
            "SELECT * FROM traces WHERE run_id=? ORDER BY started_at", (RUN_ID,)
        )
        overall = {
            "run_id": RUN_ID,
            "turns": len(rows),
            "success": sum(1 for row in rows if row["trace_status"] == "success"),
            "blocked": sum(1 for row in rows if row["trace_status"] == "blocked"),
            "score": mean([float(row["score"]) for row in rows]),
            "tool_match": mean([float(row["tool_match"]) for row in rows]),
            "args_match": mean([float(row["args_match"]) for row in rows]),
            "facts_match": mean([float(row["facts_match"]) for row in rows]),
            "groundedness": mean([float(row["groundedness"]) for row in rows]),
            "citation_coverage": mean(
                [
                    float(row["citation_coverage"])
                    for row in rows
                    if row.get("citation_coverage") is not None
                ]
            ),
            "tokens": sum(int(row["total_tokens"] or 0) for row in traces),
            "cost_equivalent_usd": round(
                sum(float(row["cost_equivalent_usd"] or 0) for row in traces), 8
            ),
            "latency_mean_s": round(
                mean([float(row["duration_ms"] or 0) for row in traces]) / 1000, 2
            ),
            "latency_max_s": round(
                max(float(row["duration_ms"] or 0) for row in traces) / 1000, 2
            ),
            "models": sorted(
                {
                    item.strip()
                    for trace in traces
                    for item in str(trace.get("model_actual") or "").split(",")
                    if item.strip()
                }
            ),
        }
    rag_eval = load_latest("rag_eval")
    rag_summary = rag_eval.get("summary", rag_eval) if rag_eval else {}
    prompt_eval = load_latest("prompt_eval")
    planning_eval = load_latest("planning_eval")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "overall": overall,
        "rows": rows,
        "traces": [
            {
                key: trace.get(key)
                for key in (
                    "trace_id",
                    "case_id",
                    "status",
                    "duration_ms",
                    "total_tokens",
                    "model_actual",
                    "prompt_version",
                    "mode",
                    "replan_count",
                    "citation_coverage",
                    "rag_sources_json",
                )
            }
            for trace in traces
        ],
        "rag_eval": rag_eval.get("summary", {}) if rag_eval else {},
        "prompt_eval": {
            "baseline": prompt_eval.get("comparison", {}).get(
                "baseline_system_v1", {}
            ),
            "current": prompt_eval.get("comparison", {}).get(
                "current_system_v2", {}
            ),
            "functional_regression": prompt_eval.get(
                "functional_regression", {}
            ),
        }
        if prompt_eval
        else {},
        "planning_eval": planning_eval.get("summary", [])
        if planning_eval
        else [],
    }
    json_path = OUT / "resultados_eft.json"
    csv_path = OUT / "resultados_eft.csv"
    md_path = OUT / "RESULTADOS_EFT.md"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    fields = [
        "case_id",
        "category",
        "trace_status",
        "score",
        "tool_match",
        "args_match",
        "facts_match",
        "groundedness",
        "citation_coverage",
        "replan_count",
        "mode",
        "duration_ms",
        "total_tokens",
        "cost_equivalent_usd",
        "model_actual",
        "trace_id",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})

    lines = [
        "# Resultados EFT — AgroID Huevos",
        "",
        f"Generado: {payload['generated_at']}",
        "",
        "## Suite real EFT",
        "",
        f"Corrida `{RUN_ID}` con `nvidia/nemotron-3.5-lightning:free`.",
        "",
        "| Turnos | Éxito | Bloqueados | Score | Tool | Args | Facts | Grounded | Citas | Tokens | Costo equiv. | Latencia media |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {overall['turns']} | {overall['success']} | {overall['blocked']} | "
        f"{overall['score']:.3f} | {overall['tool_match']:.3f} | "
        f"{overall['args_match']:.3f} | {overall['facts_match']:.3f} | "
        f"{overall['groundedness']:.3f} | {overall['citation_coverage']:.3f} | "
        f"{overall['tokens']:,} | USD {overall['cost_equivalent_usd']:.6f} | "
        f"{overall['latency_mean_s']:.2f} s |",
        "",
        "## Detalle por caso",
        "",
        "| Caso | Categoría | Estado | Score | Tool | Grounded | Citas | Replans | Latencia | Herramientas |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        tools = ", ".join(
            item.get("tool", "")
            for item in json.loads(row.get("tool_calls_json") or "[]")
        )
        lines.append(
            f"| {row['case_id']} | {row['category']} | {row['trace_status']} | "
            f"{row['score']:.3f} | {row['tool_match']:.3f} | "
            f"{row['groundedness']:.3f} | "
            f"{row['citation_coverage'] if row['citation_coverage'] is not None else '-'} | "
            f"{row['replan_count']} | {float(row['duration_ms'])/1000:.2f} s | "
            f"{tools or '-'} |"
        )
    if rag_summary:
        lines.extend(
            [
                "",
                "## Evaluación RAG híbrido",
                "",
                f"- Casos: {rag_summary.get('cases')}",
                f"- Recall@3: {rag_summary.get('recall_at_k')}",
                f"- Casos con fuente interna: {rag_summary.get('cases_with_internal')}",
                f"- Casos con fuente externa: {rag_summary.get('cases_with_external')}",
                f"- Integridad: {rag_summary.get('integrity_ok')}",
                f"- Latencia P50: {rag_summary.get('latency_p50_ms')} ms",
                "",
            ]
        )
    if prompt_eval:
        lines.extend(
            [
                "## Evaluación de prompts",
                "",
                f"- Rúbrica system v1: {prompt_eval['comparison']['baseline_system_v1']['score']}",
                f"- Rúbrica system v2: {prompt_eval['comparison']['current_system_v2']['score']}",
                f"- Regresión funcional (simulada): "
                f"{prompt_eval['functional_regression']['mean_score']}",
                "",
            ]
        )
    if planning_eval:
        lines.extend(
            [
                "## Comparación de modos",
                "",
                "| Modo | Casos | Score | Tool | Grounded | Iteraciones | Tokens | Replans |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for item in planning_eval.get("summary", []):
            lines.append(
                f"| {item['mode']} | {item['cases']} | {item['mean_score']:.3f} | "
                f"{item['mean_tool_match']:.3f} | {item['mean_groundedness']:.3f} | "
                f"{item['mean_iterations']} | {item['mean_tokens']:.0f} | "
                f"{item['replan_rate']:.2f} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Lectura",
            "",
            "La suite real EFT confirma que el agente usa herramientas, cita fuentes",
            "recuperadas y mantiene el bloqueo de seguridad. Las brechas visibles son",
            "la cobertura de citas (el modelo cita una fuente aunque recupere varias),",
            "la consulta ambigua E04 (herramienta adicional) y la groundedness de",
            "algunos turnos. Esas brechas alimentan la sección de mejoras del informe.",
            "",
            "## Archivos",
            "",
            "- `resultados_eft.json`: métricas, filas y trazas.",
            "- `resultados_eft.csv`: una fila por caso.",
            "- `RESULTADOS_EFT.md`: este documento.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    print(f"Markdown: {md_path}")
    print(json.dumps(overall, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
