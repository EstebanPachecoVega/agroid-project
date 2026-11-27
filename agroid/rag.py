"""Recuperación híbrida sobre fuentes internas y externas.

El pipeline combina:

- ``data/manual.json``: manual interno de AgroID Huevos (10 fragmentos).
- ``data/external_corpus.json``: corpus técnico externo citado (FAO, USDA,
  Codex, extensión universitaria, INIA), con paráfrasis breves y metadatos.

Cada corpus tiene su propio manifiesto SHA-256/HMAC. Si un fragmento cambia o
falta, se excluye y se registra el incidente. La búsqueda usa embeddings si
están disponibles; si no, TF-IDF. El resultado conserva ``source_type``,
``title``, ``url`` y ``year`` para que el agente pueda citar la procedencia.
"""

from __future__ import annotations

import hashlib
import os
import threading
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable

import numpy as np

from .config import get_settings
from .observability.logging import get_logger
from .security.injection import scan_untrusted
from .security.integrity import (
    IntegrityReport,
    load_manual,
    verify_manual_file,
)


@dataclass
class RetrievalHit:
    fragment_id: str
    tema: str
    texto: str
    score: float
    source_type: str = "interno"
    title: str = ""
    url: str = ""
    year: Any = ""
    author: str = ""
    nota: str = ""

    @property
    def citation(self) -> str:
        return f"[{self.fragment_id}]"

    def as_dict(self) -> dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "tema": self.tema,
            "texto": self.texto,
            "score": round(self.score, 4),
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "year": self.year,
            "author": self.author,
            "nota": self.nota,
            "citation": self.citation,
        }


@dataclass
class CorpusStatus:
    label: str
    path: str
    manifest_path: str
    fragments: int = 0
    allowed: int = 0
    integrity_ok: bool = False
    integrity_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": self.path,
            "manifest_path": self.manifest_path,
            "fragments": self.fragments,
            "allowed": self.allowed,
            "integrity_ok": self.integrity_ok,
            "integrity_reason": self.integrity_reason,
        }


class Recuperador:
    def __init__(
        self,
        manual_path: str | os.PathLike[str] | None = None,
        manifest_path: str | os.PathLike[str] | None = None,
        hmac_key: str | None = None,
        external_path: str | os.PathLike[str] | None = None,
        external_manifest_path: str | os.PathLike[str] | None = None,
        force_tfidf: bool = False,
    ) -> None:
        settings = get_settings()
        self.force_tfidf = force_tfidf
        self.manual_path = str(manual_path or settings.manual_path)
        self.manifest_path = str(manifest_path or settings.manifest_path)
        self.external_path = str(
            external_path or settings.external_corpus_path
        )
        self.external_manifest_path = str(
            external_manifest_path or settings.external_manifest_path
        )
        self.hmac_key = (
            settings.manifest_hmac_key if hmac_key is None else hmac_key
        )
        self._lock = threading.Lock()

        self.internal_fragments = load_manual(self.manual_path)
        self.external_fragments = self._load_external()
        self.fragments = self.internal_fragments + self.external_fragments
        self.internal_ids = {
            fragment["id"] for fragment in self.internal_fragments
        }
        self.external_ids = {
            fragment["id"] for fragment in self.external_fragments
        }
        self.fragmentos_por_id = {
            fragment["id"]: fragment for fragment in self.fragments
        }
        self.integrity: dict[str, IntegrityReport] = {}
        self.allowed_ids: set[str] = set()
        self._refresh_integrity(initial=True)

        self._log_integrity()
        self.cli = None
        self.tfidf = None
        self.M = None
        self.modo = "tfidf"
        self._init_retrieval()

    # ------------------------------------------------------------------
    # Carga e integridad
    # ------------------------------------------------------------------
    def _load_external(self) -> list[dict[str, Any]]:
        try:
            fragments = load_manual(self.external_path)
        except FileNotFoundError:
            get_logger().log(
                "rag.external.missing",
                level="WARNING",
                path=self.external_path,
            )
            return []
        except Exception as exc:
            get_logger().log(
                "rag.external.error",
                level="ERROR",
                error=f"{type(exc).__name__}: {str(exc)[:200]}",
            )
            return []
        for fragment in fragments:
            fragment.setdefault("source_type", "externo")
            fragment.setdefault(
                "tema", fragment.get("tema", "fuente externa")
            )
        return fragments

    def _verify_corpus(
        self, path: str, manifest_path: str, fragments: list[dict[str, Any]]
    ) -> IntegrityReport:
        return verify_manual_file(
            path,
            manifest_path,
            hmac_key=self.hmac_key,
            fragments=fragments,
        )

    def _refresh_integrity(self, initial: bool = False) -> None:
        internal = self._verify_corpus(
            self.manual_path, self.manifest_path, self.internal_fragments
        )
        external = self._verify_corpus(
            self.external_path,
            self.external_manifest_path,
            self.external_fragments,
        ) if self.external_fragments else IntegrityReport(
            ok=False, reason="corpus_externo_no_disponible"
        )
        self.integrity = {"interno": internal, "externo": external}
        allowed: set[str] = set()
        for label, fragments in (
            ("interno", self.internal_fragments),
            ("externo", self.external_fragments),
        ):
            report = self.integrity[label]
            # Si falta el manifiesto o está corrupto, se excluye el corpus
            # completo: es preferible una respuesta sin esa fuente a una
            # respuesta con contenido no verificado.
            blocked = set(report.mismatches) | set(report.missing)
            if not report.ok and not report.mismatches and not report.missing:
                blocked = {fragment["id"] for fragment in fragments}
            allowed |= {
                fragment["id"] for fragment in fragments
            } - blocked
        self.allowed_ids = allowed
        self._corpus_status = [
            CorpusStatus(
                label="interno",
                path=self.manual_path,
                manifest_path=self.manifest_path,
                fragments=len(self.internal_fragments),
                allowed=len(
                    [f for f in self.internal_fragments if f["id"] in allowed]
                ),
                integrity_ok=internal.ok,
                integrity_reason=internal.reason,
            ),
            CorpusStatus(
                label="externo",
                path=self.external_path,
                manifest_path=self.external_manifest_path,
                fragments=len(self.external_fragments),
                allowed=len(
                    [f for f in self.external_fragments if f["id"] in allowed]
                ),
                integrity_ok=external.ok,
                integrity_reason=external.reason,
            ),
        ]

    def _log_integrity(self) -> None:
        for label, report in self.integrity.items():
            try:
                from .observability import store

                payload = report.to_dict()
                payload["corpus"] = label
                store.record_integrity(payload)
            except Exception:
                pass
            get_logger().log(
                "rag.integrity",
                level="INFO" if report.ok else "ERROR",
                corpus=label,
                ok=report.ok,
                reason=report.reason,
                checked=report.checked,
                mismatches=report.mismatches,
                hmac_ok=report.hmac_ok,
            )

    def verify(self) -> dict[str, IntegrityReport]:
        before = {
            label: (report.ok, tuple(report.mismatches), tuple(report.missing))
            for label, report in self.integrity.items()
        }
        with self._lock:
            self._refresh_integrity()
            after = {
                label: (
                    report.ok,
                    tuple(report.mismatches),
                    tuple(report.missing),
                )
                for label, report in self.integrity.items()
            }
        if before != after:
            self._log_integrity()
        return self.integrity

    # ------------------------------------------------------------------
    # Inicialización de recuperación
    # ------------------------------------------------------------------
    @staticmethod
    def _document_text(fragment: dict[str, Any]) -> str:
        """Texto indexable: tema, título, autor y contenido.

        Los metadatos ayudan a consultas como "USDA" o "Codex", que no siempre
        aparecen en el cuerpo del fragmento. La respuesta sigue mostrando solo
        el texto, pero la recuperación aprovecha la procedencia.
        """
        parts = [
            str(fragment.get("tema", "")),
            str(fragment.get("title", "")),
            str(fragment.get("author", "")),
            str(fragment.get("texto", "")),
        ]
        return " ".join(part for part in parts if part)

    def _init_retrieval(self) -> None:
        settings = get_settings()
        documents = [self._document_text(fragment) for fragment in self.fragments]
        try:
            if self.force_tfidf:
                raise RuntimeError("TF-IDF forzado para evaluación reproducible")
            if not settings.llm_api_key:
                raise RuntimeError("sin LLM_API_KEY para embeddings")
            from openai import OpenAI

            self.cli = OpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
            )
            response = self.cli.embeddings.create(
                model=settings.llm_embed_model,
                input=documents,
            )
            self.M = self._unit(
                np.array([item.embedding for item in response.data])
            )
            self.modo = "embeddings"
        except Exception as exc:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self.tfidf = TfidfVectorizer(
                strip_accents="unicode", sublinear_tf=True
            )
            self.M = self.tfidf.fit_transform(documents)
            self.modo = "tfidf"
            get_logger().log(
                "rag.fallback",
                level="WARNING",
                mode="tfidf",
                reason=f"{type(exc).__name__}: {str(exc)[:200]}",
            )

    @staticmethod
    def _unit(matrix: np.ndarray) -> np.ndarray:
        return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------
    def _scores(self, consulta: str) -> np.ndarray:
        consulta = unicodedata.normalize("NFC", str(consulta or ""))
        if self.modo == "embeddings" and self.cli is not None:
            settings = get_settings()
            query = self.cli.embeddings.create(
                model=settings.llm_embed_model, input=[consulta]
            ).data[0].embedding
            return self.M @ self._unit(np.array([query]))[0]
        query_matrix = self.tfidf.transform([consulta])
        return (self.M @ query_matrix.T).toarray().ravel()

    def _hit_from_index(self, index: int, score: float) -> RetrievalHit:
        fragment = self.fragments[index]
        return RetrievalHit(
            fragment_id=str(fragment["id"]),
            tema=str(fragment.get("tema", "")),
            texto=str(fragment["texto"]),
            score=score,
            source_type=str(fragment.get("source_type", "interno")),
            title=str(fragment.get("title", "")),
            url=str(fragment.get("url", "")),
            year=fragment.get("year", ""),
            author=str(fragment.get("author", "")),
            nota=str(fragment.get("nota", "")),
        )

    def _is_allowed(self, hit: RetrievalHit) -> bool:
        if hit.fragment_id not in self.allowed_ids:
            return False
        scan = scan_untrusted(hit.texto)
        if scan.blocked:
            get_logger().log(
                "rag.fragment.blocked",
                level="WARNING",
                fragment_id=hit.fragment_id,
                score=scan.score,
                matches=scan.matches,
            )
            return False
        return True

    def buscar_detallado(
        self,
        consulta: str,
        k: int = 3,
        balance: bool = True,
        source_type: str | None = None,
        min_score: float | None = None,
    ) -> list[RetrievalHit]:
        """Busca en ambos corpus y devuelve hasta ``k`` fragmentos citables.

        ``balance=True`` procura incluir al menos un fragmento interno y uno
        externo cuando ambos superan el umbral. Así el agente no responde solo
        con el manual interno ni solo con documentación pública.
        """
        if not str(consulta or "").strip():
            return []
        consulta = unicodedata.normalize("NFC", str(consulta))
        k = max(1, min(6, int(k)))
        self.verify()
        try:
            scores = self._scores(consulta)
        except Exception as exc:
            get_logger().log(
                "rag.search.error",
                level="ERROR",
                error=f"{type(exc).__name__}: {str(exc)[:200]}",
            )
            return []

        threshold = min_score
        if threshold is None:
            threshold = 0.10 if self.modo == "tfidf" else 0.20

        candidates: list[RetrievalHit] = []
        for index in np.argsort(scores)[::-1]:
            score = float(scores[int(index)])
            if score <= threshold:
                continue
            hit = self._hit_from_index(int(index), score)
            if source_type and hit.source_type != source_type:
                continue
            if not self._is_allowed(hit):
                continue
            candidates.append(hit)

        selected: list[RetrievalHit] = []
        if balance and len(candidates) > 1 and k > 1:
            internal = [h for h in candidates if h.source_type == "interno"]
            external = [h for h in candidates if h.source_type == "externo"]
            if internal and external:
                selected = [internal[0], external[0]]
        for hit in candidates:
            if len(selected) >= k:
                break
            if all(existing.fragment_id != hit.fragment_id for existing in selected):
                selected.append(hit)
        selected = selected[:k]
        selected.sort(key=lambda item: item.score, reverse=True)

        get_logger().log(
            "rag.search",
            mode=self.modo,
            query_chars=len(consulta),
            hits=[hit.fragment_id for hit in selected],
            sources=[hit.source_type for hit in selected],
            scores=[round(hit.score, 4) for hit in selected],
            integrity_ok=all(
                report.ok for report in self.integrity.values()
            ),
        )
        return selected

    def buscar(self, consulta: str, k: int = 2) -> list[tuple[float, str]]:
        """Interfaz compatible con el notebook EP2: (puntaje, texto)."""
        return [
            (hit.score, hit.texto)
            for hit in self.buscar_detallado(consulta, k=k)
        ]

    def source_mix(self) -> dict[str, int]:
        internal = len([f for f in self.internal_fragments if f["id"] in self.allowed_ids])
        external = len([f for f in self.external_fragments if f["id"] in self.allowed_ids])
        return {
            "interno": internal,
            "externo": external,
            "total": internal + external,
        }

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.modo,
            "fragments": len(self.fragments),
            "allowed": len(self.allowed_ids),
            "source_mix": self.source_mix(),
            "corpora": [status.as_dict() for status in self._corpus_status],
            "integrity_ok": all(
                report.ok for report in self.integrity.values()
            ),
            "integrity_reason": "; ".join(
                f"{label}:{report.reason}"
                for label, report in self.integrity.items()
                if not report.ok
            ),
            "manual_path": self.manual_path,
            "manifest_path": self.manifest_path,
            "external_path": self.external_path,
            "external_manifest_path": self.external_manifest_path,
        }

    def cite_hits(self, hits: Iterable[RetrievalHit]) -> list[dict[str, Any]]:
        return [hit.as_dict() for hit in hits]


@lru_cache(maxsize=1)
def get_rag() -> Recuperador:
    return Recuperador()


def reset_rag() -> None:
    get_rag.cache_clear()
