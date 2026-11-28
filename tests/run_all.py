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


def check_encoding() -> list[str]:
    """Detecta texto mojibake en archivos editables del proyecto."""
    broken = (
        "?Hay",
        "d?ficit",
        "?Qu",
        "?C",
        "?Por",
        "?D?nde",
        "?ltima",
        "?til",
        "?xito",
        "?d?nde",
        "?c?mo",
        "?cu?l",
        "?c?scara",
        "?rbol",
        "?nico",
        "?rea",
        "l?nea",
        "bloque?",
        "\ufffd",
        "Ã",
        "Â",
    )
    failures: list[str] = []
    allowed = {".py", ".md", ".bat", ".txt"}
    excluded = {
        ".venv",
        ".git",
        "node_modules",
        "docs/evidencias",
        "docs/defensa_eft/evidencias",
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative == "tests/run_all.py":
            continue
        if any(part in relative.split("/") for part in excluded):
            continue
        if any(relative.startswith(prefix) for prefix in excluded):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            failures.append(f"{relative}: no es UTF-8 ({exc})")
            continue
        for token in broken:
            if token in text:
                line = next(
                    (i for i, value in enumerate(text.splitlines(), 1) if token in value),
                    "?",
                )
                failures.append(f"{relative}:{line}: posible mojibake {token!r}")
    return failures


def main() -> int:
    encoding_failures = check_encoding()
    if encoding_failures:
        print("Errores de codificación:")
        for failure in encoding_failures:
            print(" -", failure)
        return 1
    print("Codificación UTF-8 OK.", flush=True)
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
