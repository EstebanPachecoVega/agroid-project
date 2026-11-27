"""Importa la evidencia real EFT al SQLite de observabilidad.

La suite real se ejecutó y consolidó en `resultados_eft.json`. Si luego se
ejecuta la suite simulada con `--reset`, el store local se limpia. Este script
vuelve a insertar la corrida real para que el dashboard muestre ambas capas
sin necesidad de consumir cuota otra vez.

Uso:
    python docs/importar_evidencia_eft.py
"""

from __future__ import annotations

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agroid.observability import store  # noqa: E402


def main() -> int:
    payload = json.loads(
        (ROOT / "docs" / "evidencias_eft" / "resultados_eft.json").read_text(
            encoding="utf-8"
        )
    )
    run_id = payload["run_id"]
    store.init_store()
    if store.query("SELECT 1 FROM runs WHERE run_id=?", (run_id,)):
        print(f"La corrida {run_id} ya está en el store.")
        return 0
    store.insert_run(
        {
            "run_id": run_id,
            "started_at": payload.get("generated_at", ""),
            "ended_at": payload.get("generated_at", ""),
            "mode": "real",
            "suite": "eft",
            "model_requested": "nvidia/nemotron-3.5-lightning:free",
            "model_pinned": "nvidia/nemotron-3.5-lightning:free",
            "git_commit": "",
            "notes": "Evidencia real EFT importada desde resultados_eft.json",
        }
    )
    inserted = 0
    for row in payload.get("rows", []):
        trace_id = row.get("trace_id")
        if not trace_id:
            continue
        store.insert_trace(
            {
                "trace_id": trace_id,
                "run_id": run_id,
                "session_id": f"real-eft-{row.get('case_id', '')}",
                "turn_id": str(trace_id)[:12],
                "started_at": row.get("started_at", ""),
                "ended_at": row.get("started_at", ""),
                "duration_ms": row.get("duration_ms", 0),
                "mode": row.get("mode", "real"),
                "requested_mode": "real",
                "prompt_version": "v2",
                "category": row.get("category", ""),
                "experiment_group": row.get("experiment_group", "eft"),
                "consistency_group": row.get("consistency_group", ""),
                "input_redacted": "",
                "output_redacted": row.get("output_redacted", ""),
                "status": row.get("trace_status", ""),
                "error_type": "",
                "iterations": 0,
                "tool_calls_json": row.get("tool_calls_json", "[]"),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": row.get("total_tokens", 0),
                "cost_usd": row.get("cost_usd", 0),
                "cost_equivalent_usd": row.get("cost_equivalent_usd", 0),
                "model_requested": row.get("model_actual", ""),
                "model_actual": row.get("model_actual", ""),
                "langsmith_trace_id": "",
                "langsmith_run_id": "",
                "security_json": "{}",
                "anomalies_json": "{}",
                "plan_json": "{}",
                "replan_count": row.get("replan_count", 0),
                "rag_sources_json": row.get("rag_sources_json", "[]"),
                "citation_coverage": row.get("citation_coverage"),
                "context_budget_json": "{}",
                "critic_json": "{}",
            }
        )
        store.insert_evaluation(row)
        inserted += 1
    print(f"Corrida {run_id}: {inserted} casos importados al store.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
