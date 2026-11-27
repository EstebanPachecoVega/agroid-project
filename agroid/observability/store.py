"""Almacenamiento SQLite de observabilidad y evaluaciones.

La base es independiente de la base de negocio para que el dashboard pueda
leerse y respaldarse sin mezclar datos operativos.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..config import get_settings

_obs_path_override: Path | None = None


def set_obs_db_path(path: str | os.PathLike[str]) -> Path:
    global _obs_path_override
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    _obs_path_override = target
    return target


def reset_obs_db_path() -> None:
    global _obs_path_override
    _obs_path_override = None


def get_obs_db_path() -> Path:
    if _obs_path_override is not None:
        return _obs_path_override
    return get_settings().obs_db_path


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or get_obs_db_path()
    con = sqlite3.connect(target, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=10000")
    return con


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        started_at TEXT,
        ended_at TEXT,
        mode TEXT,
        suite TEXT,
        model_requested TEXT,
        model_pinned TEXT,
        git_commit TEXT,
        notes TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS traces (
        trace_id TEXT PRIMARY KEY,
        run_id TEXT,
        session_id TEXT,
        turn_id TEXT,
        started_at TEXT,
        ended_at TEXT,
        duration_ms REAL,
        mode TEXT,
        requested_mode TEXT,
        prompt_version TEXT,
        category TEXT,
        experiment_group TEXT,
        consistency_group TEXT,
        input_redacted TEXT,
        output_redacted TEXT,
        status TEXT,
        error_type TEXT,
        iterations INTEGER,
        tool_calls_json TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        cost_usd REAL,
        cost_equivalent_usd REAL,
        model_requested TEXT,
        model_actual TEXT,
        langsmith_trace_id TEXT,
        langsmith_run_id TEXT,
        security_json TEXT,
        anomalies_json TEXT,
        plan_json TEXT,
        replan_count INTEGER DEFAULT 0,
        rag_sources_json TEXT,
        citation_coverage REAL,
        context_budget_json TEXT,
        critic_json TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS spans (
        span_id TEXT PRIMARY KEY,
        trace_id TEXT,
        parent_span_id TEXT,
        name TEXT,
        kind TEXT,
        started_at TEXT,
        ended_at TEXT,
        duration_ms REAL,
        status TEXT,
        attributes_json TEXT,
        langsmith_run_id TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS llm_calls (
        span_id TEXT PRIMARY KEY,
        trace_id TEXT,
        parent_span_id TEXT,
        model_requested TEXT,
        model_actual TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        cost_usd REAL,
        cost_equivalent_usd REAL,
        latency_ms REAL,
        ttft_ms REAL,
        tokens_per_second REAL,
        finish_reason TEXT,
        status TEXT,
        estimated_tokens INTEGER,
        started_at TEXT,
        ended_at TEXT,
        attributes_json TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS tool_calls (
        span_id TEXT PRIMARY KEY,
        trace_id TEXT,
        parent_span_id TEXT,
        tool_name TEXT,
        args_json TEXT,
        result_summary TEXT,
        status TEXT,
        error_type TEXT,
        duration_ms REAL,
        started_at TEXT,
        ended_at TEXT,
        attributes_json TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS security_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        trace_id TEXT,
        session_id TEXT,
        event_type TEXT,
        severity TEXT,
        detail_json TEXT,
        action_taken TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        case_id TEXT,
        category TEXT,
        experiment_group TEXT,
        repetition INTEGER,
        trace_id TEXT,
        tool_match REAL,
        args_match REAL,
        facts_match REAL,
        groundedness REAL,
        consistency_group TEXT,
        score REAL,
        citation_coverage REAL,
        mode TEXT,
        replan_count INTEGER DEFAULT 0,
        rag_sources_json TEXT,
        notes TEXT,
        created_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS manual_integrity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checked_at TEXT,
        ok INTEGER,
        reason TEXT,
        detail_json TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS langsmith_runs (
        run_id TEXT PRIMARY KEY,
        trace_id TEXT,
        parent_run_id TEXT,
        name TEXT,
        run_type TEXT,
        start_time TEXT,
        end_time TEXT,
        total_tokens INTEGER,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_cost REAL,
        status TEXT,
        error TEXT,
        tags_json TEXT,
        extra_json TEXT,
        inputs_json TEXT,
        outputs_json TEXT,
        exported_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS ttft_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        measured_at TEXT,
        model TEXT,
        prompt_preview TEXT,
        ttft_ms REAL,
        total_ms REAL,
        completion_tokens INTEGER,
        tokens_per_second REAL,
        ms_per_token REAL,
        status TEXT,
        error TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_traces_started ON traces(started_at)",
    "CREATE INDEX IF NOT EXISTS idx_traces_run ON traces(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_llm_trace ON llm_calls(trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_tools_trace ON tool_calls(trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_security_trace ON security_events(trace_id)",
    "CREATE INDEX IF NOT EXISTS idx_evals_run ON evaluations(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_ls_trace ON langsmith_runs(trace_id)",
]


def init_store(path: str | os.PathLike[str] | None = None) -> Path:
    target = set_obs_db_path(path) if path else get_obs_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    con = _connect(target)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        for statement in SCHEMA:
            con.execute(statement)
        _migrate_trace_columns(con)
        con.commit()
    finally:
        con.close()
    return target


def _migrate_trace_columns(con: sqlite3.Connection) -> None:
    """Agrega columnas EFT a bases de observabilidad ya creadas."""
    existing = {
        row[1] for row in con.execute("PRAGMA table_info(traces)").fetchall()
    }
    additions = {
        "requested_mode": "TEXT",
        "prompt_version": "TEXT",
        "plan_json": "TEXT",
        "replan_count": "INTEGER DEFAULT 0",
        "rag_sources_json": "TEXT",
        "citation_coverage": "REAL",
        "context_budget_json": "TEXT",
        "critic_json": "TEXT",
    }
    for column, definition in additions.items():
        if column not in existing:
            con.execute(f"ALTER TABLE traces ADD COLUMN {column} {definition}")

    existing_eval = {
        row[1]
        for row in con.execute("PRAGMA table_info(evaluations)").fetchall()
    }
    eval_additions = {
        "citation_coverage": "REAL",
        "mode": "TEXT",
        "replan_count": "INTEGER DEFAULT 0",
        "rag_sources_json": "TEXT",
    }
    for column, definition in eval_additions.items():
        if column not in existing_eval:
            con.execute(
                f"ALTER TABLE evaluations ADD COLUMN {column} {definition}"
            )


def reset_store(path: str | os.PathLike[str] | None = None) -> Path:
    target = Path(path).expanduser().resolve() if path else get_obs_db_path()
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(target) + suffix)
        if candidate.exists():
            try:
                candidate.unlink()
            except OSError:
                pass
    return init_store(target)


def query(
    sql: str,
    params: Iterable[Any] = (),
    path: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    target = Path(path) if path else get_obs_db_path()
    con = _connect(target)
    try:
        cur = con.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]
    finally:
        con.close()


def execute(
    sql: str,
    params: Iterable[Any] = (),
    path: str | os.PathLike[str] | None = None,
) -> None:
    target = Path(path) if path else get_obs_db_path()
    con = _connect(target)
    try:
        con.execute(sql, tuple(params))
        con.commit()
    finally:
        con.close()


def _insert(table: str, values: dict[str, Any]) -> None:
    if not values:
        return
    columns = list(values.keys())
    placeholders = ",".join("?" for _ in columns)
    sql = (
        f"INSERT OR REPLACE INTO {table} "
        f"({','.join(columns)}) VALUES ({placeholders})"
    )
    execute(sql, [values[column] for column in columns])


def insert_run(run: dict[str, Any]) -> None:
    _insert("runs", run)


def insert_trace(trace: dict[str, Any]) -> None:
    _insert("traces", trace)


_TRACE_COLUMNS = {
    "run_id",
    "session_id",
    "turn_id",
    "started_at",
    "ended_at",
    "duration_ms",
    "mode",
    "requested_mode",
    "prompt_version",
    "category",
    "experiment_group",
    "consistency_group",
    "input_redacted",
    "output_redacted",
    "status",
    "error_type",
    "iterations",
    "tool_calls_json",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cost_usd",
    "cost_equivalent_usd",
    "model_requested",
    "model_actual",
    "langsmith_trace_id",
    "langsmith_run_id",
    "security_json",
    "anomalies_json",
    "plan_json",
    "replan_count",
    "rag_sources_json",
    "citation_coverage",
    "context_budget_json",
    "critic_json",
}


def update_trace(trace_id: str, values: dict[str, Any]) -> None:
    clean = {k: v for k, v in values.items() if k in _TRACE_COLUMNS}
    if not clean:
        return
    assignments = ",".join(f"{key}=?" for key in clean)
    execute(
        f"UPDATE traces SET {assignments} WHERE trace_id=?",
        [*clean.values(), trace_id],
    )


def insert_span(span: dict[str, Any]) -> None:
    _insert("spans", span)


def insert_llm_call(call: dict[str, Any]) -> None:
    _insert("llm_calls", call)


def insert_tool_call(call: dict[str, Any]) -> None:
    _insert("tool_calls", call)


def insert_security_event(event: dict[str, Any]) -> int:
    values = {
        "created_at": event.get("created_at") or utc_now(),
        "trace_id": event.get("trace_id", ""),
        "session_id": event.get("session_id", ""),
        "event_type": event.get("event_type", "unknown"),
        "severity": event.get("severity", "info"),
        "detail_json": _json(event.get("detail", {})),
        "action_taken": event.get("action_taken", ""),
    }
    con = _connect()
    try:
        cur = con.execute(
            "INSERT INTO security_events "
            "(created_at, trace_id, session_id, event_type, severity, "
            "detail_json, action_taken) VALUES (?,?,?,?,?,?,?)",
            tuple(values.values()),
        )
        con.commit()
        return int(cur.lastrowid or 0)
    finally:
        con.close()


def insert_evaluation(evaluation: dict[str, Any]) -> int:
    values = {
        "run_id": evaluation.get("run_id", ""),
        "case_id": evaluation.get("case_id", ""),
        "category": evaluation.get("category", ""),
        "experiment_group": evaluation.get("experiment_group", ""),
        "repetition": int(evaluation.get("repetition", 0) or 0),
        "trace_id": evaluation.get("trace_id", ""),
        "tool_match": float(evaluation.get("tool_match", 0.0) or 0.0),
        "args_match": float(evaluation.get("args_match", 0.0) or 0.0),
        "facts_match": float(evaluation.get("facts_match", 0.0) or 0.0),
        "groundedness": float(evaluation.get("groundedness", 0.0) or 0.0),
        "consistency_group": evaluation.get("consistency_group", ""),
        "score": float(evaluation.get("score", 0.0) or 0.0),
        "citation_coverage": (
            float(evaluation["citation_coverage"])
            if evaluation.get("citation_coverage") is not None
            else None
        ),
        "mode": evaluation.get("mode", ""),
        "replan_count": int(evaluation.get("replan_count", 0) or 0),
        "rag_sources_json": _json(evaluation.get("rag_sources", [])),
        "notes": evaluation.get("notes", ""),
        "created_at": evaluation.get("created_at") or utc_now(),
    }
    con = _connect()
    try:
        cur = con.execute(
            "INSERT INTO evaluations "
            "(run_id, case_id, category, experiment_group, repetition, "
            "trace_id, tool_match, args_match, facts_match, groundedness, "
            "consistency_group, score, citation_coverage, mode, replan_count, "
            "rag_sources_json, notes, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            tuple(values.values()),
        )
        con.commit()
        return int(cur.lastrowid or 0)
    finally:
        con.close()


def insert_langsmith_run(run: dict[str, Any]) -> None:
    _insert("langsmith_runs", run)


def insert_ttft(measurement: dict[str, Any]) -> int:
    values = {
        "measured_at": measurement.get("measured_at") or utc_now(),
        "model": measurement.get("model", ""),
        "prompt_preview": measurement.get("prompt_preview", ""),
        "ttft_ms": measurement.get("ttft_ms"),
        "total_ms": measurement.get("total_ms"),
        "completion_tokens": measurement.get("completion_tokens"),
        "tokens_per_second": measurement.get("tokens_per_second"),
        "ms_per_token": measurement.get("ms_per_token"),
        "status": measurement.get("status", ""),
        "error": measurement.get("error", ""),
    }
    con = _connect()
    try:
        cur = con.execute(
            "INSERT INTO ttft_measurements "
            "(measured_at, model, prompt_preview, ttft_ms, total_ms, "
            "completion_tokens, tokens_per_second, ms_per_token, status, error) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            tuple(values.values()),
        )
        con.commit()
        return int(cur.lastrowid or 0)
    finally:
        con.close()


def record_integrity(report: dict[str, Any]) -> None:
    execute(
        "INSERT INTO manual_integrity "
        "(checked_at, ok, reason, detail_json) VALUES (?,?,?,?)",
        (
            report.get("checked_at") or utc_now(),
            1 if report.get("ok") else 0,
            report.get("reason", ""),
            _json(report),
        ),
    )


def table(name: str, path: str | os.PathLike[str] | None = None):
    """Devuelve una tabla como DataFrame (importa pandas solo si se usa)."""
    import pandas as pd

    target = Path(path) if path else get_obs_db_path()
    con = sqlite3.connect(target)
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", con)
    finally:
        con.close()


def count(table_name: str) -> int:
    rows = query(f"SELECT COUNT(*) AS n FROM {table_name}")
    return int(rows[0]["n"]) if rows else 0
