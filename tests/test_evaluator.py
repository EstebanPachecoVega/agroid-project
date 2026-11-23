"""Pruebas del evaluador: normalización, rechazo seguro y argumentos."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGSMITH_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""

from agroid.agent import TurnResult
from agroid.benchmarks.cases import N05, N06
from agroid.benchmarks.evaluate import (
    _args_match,
    _normalize_text,
    _single_arg_matches,
    evaluate,
)


def _result(**kwargs) -> TurnResult:
    base = dict(
        response="",
        trace_id="t",
        session_id="s",
        turn_id="u",
        status="success",
    )
    base.update(kwargs)
    return TurnResult(**base)


def test_normalize_and_semantic_key():
    assert _normalize_text("cliente_Hotel_Costa_especie") == "cliente hotel costa especie"
    assert _single_arg_matches(
        "clave", "Hotel Costa", "cliente_Hotel_Costa_especie"
    )
    assert _single_arg_matches("especies", "codorniz y pato", "pato,codorniz")
    assert not _single_arg_matches("cantidad", 500, 400)


def test_safe_refusal_is_accepted():
    result = _result(
        response=(
            "No puedo registrar eso: la especie no es válida y la cantidad "
            "es inválida."
        ),
        tool_calls=[],
    )
    evaluation = evaluate(
        N06,
        result,
        {
            "especies": {
                "pato": {"stock": 200},
                "gallina": {"stock": 800},
            },
            "pedidos_pendientes": [],
            "datos_count": 0,
        },
    )
    assert evaluation["tool_match"] == 1.0
    assert evaluation["args_match"] == 1.0
    assert evaluation["groundedness"] == 1.0
    assert evaluation["score"] == 1.0


def test_semantic_key_counts_as_args_match():
    result = _result(
        response="Listo, lo recordaré.",
        tool_calls=[
            {
                "tool": "recordar_dato",
                "args": {
                    "clave": "cliente_Hotel_Costa_especie",
                    "valor": "Hotel Costa solo acepta huevos de pato",
                },
                "result": "OK: recordaré",
                "status": "success",
            }
        ],
    )
    assert _args_match(result, N05) == 1.0


def main():
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"{len(tests)} pruebas del evaluador aprobadas.")


if __name__ == "__main__":
    main()
