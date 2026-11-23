"""Exporta trazas de LangSmith a JSONL y SQLite para el dashboard offline."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exportar runs de LangSmith")
    parser.add_argument("--project", default=None)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default=None)
    return parser.parse_args()


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _run_row(run: Any) -> dict[str, Any]:
    from agroid.security.pii import redact_obj

    error = _get(run, "error") or ""
    return {
        "run_id": str(_get(run, "id", "")),
        "trace_id": str(_get(run, "trace_id", "")),
        "parent_run_id": str(_get(run, "parent_run_id") or ""),
        "name": str(_get(run, "name", "")),
        "run_type": str(_get(run, "run_type", "")),
        "start_time": _iso(_get(run, "start_time")),
        "end_time": _iso(_get(run, "end_time")),
        "total_tokens": int(_get(run, "total_tokens") or 0),
        "prompt_tokens": int(_get(run, "prompt_tokens") or 0),
        "completion_tokens": int(_get(run, "completion_tokens") or 0),
        "total_cost": float(_get(run, "total_cost") or 0.0),
        "status": "error" if error else "success",
        "error": str(error),
        "tags_json": json.dumps(
            redact_obj(_get(run, "tags", []) or []), ensure_ascii=False
        ),
        "extra_json": json.dumps(
            redact_obj(_get(run, "extra", {}) or {}),
            ensure_ascii=False,
            default=str,
        ),
        "inputs_json": json.dumps(
            redact_obj(_get(run, "inputs", {}) or {}),
            ensure_ascii=False,
            default=str,
        ),
        "outputs_json": json.dumps(
            redact_obj(_get(run, "outputs", {}) or {}),
            ensure_ascii=False,
            default=str,
        ),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    from agroid.config import get_settings

    settings = get_settings()
    settings.configure_langsmith()
    if not settings.langsmith_api_key:
        print("Falta LANGSMITH_API_KEY; no se puede exportar.")
        return 1
    from langsmith import Client

    project = args.project or settings.langsmith_project
    start_time = datetime.now(timezone.utc) - timedelta(days=max(1, args.days))
    client = Client()
    rows: list[dict[str, Any]] = []
    try:
        # La API de LangSmith acepta como máximo 100 runs por consulta.
        limit = min(args.limit, 100) if args.limit else 100
        runs = client.list_runs(
            project_name=project,
            start_time=start_time,
            limit=limit,
        )
        for run in runs:
            rows.append(_run_row(run))
    except Exception as exc:
        print(f"Error al consultar LangSmith: {type(exc).__name__}: {exc}")
        return 2

    from agroid.observability import store

    store.init_store()
    for row in rows:
        store.insert_langsmith_run(row)

    evidence_dir = settings.evidence_dir
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output = Path(args.out) if args.out else (
        evidence_dir
        / f"langsmith_{project}_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.jsonl"
    )
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, default=str) + "\n"
            )
    print(f"Exportados {len(rows)} runs de '{project}' a {output}")
    print("También se guardaron en la tabla langsmith_runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
