"""Pruebas del catálogo de prompts EFT."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agroid.prompts import (
    PROMPT_REGISTRY,
    catalog,
    compare_versions,
    get_prompt,
    render,
)


def test_catalog_has_required_prompts():
    for name in ("system", "system_v2", "planner", "planner_v2", "monitor", "critic", "rag_answer"):
        assert name in PROMPT_REGISTRY, name
    rows = catalog()
    assert len(rows) >= 7
    assert all(row["id"] and row["version"] for row in rows)


def test_render_system_v2():
    text = render(
        "system_v2",
        hoy="2026-11-27",
        resumen_sesion="El cliente pidió 300 huevos.",
        datos_sesion="- Hotel Costa: solo pato",
    )
    assert "2026-11-27" in text
    assert "Hotel Costa" in text
    assert "Jerarquía de fuentes" in text
    assert "[Mxx]" in text and "[Exx]" in text


def test_render_missing_variable_fails():
    try:
        render("system_v2", hoy="2026-11-27")
    except ValueError as exc:
        assert "resumen_sesion" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Debió fallar por variable faltante")


def test_planner_v2_has_json_schema():
    spec = get_prompt("planner_v2")
    assert "objetivo" in spec.template
    assert "criterio_exito" in spec.template
    assert "fallback" in spec.template
    assert "requiere_confirmacion" in spec.template


def test_compare_versions():
    rows = compare_versions()
    assert len(rows) == 2
    assert all(row["v1"]["chars"] and row["v2"]["chars"] for row in rows)
    assert any("Jerarquía" in row["mejora"] for row in rows)

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
