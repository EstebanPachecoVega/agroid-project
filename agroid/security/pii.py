"""Anonimización de datos personales (PII) antes de LLM, logs y trazas."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# RUT chileno con y sin puntos.
_RUT_DOTS = re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b")
_RUT_PLAIN = re.compile(r"\b\d{7,8}-[\dkK]\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
# Teléfonos chilenos: +56 9 1234 5678, 9 1234 5678, +56 2 2345 6789.
_PHONE = re.compile(
    r"(?:\+?56[\s.\-]?)?(?:9[\s.\-]?\d{4}[\s.\-]?\d{4}|"
    r"2[\s.\-]?\d{4}[\s.\-]?\d{4})\b"
)
_CARD_CANDIDATE = re.compile(r"\b(?:\d[ \-]?){13,19}\b")


def _luhn(number: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", number)]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


@dataclass
class RedactionResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)
    mapping: dict[str, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def had_pii(self) -> bool:
        return self.total > 0

    def public_counts(self) -> dict[str, int]:
        return {k: v for k, v in self.counts.items() if v}


def redact(text: Any) -> RedactionResult:
    """Reemplaza PII por marcadores estables dentro del texto.

    El mapeo marcador -> valor original queda solo en memoria y no debe
    persistirse. El texto redactado es el que viaja al LLM y a los logs.
    """
    original = "" if text is None else str(text)
    counts: dict[str, int] = {
        "rut": 0,
        "email": 0,
        "telefono": 0,
        "tarjeta": 0,
    }
    mapping: dict[str, str] = {}
    result = original

    def replace(pattern: re.Pattern[str], label: str, value: str) -> str:
        counts[label] += 1
        placeholder = f"[{label.upper()}_{counts[label]}]"
        mapping[placeholder] = value
        return placeholder

    result = _EMAIL.sub(
        lambda m: replace(_EMAIL, "email", m.group(0)), result
    )
    result = _RUT_DOTS.sub(
        lambda m: replace(_RUT_DOTS, "rut", m.group(0)), result
    )
    result = _RUT_PLAIN.sub(
        lambda m: replace(_RUT_PLAIN, "rut", m.group(0)), result
    )
    result = _PHONE.sub(
        lambda m: replace(_PHONE, "telefono", m.group(0)), result
    )

    def card_repl(match: re.Match[str]) -> str:
        value = match.group(0)
        if _luhn(value):
            return replace(_CARD_CANDIDATE, "tarjeta", value)
        return value

    result = _CARD_CANDIDATE.sub(card_repl, result)

    return RedactionResult(text=result, counts=counts, mapping=mapping)


def contains_pii(text: Any) -> bool:
    return redact(text).had_pii


def redact_obj(value: Any) -> Any:
    """Redacta recursivamente strings dentro de dicts/listas para logs."""
    if isinstance(value, str):
        return redact(value).text
    if isinstance(value, dict):
        return {str(k): redact_obj(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_obj(v) for v in value]
    return value
