"""Pruebas del presupuesto de contexto."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage

from agroid.context_budget import (
    ContextBudget,
    estimate_tokens,
    trim_messages,
    trim_text,
)


def test_estimate_and_trim():
    assert estimate_tokens("12345678") == 2
    assert trim_text("abcdefghij", 6).endswith("…")
    assert len(trim_text("abcdefghij", 6)) == 6


def test_trim_messages_keeps_recent():
    messages = [
        HumanMessage(content="mensaje " + str(index) * 50)
        for index in range(10)
    ]
    kept = trim_messages(messages, max_tokens=120, min_keep=2)
    assert len(kept) < len(messages)
    assert kept[-1].content == messages[-1].content


def test_budget_report():
    budget = ContextBudget(max_history_tokens=80)
    history = budget.prepare_history(
        [HumanMessage(content="hola " * 100), AIMessage(content="respuesta")]
    )
    assert budget.report["history_messages_total"] == 2
    assert budget.report["history_messages_used"] >= 1
    assert budget.total_tokens_est() >= 0

def main():
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"{len(tests)} pruebas nuevas aprobadas.")


if __name__ == "__main__":
    main()
