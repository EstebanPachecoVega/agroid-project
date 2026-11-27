"""Comparación de modos react, plan y auto con LLM simulado.

Mide selección de herramientas, argumentos, hechos, iteraciones, latencia,
tokens y replanificación. La suite es funcional: no demuestra que un modelo
real planifique mejor, pero sí que el enrutamiento y los contratos no se rompen
y permite comparar el costo estructural de cada modo.

Uso:
    python -m agroid.benchmarks.planning_eval
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from typing import Any

os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGSMITH_API_KEY", "")
os.environ.setdefault("LLM_API_KEY", "")

from ..agent import reset_memories, run_turn  # noqa: E402
from ..benchmarks.cases import CASES  # noqa: E402
from ..benchmarks.evaluate import evaluate  # noqa: E402
from ..benchmarks.sim_llm import SimulatedLLM  # noqa: E402
from ..config import get_settings  # noqa: E402
from ..db import inicializar_bd, set_db_path, snapshot  # noqa: E402
from ..observability import store  # noqa: E402


CASE_IDS = ["N01", "N04", "E03", "E04", "E05"]
MODES = ["react", "plan", "auto"]


def run_comparison() -> dict[str, Any]:
    settings = get_settings()
    tmp = settings.eft_evidence_dir / "tmp_planning_eval"
    tmp.mkdir(parents=True, exist_ok=True)
    set_db_path(tmp / "agroid.db")
    store.set_obs_db_path(tmp / "observability.db")
    store.reset_store()
    llm = SimulatedLLM()
    rows: list[dict[str, Any]] = []
    for mode in MODES:
        for case_id in CASE_IDS:
            case = CASES[case_id]
            inicializar_bd(reset=True)
            reset_memories()
            result = run_turn(
                case.input,
                session_id=f"plan-{mode}-{case_id}",
                modo=mode,
                category=case.category,
                experiment_group=f"mode_{mode}",
                model="simulado",
                llm=llm,
            )
            evaluation = evaluate(case, result, snapshot())
            rows.append(
                {
                    "mode_requested": mode,
                    "mode_effective": result.mode,
                    "case_id": case_id,
                    "category": case.category,
                    "status": result.status,
                    "tool_match": evaluation["tool_match"],
                    "args_match": evaluation["args_match"],
                    "facts_match": evaluation["facts_match"],
                    "groundedness": evaluation["groundedness"],
                    "score": evaluation["score"],
                    "iterations": result.iterations,
                    "replan_count": result.replan_count,
                    "tokens": result.total_tokens,
                    "latency_ms": result.duration_ms,
                    "tools": ",".join(result.tool_names),
                    "plan_steps": len(result.plan.get("pasos", []))
                    if isinstance(result.plan, dict)
                    else 0,
                }
            )
    summary = []
    for mode in MODES:
        subset = [row for row in rows if row["mode_requested"] == mode]
        summary.append(
            {
                "mode": mode,
                "cases": len(subset),
                "mean_score": round(
                    sum(row["score"] for row in subset) / len(subset), 4
                ),
                "mean_tool_match": round(
                    sum(row["tool_match"] for row in subset) / len(subset), 4
                ),
                "mean_args_match": round(
                    sum(row["args_match"] for row in subset) / len(subset), 4
                ),
                "mean_groundedness": round(
                    sum(row["groundedness"] for row in subset) / len(subset),
                    4,
                ),
                "mean_iterations": round(
                    sum(row["iterations"] for row in subset) / len(subset), 2
                ),
                "mean_tokens": round(
                    sum(row["tokens"] for row in subset) / len(subset), 1
                ),
                "mean_latency_ms": round(
                    sum(row["latency_ms"] for row in subset) / len(subset), 2
                ),
                "replan_rate": round(
                    sum(1 for row in subset if row["replan_count"] > 0)
                    / len(subset),
                    4,
                ),
            }
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = settings.eft_evidence_dir / f"planning_eval_{stamp}.json"
    csv_path = settings.eft_evidence_dir / f"planning_eval_{stamp}.csv"
    json_path.write_text(
        json.dumps(
            {"summary": summary, "rows": rows},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return {
        "summary": summary,
        "rows": rows,
        "json": str(json_path),
        "csv": str(csv_path),
    }


def main() -> int:
    result = run_comparison()
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
    print("\nCasos:")
    for row in result["rows"]:
        print(
            f"  {row['mode_requested']:5s} {row['case_id']} "
            f"score={row['score']:.3f} tools={row['tools']} "
            f"replans={row['replan_count']} {row['latency_ms']:.0f} ms"
        )
    print(f"\nJSON: {result['json']}\nCSV: {result['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
