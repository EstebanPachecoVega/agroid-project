"""Filtro de moderación y de temas ajenos al dominio de inventario de huevos."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_CATEGORIES: dict[str, tuple[float, list[str]]] = {
    "autolesion": (
        0.9,
        [
            r"\bsuicid\w*",
            r"\bautolesi\w*",
            r"\bcortarme\b",
            r"\bself[\s-]?harm\b",
        ],
    ),
    "violencia": (
        0.8,
        [
            r"\basesin\w*",
            r"\bmatar\b",
            r"\bviolencia\b",
            r"\barma\s+de\s+fuego\b",
            r"\bbomba\b",
            r"\bterroris\w*",
        ],
    ),
    "drogas": (
        0.7,
        [
            r"\bcocaina\b",
            r"\bmarihuana\b",
            r"\bdroga\w*",
            r"\bfentanilo\b",
        ],
    ),
    "odio": (
        0.8,
        [
            r"\bdiscurso\s+de\s+odio\b",
            r"\bgenocidio\b",
            r"\bsupremac\w*",
            r"\bnazi\w*",
        ],
    ),
    "sexual": (
        0.7,
        [
            r"\bpornograf\w*",
            r"\bcontenido\s+sexual\b",
        ],
    ),
    "ilegal": (
        0.6,
        [
            r"\bcomo\s+hackear\b",
            r"\bcomo\s+robar\b",
            r"\bblanqueo\s+de\s+dinero\b",
            r"\bevadir\s+impuestos\b",
        ],
    ),
}

_DOMAIN_KEYWORDS = {
    "huevo",
    "huevos",
    "gallina",
    "gallinas",
    "codorniz",
    "codornices",
    "pato",
    "patos",
    "ganso",
    "gansos",
    "guinea",
    "inventario",
    "stock",
    "pedido",
    "pedidos",
    "cliente",
    "produccion",
    "producción",
    "recoleccion",
    "recolección",
    "almacenamiento",
    "almacenar",
    "conservacion",
    "conservación",
    "incubacion",
    "incubación",
    "postura",
    "deficit",
    "déficit",
    "despacho",
    "despachar",
    "agroid",
}

_OFF_TOPIC_MARKERS = [
    "politica",
    "política",
    "elecciones",
    "religion",
    "religión",
    "futbol",
    "fútbol",
    "receta de cocina",
    "programa en python",
]


@dataclass
class ModerationResult:
    blocked: bool = False
    flagged: bool = False
    categories: list[str] = field(default_factory=list)
    off_topic: bool = False
    score: float = 0.0


def _norm(text: str) -> str:
    return (
        unicodedata.normalize("NFKD", (text or "").lower())
        .encode("ascii", "ignore")
        .decode()
    )


def check(text: str) -> ModerationResult:
    haystack = _norm(text)
    score = 0.0
    categories: list[str] = []
    for name, (weight, patterns) in _CATEGORIES.items():
        if any(re.search(pattern, haystack) for pattern in patterns):
            score = max(score, weight)
            categories.append(name)

    words = set(re.findall(r"[a-z0-9]+", haystack))
    has_domain = bool(words & _DOMAIN_KEYWORDS)
    off_topic = (
        not has_domain
        and any(marker in haystack for marker in _OFF_TOPIC_MARKERS)
    )
    return ModerationResult(
        blocked=score >= 0.7,
        flagged=bool(categories) or off_topic,
        categories=categories,
        off_topic=off_topic,
        score=round(score, 3),
    )


def safe_message(categories: list[str] | None = None) -> str:
    if categories:
        return (
            "No puedo ayudar con esa solicitud. Mi función es gestionar "
            "inventario, pedidos y producción de huevos de AgroID."
        )
    return (
        "Esa consulta está fuera de mi alcance. Puedo ayudarte con stock, "
        "pedidos, déficit, priorización y recomendaciones del manual de huevos."
    )
