"""Pruebas de memoria de sesión y continuidad en flujos prolongados."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGSMITH_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""

from agroid.config import reload_settings
from agroid.db import inicializar_bd, set_db_path, sql
from agroid.memory import SessionMemory

ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="agroid-memory-"))


def _setup():
    os.environ["AGROID_DATA_DIR"] = str(ROOT / "data")
    os.environ["AGROID_LOGS_DIR"] = str(TMP / "logs")
    reload_settings()
    set_db_path(TMP / "agroid.db")
    inicializar_bd(reset=True)


def _insert_turn(session: str, user: str, assistant: str):
    sql(
        "INSERT INTO historial (session_id, rol, contenido) VALUES (?,?,?)",
        (session, "humano", user),
        escribir=True,
    )
    sql(
        "INSERT INTO historial (session_id, rol, contenido) VALUES (?,?,?)",
        (session, "ia", assistant),
        escribir=True,
    )


def test_long_flow_summary_and_window():
    _setup()
    session = "long-flow"
    for index in range(1, 13):
        _insert_turn(
            session,
            f"Turno {index}: recuerda que el cliente Hotel Costa solo acepta pato.",
            f"Registrado el turno {index}. Queda stock de pato.",
        )
    memory = SessionMemory(session, window=5)
    messages = memory.messages()
    assert len(messages) == 10  # cinco pares
    summary = memory.summary()
    assert "Hotel Costa" in summary
    assert "pato" in summary.lower()
    assert memory.status()["summary_chars"] > 0


def test_summary_survives_memory_reset():
    _setup()
    session = "persist"
    for index in range(6):
        _insert_turn(
            session,
            f"Pedido urgente {index}: Clínica Sur necesita 900 huevos.",
            "Pedido registrado y priorizado.",
        )
    first = SessionMemory(session, window=5)
    assert first.summary()
    # Simula reinicio de runtime: nueva instancia sin caché en RAM.
    second = SessionMemory(session, window=5)
    assert second.summary() == first.summary()
    assert second.status()["messages_in_window"] == 10


def test_session_isolation():
    _setup()
    _insert_turn("s1", "Recuerda que Hotel Costa solo acepta pato.", "Ok.")
    _insert_turn("s2", "Recuerda que Clínica Sur pide gallina.", "Ok.")
    m1 = SessionMemory("s1")
    m2 = SessionMemory("s2")
    assert "Hotel Costa" in m1.summary()
    assert "Hotel Costa" not in m2.summary()
    assert "Clínica Sur" in m2.summary()

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
