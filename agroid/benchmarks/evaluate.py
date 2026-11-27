"""Evaluación objetiva de un turno contra un caso dorado.

Mide cuatro dimensiones:

- ``tool_match``: selección de herramientas.
- ``args_match``: argumentos críticos.
- ``facts_match``: cifras y estado de la base esperados.
- ``groundedness``: proporción de cifras de la respuesta respaldadas por
  resultados de herramientas o por el estado de la base.

No pretende sustituir la revisión humana de la calidad redaccional.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..agent import TurnResult
from ..db import norm_especie
from .cases import Case

_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_WRITE_TOOLS = {
    "registrar_produccion",
    "registrar_pedido",
    "despachar_pedido",
    "recordar_dato",
}


def parse_number(value: str) -> float:
    raw = value.strip()
    if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", raw):
        return float(raw.replace(".", ""))
    if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+", raw):
        return float(raw.replace(",", ""))
    if "," in raw:
        return float(raw.replace(".", "").replace(",", "."))
    return float(raw)


def extract_numbers(text: str) -> list[float]:
    if not text:
        return []
    cleaned = _DATE.sub(" ", str(text))
    numbers: list[float] = []
    for match in _NUMBER.findall(cleaned):
        token = match.strip()
        if not token or token in {"-", "."}:
            continue
        try:
            numbers.append(parse_number(token))
        except ValueError:
            continue
    return numbers


def normalize_species_set(value: Any) -> set[str]:
    tokens = re.split(r"[,;/]| y ", str(value or "").lower())
    result = set()
    for token in tokens:
        normalized = norm_especie(token)
        if normalized:
            result.add(normalized)
        elif token.strip() in {
            "gallina",
            "codorniz",
            "pato",
            "ganso",
            "guinea",
        }:
            result.add(token.strip())
    return result


def _db_matches(expected: dict[str, Any], snapshot: dict[str, Any]) -> tuple[int, int]:
    matched = total = 0
    for species, fields in (expected.get("especies") or {}).items():
        for field, value in fields.items():
            total += 1
            actual = (
                snapshot.get("especies", {})
                .get(species, {})
                .get(field)
            )
            if actual == value:
                matched += 1
    if "datos_count" in expected:
        total += 1
        matched += int(snapshot.get("datos_count") == expected["datos_count"])
    if "pedidos_pendientes_count" in expected:
        total += 1
        matched += int(
            len(snapshot.get("pedidos_pendientes", []))
            == expected["pedidos_pendientes_count"]
        )
    return matched, total


def _args_match(result: TurnResult, case: Case) -> float:
    if case.allow_safe_refusal and _is_safe_refusal(result):
        return 1.0
    if not case.expected_args:
        return 1.0
    actual_calls = list(result.tool_calls)
    used: set[int] = set()
    checks = passed = 0
    for tool_name, expected_args in case.expected_args.items():
        candidates = [
            (index, call)
            for index, call in enumerate(actual_calls)
            if call.get("tool") == tool_name and index not in used
        ]
        if not candidates:
            checks += len(expected_args)
            continue
        # Elige la llamada que más claves esperadas cumple.
        best_index, best_call, best_hits = None, None, -1
        for index, call in candidates:
            args = call.get("args") or {}
            hits = 0
            for key, expected in expected_args.items():
                if _single_arg_matches(key, expected, args.get(key)):
                    hits += 1
            if hits > best_hits:
                best_index, best_call, best_hits = index, call, hits
        if best_index is not None:
            used.add(best_index)
        for key, expected in expected_args.items():
            checks += 1
            if _single_arg_matches(
                key, expected, (best_call or {}).get("args", {}).get(key)
            ):
                passed += 1
    return round(passed / checks, 4) if checks else 1.0


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[_\-./]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _single_arg_matches(key: str, expected: Any, actual: Any) -> bool:
    if actual is None:
        return False
    if key == "especies":
        return normalize_species_set(expected) == normalize_species_set(actual)
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return float(actual) == float(expected)
        except (TypeError, ValueError):
            return False
    if isinstance(expected, str):
        expected_text = _normalize_text(expected)
        actual_text = _normalize_text(actual)
        return (
            expected_text == actual_text
            or expected_text in actual_text
            or actual_text in expected_text
        )
    return _normalize_text(expected) == _normalize_text(actual)


def _is_safe_refusal(result: TurnResult) -> bool:
    if result.status != "success" or result.tool_calls:
        return False
    response = _normalize_text(result.response)
    markers = (
        "no puedo",
        "no es valida",
        "no es valido",
        "no corresponde",
        "no es posible",
        "no acepta",
        "invalida",
        "invalido",
        "debe ser positiva",
        "debe ser positivo",
        "no existe",
        "no reconozco",
    )
    return any(marker in response for marker in markers)


def _facts_match(
    result: TurnResult, case: Case, snapshot: dict[str, Any]
) -> float:
    checks = passed = 0
    tool_text = " ".join(
        str(call.get("result", "")) for call in result.tool_calls
    )
    tool_numbers = set(extract_numbers(tool_text))
    for number in case.expected_numbers:
        checks += 1
        if any(abs(number - candidate) < 0.01 for candidate in tool_numbers):
            passed += 1
    matched, total = _db_matches(case.expected_db, snapshot)
    checks += total
    passed += matched
    if checks == 0:
        return 1.0
    return round(passed / checks, 4)


def _groundedness(
    result: TurnResult, snapshot: dict[str, Any], case: Case
) -> float:
    if result.status in {"blocked", "blocked_output"}:
        return 1.0
    if case.allow_safe_refusal and _is_safe_refusal(result):
        return 1.0
    response_numbers = extract_numbers(result.response)
    if not response_numbers:
        return 1.0
    sources = " ".join(
        [
            *[str(call.get("result", "")) for call in result.tool_calls],
            json.dumps(snapshot, ensure_ascii=False, default=str),
        ]
    )
    source_numbers = set(extract_numbers(sources))
    supported = sum(
        1
        for number in response_numbers
        if any(abs(number - candidate) < 0.01 for candidate in source_numbers)
    )
    return round(supported / len(response_numbers), 4)


def _tool_match(result: TurnResult, case: Case) -> float:
    actual = [name for name in result.tool_names if name]
    expected = list(case.expected_tools)

    if case.expected_blocked:
        return 1.0 if result.status in {"blocked", "blocked_output"} else 0.0

    if case.allow_safe_refusal and _is_safe_refusal(result):
        return 1.0

    if case.allow_clarification and not actual:
        response = (result.response or "").lower()
        asks = any(
            marker in response
            for marker in (
                "?",
                "especifica",
                "específica",
                "cuál",
                "cual",
                "qué especie",
                "que especie",
                "detalle",
                "no tengo",
                "necesito saber",
            )
        )
        return 1.0 if asks else 0.0

    if not expected:
        return 1.0 if not (set(actual) & _WRITE_TOOLS) else 0.0

    expected_set = set(expected)
    actual_set = set(actual)
    if expected_set == actual_set:
        return 1.0
    union = expected_set | actual_set
    return round(len(expected_set & actual_set) / len(union), 4) if union else 1.0


def evaluate(
    case: Case,
    result: TurnResult,
    snapshot_after: dict[str, Any],
) -> dict[str, Any]:
    tool_match = _tool_match(result, case)
    args_match = _args_match(result, case)
    facts_match = _facts_match(result, case, snapshot_after)
    groundedness = _groundedness(result, snapshot_after, case)

    if case.expected_blocked:
        score = 1.0 if result.status in {"blocked", "blocked_output"} else 0.0
    else:
        score = round(
            0.4 * tool_match
            + 0.3 * args_match
            + 0.2 * facts_match
            + 0.1 * groundedness,
            4,
        )

    notes = []
    if result.status != "success":
        notes.append(f"status={result.status}")
    if result.error_type:
        notes.append(f"error={result.error_type}")
    if case.consistency_group:
        notes.append(f"consistency_group={case.consistency_group}")
    if case.bias_pair:
        notes.append(f"bias_pair={case.bias_pair}")

    return {
        "case_id": case.id,
        "category": case.category,
        "experiment_group": case.group,
        "trace_id": result.trace_id,
        "tool_match": tool_match,
        "args_match": args_match,
        "facts_match": facts_match,
        "groundedness": groundedness,
        "citation_coverage": result.citation_coverage,
        "score": score,
        "consistency_group": case.consistency_group,
        "notes": "; ".join(notes),
        "status": result.status,
        "tool_names": result.tool_names,
        "mode": getattr(result, "mode", "") or result.requested_mode or result.status,
        "replan_count": result.replan_count,
        "rag_sources": [item.get("fragment_id") for item in result.rag_sources],
        "response_preview": (result.response or "")[:300],
    }
