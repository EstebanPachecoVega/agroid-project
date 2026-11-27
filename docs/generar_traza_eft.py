"""Genera una corrida real corta EFT para capturas de traza y waterfall.

No reemplaza la suite completa de 8 casos: sirve para tener spans reales de
E01, E03 y E05 en SQLite y LangSmith, de modo que el dashboard pueda mostrar
un waterfall con datos de la entrega EFT.

Uso:
    python docs/generar_traza_eft.py --run-id real-eft-visual-20261127
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agroid.agent import reset_memories, run_turn  # noqa: E402
from agroid.benchmarks.cases import get_cases  # noqa: E402
from agroid.config import get_settings, reload_settings  # noqa: E402
from agroid.db import inicializar_bd  # noqa: E402
from agroid.observability import store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="real-eft-visual-20261127")
    parser.add_argument("--cases", default="E01,E03,E05")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    reload_settings()
    settings = get_settings()
    settings.configure_langsmith()
    model = args.model or settings.llm_model_pinned
    wanted = {item.strip() for item in args.cases.split(",") if item.strip()}
    cases = [case for case in get_cases("eft") if case.id in wanted]

    store.init_store()
    if not store.query("SELECT 1 FROM runs WHERE run_id=?", (args.run_id,)):
        store.insert_run(
            {
                "run_id": args.run_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "mode": "real",
                "suite": "eft",
                "model_requested": model,
                "model_pinned": settings.llm_model_pinned,
                "git_commit": "",
                "notes": "Corrida corta para spans y capturas de defensa",
            }
        )

    rows: list[dict[str, object]] = []
    for case in cases:
        inicializar_bd(reset=True)
        reset_memories()
        print(f"Ejecutando {case.id}: {case.input}")
        result = run_turn(
            case.input,
            session_id=f"visual-{case.id}",
            modo=case.mode,
            category=case.category,
            experiment_group=case.group,
            run_id=args.run_id,
            model=model,
        )
        rows.append(
            {
                "case_id": case.id,
                "trace_id": result.trace_id,
                "status": result.status,
                "mode": result.mode,
                "duration_ms": result.duration_ms,
                "tokens": result.total_tokens,
                "tools": [call.get("tool") for call in result.tool_calls],
                "output": result.response,
            }
        )
        print(
            f"  trace={result.trace_id} status={result.status} "
            f"{result.duration_ms/1000:.1f}s tokens={result.total_tokens}"
        )

    out = ROOT / "docs" / "evidencias_eft" / f"traza_{args.run_id}.json"
    out.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Guardado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
