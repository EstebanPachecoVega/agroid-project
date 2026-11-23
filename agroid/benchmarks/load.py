"""Prueba de carga con LLM simulado y sesiones concurrentes.

No consume cuota de OpenRouter ni envía trazas a LangSmith. Sirve para medir
latencia, errores y contención de SQLite antes de proponer Redis/Postgres.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from time import perf_counter

PROMPTS = [
    "¿Cuánto queda?",
    "¿Hay déficit con los pedidos pendientes?",
    "Prioriza los pedidos pendientes y dime cómo almacenar huevos de codorniz.",
    "Acabo de recolectar 100 huevos de gallina.",
    "Consulta los pedidos pendientes.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prueba de carga simulada")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LLM_API_KEY"] = ""
    os.environ["AGROID_RATE_LIMIT_TURNS_PER_DAY"] = "100000"
    os.environ["AGROID_RATE_LIMIT_PER_MINUTE"] = "100000"
    os.environ["AGROID_MAX_CONCURRENT"] = str(max(1, args.workers + 2))

    from agroid.config import get_settings, reload_settings

    reload_settings()
    settings = get_settings()
    from agroid.agent import reset_memories, run_turn
    from agroid.benchmarks.sim_llm import SimulatedLLM
    from agroid.db import inicializar_bd
    from agroid.observability import store
    from agroid.observability.metrics import percentile

    store.init_store()
    inicializar_bd(reset=True)
    reset_memories()
    run_id = args.run_id or (
        f"load-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    )
    llm = SimulatedLLM()

    def task(index: int) -> dict:
        prompt = PROMPTS[index % len(PROMPTS)]
        start = perf_counter()
        try:
            result = run_turn(
                prompt,
                session_id=f"load-{run_id}-{index}",
                category="carga",
                experiment_group="load",
                run_id=run_id,
                model="simulado",
                llm=llm,
            )
            return {
                "index": index,
                "status": result.status,
                "latency_ms": round((perf_counter() - start) * 1000, 2),
                "tokens": result.total_tokens,
                "tool_errors": sum(
                    1
                    for call in result.tool_calls
                    if call.get("status") == "error"
                ),
                "error": result.error,
            }
        except Exception as exc:
            return {
                "index": index,
                "status": "exception",
                "latency_ms": round((perf_counter() - start) * 1000, 2),
                "tokens": 0,
                "tool_errors": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(task, index) for index in range(args.requests)]
        for future in as_completed(futures):
            item = future.result()
            results.append(item)
            if item["status"] not in {"success", "blocked"}:
                print(
                    f"  request {item['index']}: {item['status']} "
                    f"({item['error'][:100]})"
                )

    latencies = [item["latency_ms"] for item in results]
    summary = {
        "run_id": run_id,
        "requests": len(results),
        "workers": args.workers,
        "success": sum(1 for r in results if r["status"] == "success"),
        "blocked": sum(1 for r in results if r["status"] == "blocked"),
        "exceptions": sum(1 for r in results if r["status"] == "exception"),
        "tool_errors": sum(int(r["tool_errors"]) for r in results),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "max_ms": max(latencies) if latencies else None,
        "total_tokens": sum(int(r["tokens"]) for r in results),
        "db_path": str(settings.db_path),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    output_dir = settings.evidence_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"load_{run_id}.json"
    json_path.write_text(
        json.dumps(
            {"summary": summary, "results": results},
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    csv_path = output_dir / f"load_{run_id}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"Evidencia: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
