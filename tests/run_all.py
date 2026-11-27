"""Ejecuta todas las pruebas del proyecto en procesos separados.

Cada archivo configura sus propios directorios temporales y desactiva
LangSmith, por lo que no consumen cuota ni envían trazas.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    "tests/test_security.py",
    "tests/test_observability.py",
    "tests/test_tools.py",
    "tests/test_evaluator.py",
    "tests/test_agent_sim.py",
    "tests/test_prompts.py",
    "tests/test_rag_hybrid.py",
    "tests/test_planning.py",
    "tests/test_memory_long_flow.py",
    "tests/test_context_budget.py",
]


def main() -> int:
    failures = []
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    for test in TESTS:
        print("\n" + "=" * 72)
        print(test)
        print("=" * 72)
        result = subprocess.run(
            [sys.executable, str(ROOT / test)],
            cwd=ROOT,
            env=environment,
        )
        if result.returncode != 0:
            failures.append(test)
    print("\n" + "=" * 72)
    if failures:
        print("Fallaron:", ", ".join(failures))
        return 1
    print("Todas las pruebas aprobaron.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
