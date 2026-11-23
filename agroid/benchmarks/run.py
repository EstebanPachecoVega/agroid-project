"""Runner de la suite EP3.

Uso:
    python -m agroid.benchmarks.run --mode sim --suite golden
    python -m agroid.benchmarks.run --mode real --suite router --model openrouter/free
    python -m agroid.benchmarks.run --mode real --suite pinned --model google/gemma-4-31b-it:free

El modo ``sim`` no usa red, no consume cuota y no envía trazas a LangSmith.
El modo ``real`` verifica la cuota gratuita de OpenRouter antes de empezar.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Suite de evaluación AgroID EP3")
    parser.add_argument("--mode", choices=["sim", "real"], default="sim")
    parser.add_argument(
        "--suite",
        default="golden",
        choices=[
            "golden",
            "router",
            "pinned",
            "consistency",
            "bias",
            "post_fix",
            "experiment",
        ],
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--pause", type=float, default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def _default_model(suite: str, settings: Any) -> str:
    if suite in {"pinned", "consistency", "bias", "post_fix"}:
        return settings.llm_model_pinned
    return settings.llm_model


def _openrouter_key_info(api_key: str) -> dict[str, Any] | None:
    if not api_key:
        return None
    from urllib.request import Request, urlopen

    request = Request(
        "https://openrouter.ai/api/v1/key",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
        return payload.get("data", payload)
    except Exception as exc:
        print(f"[aviso] No se pudo consultar la cuota de OpenRouter: {exc}")
        return None


def _quota_summary(info: dict[str, Any] | None) -> str:
    if not info:
        return "cuota desconocida"
    free = info.get("free_model_daily_requests") or {}
    return (
        f"free_model_daily_requests: used={free.get('used')} "
        f"limit={free.get('limit')} remaining={free.get('remaining')}; "
        f"is_free_tier={info.get('is_free_tier')}"
    )


def _progress_path(evidence_dir: Path, run_id: str) -> Path:
    return evidence_dir / f"progress_{run_id}.json"


def _load_progress(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    except Exception:
        return set()


def _save_progress(path: Path, run_id: str, completed: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "completed": sorted(completed),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_evidence(
    evidence_dir: Path,
    run_id: str,
    results: list[dict[str, Any]],
) -> tuple[Path, Path]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = evidence_dir / f"bench_{run_id}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for item in results:
            handle.write(
                json.dumps(item, ensure_ascii=False, default=str) + "\n"
            )
    csv_path = evidence_dir / f"bench_{run_id}.csv"
    if results:
        fields = list(results[0].keys())
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)
    else:
        csv_path.write_text("", encoding="utf-8")
    return jsonl_path, csv_path


def _print_summary(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No se ejecutaron casos.")
        return
    def mean(key: str) -> float:
        values = [float(item.get(key, 0.0)) for item in results]
        return sum(values) / len(values) if values else 0.0

    print("\nResumen de la corrida")
    print(f"  turnos: {len(results)}")
    print(f"  tool_match:   {mean('tool_match'):.3f}")
    print(f"  args_match:   {mean('args_match'):.3f}")
    print(f"  facts_match:  {mean('facts_match'):.3f}")
    print(f"  groundedness: {mean('groundedness'):.3f}")
    print(f"  score:        {mean('score'):.3f}")
    statuses: dict[str, int] = {}
    for item in results:
        statuses[item.get("status", "?")] = statuses.get(
            item.get("status", "?"), 0
        ) + 1
    print("  estados:", ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())))


def main() -> int:
    args = parse_args()

    # El modo simulado no debe consumir LangSmith ni la cuota real.
    if args.mode == "sim":
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LLM_API_KEY"] = ""
        os.environ["AGROID_RATE_LIMIT_TURNS_PER_DAY"] = "10000"
        os.environ["AGROID_RATE_LIMIT_PER_MINUTE"] = "10000"
        os.environ["AGROID_MAX_CONCURRENT"] = "20"
    else:
        os.environ.setdefault("LANGSMITH_TRACING", "true")

    from agroid.config import get_settings, reload_settings

    reload_settings()
    settings = get_settings()
    settings.configure_langsmith()

    from agroid.db import inicializar_bd, snapshot
    from agroid.observability import store
    from agroid.observability.metrics import kpis, load_frames
    from agroid.agent import reset_memories, run_turn
    from agroid.benchmarks.cases import (
        DEFAULT_REPETITIONS,
        get_cases,
    )
    from agroid.benchmarks.evaluate import evaluate
    from agroid.benchmarks.sim_llm import SimulatedLLM

    if args.reset:
        store.reset_store()
    else:
        store.init_store()

    cases = get_cases(args.suite)
    repetitions = (
        args.repetitions
        if args.repetitions is not None
        else DEFAULT_REPETITIONS.get(args.suite, 1)
    )
    model = args.model or (
        "simulado" if args.mode == "sim" else _default_model(args.suite, settings)
    )
    run_id = args.run_id or (
        f"{args.mode}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    )
    pause = args.pause if args.pause is not None else (
        0.0 if args.mode == "sim" else 4.0
    )
    evidence_dir = settings.evidence_dir
    progress_path = _progress_path(evidence_dir, run_id)
    completed = _load_progress(progress_path) if args.resume else set()

    if args.mode == "real":
        info = _openrouter_key_info(settings.llm_api_key)
        print("OpenRouter:", _quota_summary(info))
        expected_turns = len(cases) * repetitions
        if args.limit is not None:
            expected_turns = min(expected_turns, args.limit)
        expected_requests = expected_turns * 4 + 8
        free = (info or {}).get("free_model_daily_requests") or {}
        remaining = free.get("remaining")
        if (
            settings.is_free_model(model)
            and remaining is not None
            and remaining < expected_requests
            and not args.force
        ):
            print(
                f"[detenido] La cuota gratuita restante ({remaining}) es menor "
                f"que la estimación ({expected_requests} solicitudes). "
                "Ejecuta con --limit, espera al reinicio diario o usa --force."
            )
            return 2

    store.insert_run(
        {
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "mode": args.mode,
            "suite": args.suite,
            "model_requested": model,
            "model_pinned": settings.llm_model_pinned,
            "git_commit": _git_commit(),
            "notes": f"limit={args.limit} repetitions={repetitions}",
        }
    )

    llm = SimulatedLLM() if args.mode == "sim" else None
    results: list[dict[str, Any]] = []
    executed = 0

    print(
        f"Run {run_id} | mode={args.mode} suite={args.suite} "
        f"model={model} repetitions={repetitions}"
    )
    print("Casos:", ", ".join(case.id for case in cases))

    try:
        for case in cases:
            for repetition in range(1, repetitions + 1):
                if args.limit is not None and executed >= args.limit:
                    break
                key = f"{case.id}#{repetition}"
                if key in completed:
                    continue

                inicializar_bd(reset=True)
                reset_memories()

                # Prerrequisitos necesarios para memoria/persistencia.
                for prerequisite_text, prerequisite_mode in case.prerequisite:
                    run_turn(
                        prerequisite_text,
                        session_id=case.session,
                        modo=prerequisite_mode,
                        category="prerequisite",
                        experiment_group=case.group,
                        run_id=run_id,
                        model=model,
                        llm=llm,
                    )
                if case.clear_memory:
                    reset_memories()

                result = run_turn(
                    case.input,
                    session_id=f"{case.session}-{repetition}",
                    modo=case.mode,
                    verbose=args.verbose,
                    category=case.category,
                    experiment_group=case.group,
                    consistency_group=case.consistency_group,
                    run_id=run_id,
                    model=model,
                    llm=llm,
                )
                evaluation = evaluate(case, result, snapshot())
                evaluation.update(
                    {
                        "run_id": run_id,
                        "repetition": repetition,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "model_requested": model,
                        "mode": args.mode,
                        "duration_ms": result.duration_ms,
                        "total_tokens": result.total_tokens,
                        "cost_usd": result.cost_usd,
                        "cost_equivalent_usd": result.cost_equivalent_usd,
                        "iterations": result.iterations,
                        "model_actual": result.model_actual,
                        "response_preview": result.response[:300],
                    }
                )
                store.insert_evaluation(evaluation)
                results.append(evaluation)
                completed.add(key)
                _save_progress(progress_path, run_id, completed)
                executed += 1
                print(
                    f"  {key:10s} status={result.status:12s} "
                    f"score={evaluation['score']:.3f} "
                    f"tools={','.join(result.tool_names) or '-'} "
                    f"tokens={result.total_tokens} "
                    f"{result.duration_ms/1000:.1f}s"
                )
                if pause > 0:
                    time.sleep(pause)
            if args.limit is not None and executed >= args.limit:
                break
    except KeyboardInterrupt:
        print("\nInterrumpido. El progreso quedó guardado.")

    _write_evidence(evidence_dir, run_id, results)
    store.execute(
        "UPDATE runs SET ended_at=? WHERE run_id=?",
        [datetime.now(timezone.utc).isoformat(), run_id],
    )
    frames = load_frames()
    summary = kpis(frames)
    summary_path = evidence_dir / f"summary_{run_id}.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print("\nKPIs:", json.dumps(summary, indent=2, ensure_ascii=False))
    _print_summary(results)
    print(f"\nEvidencia: {evidence_dir}")
    return 0


def _git_commit() -> str:
    try:
        import subprocess

        output = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return output.strip()
    except Exception:
        return ""


if __name__ == "__main__":
    raise SystemExit(main())
