"""Integridad del manual RAG mediante SHA-256 y HMAC opcional.

El manifiesto se genera al publicar el manual. En cada recuperación se
verifica que el texto no haya cambiado. Si un fragmento no coincide, se
excluye de la respuesta y se registra el incidente.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manual(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("fragments", [])
    if not isinstance(data, list):
        raise ValueError("El manual debe ser una lista o tener 'fragments'.")
    result = []
    for index, item in enumerate(data, start=1):
        if isinstance(item, str):
            result.append(
                {"id": f"M{index:02d}", "tema": "", "texto": item}
            )
        else:
            result.append(
                {
                    "id": str(item.get("id") or f"M{index:02d}"),
                    "tema": str(item.get("tema") or ""),
                    "texto": str(item.get("texto") or item.get("text") or ""),
                }
            )
    return result


def _canonical_payload(fragments: dict[str, str]) -> str:
    return "\n".join(f"{key}:{value}" for key, value in sorted(fragments.items()))


def build_manifest(
    fragments: Iterable[dict[str, Any]],
    hmac_key: str = "",
    version: int = 1,
) -> dict[str, Any]:
    hashes = {
        str(fragment["id"]): sha256_text(str(fragment["texto"]))
        for fragment in fragments
    }
    payload = _canonical_payload(hashes)
    signature = (
        hmac.new(
            hmac_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if hmac_key
        else None
    )
    return {
        "version": version,
        "algorithm": "sha256",
        "hmac_algorithm": "hmac-sha256" if hmac_key else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fragments": hashes,
        "hmac": signature,
    }


def save_manifest(manifest: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def load_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass
class IntegrityReport:
    ok: bool
    checked: int = 0
    mismatches: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    hmac_ok: bool = True
    reason: str = ""
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "mismatches": self.mismatches,
            "missing": self.missing,
            "extra": self.extra,
            "hmac_ok": self.hmac_ok,
            "reason": self.reason,
            "checked_at": self.checked_at,
        }


def verify_manual(
    fragments: Iterable[dict[str, Any]],
    manifest: dict[str, Any],
    hmac_key: str = "",
) -> IntegrityReport:
    expected: dict[str, str] = dict(manifest.get("fragments") or {})
    actual = {
        str(fragment["id"]): sha256_text(str(fragment["texto"]))
        for fragment in fragments
    }
    mismatches = sorted(
        key
        for key, value in expected.items()
        if key in actual and actual[key] != value
    )
    missing = sorted(key for key in expected if key not in actual)
    extra = sorted(key for key in actual if key not in expected)

    hmac_ok = True
    reason = ""
    if hmac_key:
        signature = manifest.get("hmac")
        payload = _canonical_payload(expected)
        computed = hmac.new(
            hmac_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        hmac_ok = bool(signature) and hmac.compare_digest(
            str(signature), computed
        )
        if not hmac_ok:
            reason = "firma_hmac_invalida"

    ok = not mismatches and not missing and not extra and hmac_ok
    if not reason:
        if mismatches:
            reason = "fragmentos_alterados"
        elif missing:
            reason = "fragmentos_faltantes"
        elif extra:
            reason = "fragmentos_nuevos_sin_manifiesto"
    return IntegrityReport(
        ok=ok,
        checked=len(actual),
        mismatches=mismatches,
        missing=missing,
        extra=extra,
        hmac_ok=hmac_ok,
        reason=reason,
    )


def verify_manual_file(
    manual_path: str | Path,
    manifest_path: str | Path,
    hmac_key: str = "",
    fragments: Iterable[dict[str, Any]] | None = None,
) -> IntegrityReport:
    try:
        loaded = list(fragments) if fragments is not None else load_manual(manual_path)
        manifest = load_manifest(manifest_path)
    except FileNotFoundError as exc:
        return IntegrityReport(
            ok=False,
            reason=f"archivo_no_encontrado:{Path(exc.filename or '').name}",
        )
    except (ValueError, json.JSONDecodeError) as exc:
        return IntegrityReport(ok=False, reason=f"manifiesto_invalido:{exc}")
    return verify_manual(loaded, manifest, hmac_key=hmac_key)


def write_manifest_for_file(
    manual_path: str | Path,
    manifest_path: str | Path,
    hmac_key: str = "",
) -> dict[str, Any]:
    fragments = load_manual(manual_path)
    manifest = build_manifest(fragments, hmac_key=hmac_key)
    save_manifest(manifest, manifest_path)
    return manifest
