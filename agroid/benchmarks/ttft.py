"""Medición de TTFT, latencia por token y throughput con streaming real."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

DEFAULT_PROMPTS = [
    "Explica en dos frases cómo se calcula el déficit de huevos pendientes.",
    "Resume qué recomienda el manual sobre almacenar huevos de codorniz.",
    "Enumera tres pasos para priorizar pedidos por fecha límite.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Medir TTFT con streaming")
    parser.add_argument("--model", default=None)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--prompt", action="append", default=None)
    parser.add_argument("--pause", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from agroid.config import get_settings

    settings = get_settings()
    settings.configure_langsmith()
    if not settings.llm_api_key:
        print("Falta LLM_API_KEY; no se puede medir TTFT.")
        return 1
    from agroid.agent import measure_ttft
    from agroid.observability import store

    store.init_store()
    prompts = args.prompt or DEFAULT_PROMPTS
    all_results = []
    for prompt_index, prompt in enumerate(prompts):
        if prompt_index > 0 and args.pause > 0:
            time.sleep(args.pause)
        result = measure_ttft(
            prompt,
            model=args.model or settings.llm_model,
            repetitions=max(1, args.repetitions),
            pause_s=args.pause,
        )
        result["prompt"] = prompt
        all_results.append(result)
        for run in result["runs"]:
            store.insert_ttft(
                {
                    "model": result["model"],
                    "prompt_preview": prompt[:200],
                    "ttft_ms": run.get("ttft_ms"),
                    "total_ms": run.get("total_ms"),
                    "completion_tokens": run.get("completion_tokens"),
                    "tokens_per_second": run.get("tokens_per_second"),
                    "ms_per_token": run.get("ms_per_token"),
                    "status": run.get("status"),
                    "error": run.get("error", ""),
                }
            )
        print(f"Prompt: {prompt[:60]}...")
        for run in result["runs"]:
            if run.get("status") == "success":
                print(
                    f"  TTFT={run['ttft_ms']} ms | "
                    f"total={run['total_ms']} ms | "
                    f"{run['tokens_per_second']} tok/s"
                )
            else:
                print(f"  error: {run.get('error')}")

    output = (
        settings.evidence_dir
        / f"ttft_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    )
    output.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"Guardado en {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
