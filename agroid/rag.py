"""Recuperación sobre el manual con verificación de integridad.

El manual vive en ``data/manual.json`` y su manifiesto SHA-256 en
``data/manual_manifest.json``. Si un fragmento cambió, se excluye de la
búsqueda y se registra el incidente. Si los embeddings no están disponibles,
se usa TF-IDF y se declara explícitamente.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

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

    def as_dict(self) -> dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "tema": self.tema,
            "texto": self.texto,
            "score": round(self.score, 4),
        }


class Recuperador:
    def __init__(
        self,
        manual_path: str | os.PathLike[str] | None = None,
        manifest_path: str | os.PathLike[str] | None = None,
        hmac_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self.manual_path = str(manual_path or settings.manual_path)
        self.manifest_path = str(manifest_path or settings.manifest_path)
        self.hmac_key = (
            settings.manifest_hmac_key if hmac_key is None else hmac_key
        )
        self.fragments = load_manual(self.manual_path)
        self.fragmentos_por_id = {
            fragment["id"]: fragment for fragment in self.fragments
        }
        self.integrity: IntegrityReport = verify_manual_file(
            self.manual_path,
            self.manifest_path,
            hmac_key=self.hmac_key,
            fragments=self.fragments,
        )
        self.allowed_ids = {
            fragment["id"] for fragment in self.fragments
        } - set(self.integrity.mismatches) - set(self.integrity.missing)
        self._lock = threading.Lock()
        self._log_integrity(self.integrity)
        self.tfidf = None
        self.M = None
        self.modo = "tfidf"
        self._init_retrieval()

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------
    def _init_retrieval(self) -> None:
        settings = get_settings()
        try:
            if not settings.llm_api_key:
                raise RuntimeError("sin LLM_API_KEY para embeddings")
            from openai import OpenAI

            self.cli = OpenAI(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
            )
            response = self.cli.embeddings.create(
                model=settings.llm_embed_model,
                input=[fragment["texto"] for fragment in self.fragments],
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
            self.M = self.tfidf.fit_transform(
                [fragment["texto"] for fragment in self.fragments]
            )
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
    # Integridad
    # ------------------------------------------------------------------
    def _log_integrity(self, report: IntegrityReport) -> None:
        try:
            from .observability import store

            store.record_integrity(report.to_dict())
        except Exception:
            pass
        get_logger().log(
            "rag.integrity",
            level="INFO" if report.ok else "ERROR",
            ok=report.ok,
            reason=report.reason,
            checked=report.checked,
            mismatches=report.mismatches,
            hmac_ok=report.hmac_ok,
        )

    def verify(self) -> IntegrityReport:
        report = verify_manual_file(
            self.manual_path,
            self.manifest_path,
            hmac_key=self.hmac_key,
            fragments=self.fragments,
        )
        with self._lock:
            changed = (
                report.mismatches != self.integrity.mismatches
                or report.missing != self.integrity.missing
                or report.ok != self.integrity.ok
            )
            self.integrity = report
            self.allowed_ids = {
                fragment["id"] for fragment in self.fragments
            } - set(report.mismatches) - set(report.missing)
        if changed:
            self._log_integrity(report)
        return report

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------
    def buscar_detallado(self, consulta: str, k: int = 2) -> list[RetrievalHit]:
        if not str(consulta or "").strip():
            return []
        k = max(1, min(5, int(k)))
        self.verify()
        try:
            if self.modo == "embeddings":
                settings = get_settings()
                query = self.cli.embeddings.create(
                    model=settings.llm_embed_model, input=[consulta]
                ).data[0].embedding
                scores = self.M @ self._unit(np.array([query]))[0]
            else:
                scores = (
                    self.M @ self.tfidf.transform([consulta]).T
                ).toarray().ravel()
        except Exception as exc:
            get_logger().log(
                "rag.search.error",
                level="ERROR",
                error=f"{type(exc).__name__}: {str(exc)[:200]}",
            )
            return []

        order = np.argsort(scores)[::-1]
        hits: list[RetrievalHit] = []
        for index in order:
            fragment = self.fragments[int(index)]
            score = float(scores[int(index)])
            if score <= 0:
                continue
            if fragment["id"] not in self.allowed_ids:
                continue
            # Defensa contra instrucciones escondidas en un documento.
            scan = scan_untrusted(fragment["texto"])
            if scan.blocked:
                get_logger().log(
                    "rag.fragment.blocked",
                    level="WARNING",
                    fragment_id=fragment["id"],
                    score=scan.score,
                    matches=scan.matches,
                )
                continue
            hits.append(
                RetrievalHit(
                    fragment_id=fragment["id"],
                    tema=fragment.get("tema", ""),
                    texto=fragment["texto"],
                    score=score,
                )
            )
            if len(hits) >= k:
                break
        get_logger().log(
            "rag.search",
            mode=self.modo,
            query_chars=len(consulta),
            hits=[hit.fragment_id for hit in hits],
            scores=[round(hit.score, 4) for hit in hits],
            integrity_ok=self.integrity.ok,
        )
        return hits

    def buscar(self, consulta: str, k: int = 2) -> list[tuple[float, str]]:
        """Interfaz compatible con el notebook EP2: (puntaje, texto)."""
        return [
            (hit.score, hit.texto)
            for hit in self.buscar_detallado(consulta, k=k)
        ]

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.modo,
            "fragments": len(self.fragments),
            "allowed": len(self.allowed_ids),
            "integrity_ok": self.integrity.ok,
            "integrity_reason": self.integrity.reason,
            "manual_path": self.manual_path,
            "manifest_path": self.manifest_path,
        }


@lru_cache(maxsize=1)
def get_rag() -> Recuperador:
    return Recuperador()


def reset_rag() -> None:
    get_rag.cache_clear()
