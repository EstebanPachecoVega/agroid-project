"""Evaluación de la estructura de prompts y regresión funcional.

La comparación de calidad con modelo real requiere cuota y debe ejecutarse con
``python -m agroid.benchmarks.run --mode real --suite eft``. Este script hace
dos cosas que sí se pueden reproducir sin red:

1. Audita cada prompt contra una rúbrica de rol, tarea, contexto, guardrails,
   formato, seguridad y pruebas.
2. Ejecuta una regresión funcional con LLM simulado para comprobar que el
   cambio de prompt no rompe el flujo de herramientas.

No presenta la regresión simulada como evidencia de calidad del modelo.
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

from ..config import get_settings
from ..prompts import PROMPT_REGISTRY, SYSTEM_V1  # noqa: E402


RUBRIC = [
    ("rol", 0.15, ("eres", "actúa", "asistente", "planificador", "monitor")),
    ("tarea", 0.15, ("responde", "busca", "plan", "decide", "revisa", "devuelve")),
    ("contexto", 0.15, ("{hoy}", "{datos_sesion}", "{resumen_sesion}", "{consulta}", "herramientas")),
    ("guardrails", 0.20, ("no inventes", "nunca", "no reveles", "no ejecutes", "cita", "error")),
    ("formato", 0.15, ("json", "frases", "respuesta", "formato", "pasos")),
    ("seguridad", 0.10, ("seguridad", "inyección", "instrucciones", "privacidad", "permiso")),
    ("pruebas", 0.10, ("test", "prueba", "criterio", "verificable", "[mxx]", "[exx]")),
]


def audit_prompt(template: str) -> dict[str, Any]:
    lower = template.lower()
    dimensions = {}
    total = 0.0
    for name, weight, markers in RUBRIC:
        hits = [marker for marker in markers if marker in lower]
        score = 1.0 if hits else 0.0
        dimensions[name] = {
            "score": score,
            "weight": weight,
            "matches": hits,
        }
        total += score * weight
    return {
        "score": round(total, 4),
        "dimensions": dimensions,
        "chars": len(template),
        "lines": len(template.splitlines()),
    }


def compare_prompts() -> dict[str, Any]:
    rows = []
    for name, spec in PROMPT_REGISTRY.items():
        audit = audit_prompt(spec.template)
        rows.append(
            {
                "prompt": name,
                "version": spec.version,
                "purpose": spec.purpose,
                "score": audit["score"],
                "chars": audit["chars"],
                "lines": audit["lines"],
                "guardrails": len(spec.guardrails),
                "tests": len(spec.tests),
                "dimensions": audit["dimensions"],
            }
        )
    baseline = audit_prompt(SYSTEM_V1)
    current = audit_prompt(PROMPT_REGISTRY["system_v2"].template)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_system_v1": baseline,
        "current_system_v2": current,
        "delta": round(current["score"] - baseline["score"], 4),
        "prompts": rows,
    }


def functional_regression() -> dict[str, Any]:
    """Regresión mínima con LLM simulado y el prompt EFT actual."""
    from ..agent import reset_memories, run_turn
    from ..benchmarks.cases import EFT_CASES
    from ..benchmarks.evaluate import evaluate
    from ..benchmarks.sim_llm import SimulatedLLM
    from ..db import inicializar_bd, snapshot, set_db_path
    from ..observability import store
    import tempfile
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    tmp = Path(tempfile.mkdtemp(prefix="agroid-prompt-"))
    set_db_path(tmp / "agroid.db")
    store.set_obs_db_path(tmp / "observability.db")
    store.reset_store()
    inicializar_bd(reset=True)
    reset_memories()
    llm = SimulatedLLM()
    results = []
    for case in EFT_CASES:
        result = run_turn(
            case.input,
            session_id=f"prompt-{case.id}",
            modo=case.mode,
            category=case.category,
            experiment_group="prompt_regression",
            model="simulado",
            llm=llm,
        )
        evaluation = evaluate(case, result, snapshot())
        results.append(
            {
                "case_id": case.id,
                "status": result.status,
                "tool_match": evaluation["tool_match"],
                "args_match": evaluation["args_match"],
                "facts_match": evaluation["facts_match"],
                "groundedness": evaluation["groundedness"],
                "score": evaluation["score"],
                "prompt_version": result.prompt_version,
            }
        )
    mean = lambda key: round(  # noqa: E731
        sum(float(row[key]) for row in results) / len(results), 4
    ) if results else 0.0
    return {
        "model": "simulado",
        "cases": len(results),
        "mean_tool_match": mean("tool_match"),
        "mean_args_match": mean("args_match"),
        "mean_facts_match": mean("facts_match"),
        "mean_groundedness": mean("groundedness"),
        "mean_score": mean("score"),
        "rows": results,
    }


def main() -> int:
    settings = get_settings()
    comparison = compare_prompts()
    regression = functional_regression()
    payload = {
        "comparison": comparison,
        "functional_regression": regression,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = settings.eft_evidence_dir / f"prompt_eval_{stamp}.json"
    csv_path = settings.eft_evidence_dir / f"prompt_eval_{stamp}.csv"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "prompt",
                "version",
                "score",
                "chars",
                "lines",
                "guardrails",
                "tests",
            ],
        )
        writer.writeheader()
        for row in comparison["prompts"]:
            writer.writerow(
                {
                    key: row[key]
                    for key in (
                        "prompt",
                        "version",
                        "score",
                        "chars",
                        "lines",
                        "guardrails",
                        "tests",
                    )
                }
            )
    print(json.dumps(
        {
            "baseline_system_v1": comparison["baseline_system_v1"]["score"],
            "current_system_v2": comparison["current_system_v2"]["score"],
            "delta": comparison["delta"],
            "functional_regression": {
                key: value
                for key, value in regression.items()
                if key != "rows"
            },
        },
        indent=2,
        ensure_ascii=False,
    ))
    print(f"\nJSON: {json_path}\nCSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
