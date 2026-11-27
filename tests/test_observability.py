"""Pruebas de logs JSON, store, trazabilidad, detectores y métricas."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGSMITH_API_KEY"] = ""

from agroid.config import get_settings, reload_settings
from agroid.observability import logging as obs_logging
from agroid.observability import metrics, store
from agroid.observability.detectors import detect_anomalies
from agroid.observability.tracing import (
    LLMCall,
    finish_turn,
    record_span,
    start_turn,
    utc_now,
)

TMP = Path(tempfile.mkdtemp(prefix="agroid-obs-"))


def _setup():
    os.environ["AGROID_DATA_DIR"] = str(TMP / "data")
    os.environ["AGROID_LOGS_DIR"] = str(TMP / "logs")
    os.environ["AGROID_EVIDENCE_DIR"] = str(TMP / "evidencia")
    reload_settings()
    store.set_obs_db_path(TMP / "observability.db")
    store.reset_store()
    obs_logging.set_log_path(TMP / "logs" / "test.jsonl")


def test_json_logger():
    _setup()
    record = obs_logging.log_event(
        "test.event", trace_id="abc", session_id="s1", value=42
    )
    assert record["event"] == "test.event"
    assert record["trace_id"] == "abc"
    lines = (TMP / "logs" / "test.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    last = json.loads(lines[-1])
    assert last["event"] == "test.event"
    assert last["value"] == 42


def test_trace_span_and_llm_store():
    _setup()
    state = start_turn(
        session_id="s1",
        mode="react",
        category="normal",
        experiment_group="test",
        run_id="run-test",
        input_redacted="hola",
        model_requested="openrouter/free",
    )
    store.insert_trace(state.trace_row())
    span = record_span(
        state,
        name="tool.consultar_stock",
        kind="tool",
        started_at=utc_now(),
        ended_at=utc_now(),
        duration_ms=12.5,
    )
    assert span is not None
    call = LLMCall(
        span_id="llm1",
        parent_span_id=state.root_span_id,
        model_requested="openrouter/free",
        model_actual="modelo-x",
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=120,
        cost_usd=0.0,
        cost_equivalent_usd=0.0001,
        latency_ms=500.0,
        started_at=utc_now(),
        ended_at=utc_now(),
    )
    state.add_llm(call)
    store.insert_llm_call(call.row(state.trace_id))
    finish_turn(state, "success", output="respuesta")
    store.update_trace(state.trace_id, state.trace_row())

    traces = store.query("SELECT * FROM traces")
    assert len(traces) == 1
    assert traces[0]["status"] == "success"
    assert traces[0]["total_tokens"] == 120
    assert len(store.query("SELECT * FROM spans")) >= 2
    assert len(store.query("SELECT * FROM llm_calls")) == 1


def test_detectors():
    state = start_turn(session_id="s2", mode="react", model_requested="x")
    state.iterations = 8
    first = state.note_action("consultar_stock", {"especie": "todas"})
    second = state.note_action("consultar_stock", {"especie": "todas"})
    assert first is False
    assert second is True
    state.add_llm(
        LLMCall(
            span_id="a",
            parent_span_id=state.root_span_id,
            model_requested="x",
            model_actual="x",
            prompt_tokens=100,
            completion_tokens=10,
            total_tokens=110,
            cost_usd=0.0,
            cost_equivalent_usd=0.0,
            latency_ms=10,
        )
    )
    state.add_llm(
        LLMCall(
            span_id="b",
            parent_span_id=state.root_span_id,
            model_requested="x",
            model_actual="y",
            prompt_tokens=2000,
            completion_tokens=10,
            total_tokens=2010,
            cost_usd=0.0,
            cost_equivalent_usd=0.0,
            latency_ms=10,
        )
    )
    report = detect_anomalies(state, max_iterations=8)
    assert report["flags"]["loop"]
    assert report["flags"]["max_iterations"]
    assert report["flags"]["context_drift"]
    assert report["flags"]["model_switch"]


def test_metrics_and_cost():
    _setup()
    state = start_turn(session_id="s3", mode="react", model_requested="openrouter/free")
    store.insert_trace(state.trace_row())
    call = LLMCall(
        span_id="m1",
        parent_span_id=state.root_span_id,
        model_requested="openrouter/free",
        model_actual="free-x",
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cost_usd=0.0,
        cost_equivalent_usd=0.0002,
        latency_ms=1000,
    )
    state.add_llm(call)
    finish_turn(state, "success", output="ok")
    store.update_trace(state.trace_id, state.trace_row())
    store.insert_evaluation(
        {
            "run_id": "r1",
            "case_id": "N01",
            "category": "normal",
            "experiment_group": "test",
            "repetition": 1,
            "trace_id": state.trace_id,
            "tool_match": 1.0,
            "args_match": 1.0,
            "facts_match": 0.5,
            "groundedness": 1.0,
            "score": 0.9,
        }
    )
    frames = metrics.load_frames()
    kpis = metrics.kpis(frames)
    assert kpis["traces"] == 1
    assert kpis["success_rate"] == 1.0
    assert kpis["total_tokens"] == 1500
    summary = metrics.evaluations_summary(frames)
    assert not summary.empty
    assert summary.iloc[0]["cases"] == 1

    settings = get_settings()
    free = settings.cost_for("openrouter/free", 1_000_000, 1_000_000)
    assert free["cost_usd"] == 0.0
    assert free["cost_equivalent_usd"] > 0
    paid = settings.cost_for("openai/gpt-4o-mini", 1_000_000, 1_000_000)
    assert paid["cost_usd"] > 0


def test_rag_source_mix_string_ids():
    """Las trazas importadas guardan IDs ("E05", "M01"), no diccionarios."""
    frame = pd.DataFrame(
        [
            {"rag_sources_json": '["E05", "E06", "M01"]'},
            {"rag_sources_json": '["M02", "E01"]'},
            {"rag_sources_json": "[]"},
        ]
    )
    mix = metrics.rag_source_mix({"traces": frame})
    counts = dict(zip(mix["source_type"], mix["fragments"]))
    assert counts["externo"] == 3
    assert counts["interno"] == 2
    assert set(mix["traces"]) == {2}


def main():
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"{len(tests)} pruebas de observabilidad aprobadas.")


if __name__ == "__main__":
    main()
