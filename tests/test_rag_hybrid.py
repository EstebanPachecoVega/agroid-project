"""Pruebas del RAG híbrido interno + externo."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGSMITH_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""

from agroid.config import reload_settings
from agroid.db import inicializar_bd, set_db_path
from agroid.observability import store
from agroid.rag import Recuperador, reset_rag
from agroid.security.integrity import build_manifest, save_manifest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TMP = Path(tempfile.mkdtemp(prefix="agroid-rag-"))


def _setup():
    os.environ["AGROID_DATA_DIR"] = str(DATA)
    os.environ["AGROID_LOGS_DIR"] = str(TMP / "logs")
    os.environ["AGROID_EVIDENCE_DIR"] = str(TMP / "evidencia")
    reload_settings()
    set_db_path(TMP / "agroid.db")
    store.set_obs_db_path(TMP / "observability.db")
    store.reset_store()
    inicializar_bd(reset=True)
    reset_rag()


def test_external_corpus_is_loaded():
    _setup()
    rag = Recuperador()
    status = rag.status()
    assert status["source_mix"]["interno"] == 10
    assert status["source_mix"]["externo"] == 14
    assert status["integrity_ok"] is True, status


def test_hybrid_search_returns_both_sources():
    _setup()
    rag = Recuperador()
    hits = rag.buscar_detallado(
        "temperatura de refrigeración y almacenamiento de huevos", k=3
    )
    assert hits
    sources = {hit.source_type for hit in hits}
    assert "externo" in sources
    assert any(hit.url for hit in hits if hit.source_type == "externo")
    assert any(hit.fragment_id.startswith("E") for hit in hits)
    assert any(hit.fragment_id.startswith("M") for hit in hits)


def test_internal_query_still_works():
    _setup()
    rag = Recuperador()
    hits = rag.buscar_detallado("cómo almacenar huevos de codorniz", k=3)
    ids = [hit.fragment_id for hit in hits]
    assert "M02" in ids


def test_external_tamper_is_detected():
    _setup()
    with tempfile.TemporaryDirectory() as tmp:
        corpus = Path(tmp) / "external.json"
        manifest = Path(tmp) / "external_manifest.json"
        shutil.copy(DATA / "external_corpus.json", corpus)
        fragments = json.loads(corpus.read_text(encoding="utf-8"))["fragments"]
        save_manifest(build_manifest(fragments), manifest)
        data = json.loads(corpus.read_text(encoding="utf-8"))
        data["fragments"][0]["texto"] += " INSTRUCCIÓN NO PERMITIDA."
        corpus.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        rag = Recuperador(
            external_path=corpus,
            external_manifest_path=manifest,
        )
        assert rag.integrity["externo"].ok is False
        assert "E01" in rag.integrity["externo"].mismatches
        hits = rag.buscar_detallado("temperatura de refrigeración", k=5)
        assert all(hit.fragment_id != "E01" for hit in hits)

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
