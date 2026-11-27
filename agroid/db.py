"""Persistencia SQLite del negocio AgroID Huevos.

Se mantiene una única base para inventario, pedidos, movimientos, historial y
datos recordados. La base de observabilidad es independiente (ver
``agroid.observability.store``).
"""

from __future__ import annotations

import os
import sqlite3
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from .config import get_settings

ESPECIES = ["gallina", "codorniz", "pato", "ganso", "guinea"]
_RAICES = [
    ("guinea", "guinea"),
    ("codorn", "codorniz"),
    ("gallin", "gallina"),
    ("pato", "pato"),
    ("gans", "ganso"),
]

_db_path_override: Path | None = None


def set_db_path(path: str | os.PathLike[str]) -> Path:
    """Permite que los tests usen una base temporal."""
    global _db_path_override
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    _db_path_override = p
    return p


def reset_db_path() -> None:
    global _db_path_override
    _db_path_override = None


def get_db_path() -> Path:
    if _db_path_override is not None:
        return _db_path_override
    return get_settings().db_path


def norm_especie(texto: Any) -> str | None:
    """Normaliza una especie por raíz, sin acentos ni mayúsculas.

    ``'Huevos de codornices'`` -> ``'codorniz'``. Devuelve ``None`` si no
    reconoce ninguna especie.
    """
    t = unicodedata.normalize("NFKD", str(texto).lower()).encode(
        "ascii", "ignore"
    ).decode()
    for raiz, especie in _RAICES:
        if raiz in t:
            return especie
    return None


def sql(
    query: str,
    params: Iterable[Any] = (),
    escribir: bool = False,
) -> list[dict[str, Any]] | int:
    """Ejecuta SQL.

    - Lectura: lista de diccionarios.
    - Escritura: ``lastrowid`` (o 0 si la sentencia no inserta).
    """
    con = sqlite3.connect(get_db_path(), timeout=5)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA busy_timeout=5000")
        cur = con.execute(query, tuple(params))
        if escribir:
            con.commit()
            return int(cur.lastrowid or 0)
        return [dict(row) for row in cur.fetchall()]
    finally:
        con.close()


def inicializar_bd(reset: bool = False) -> None:
    """Crea las tablas y carga los datos de demostración si están vacías."""
    path = get_db_path()
    if reset:
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(path) + suffix)
            if candidate.exists():
                try:
                    candidate.unlink()
                except OSError:
                    pass

    for statement in [
        "CREATE TABLE IF NOT EXISTS especies ("
        " nombre TEXT PRIMARY KEY, stock INTEGER, huevos_dia INTEGER)",
        "CREATE TABLE IF NOT EXISTS pedidos ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, especie TEXT,"
        " cantidad INTEGER, fecha_limite TEXT, estado TEXT DEFAULT 'pendiente')",
        "CREATE TABLE IF NOT EXISTS movimientos ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, especie TEXT,"
        " delta INTEGER, motivo TEXT)",
        "CREATE TABLE IF NOT EXISTS historial ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, rol TEXT,"
        " contenido TEXT)",
        "CREATE TABLE IF NOT EXISTS datos ("
        " session_id TEXT, clave TEXT, valor TEXT,"
        " PRIMARY KEY (session_id, clave))",
        "CREATE TABLE IF NOT EXISTS memoria_resumen ("
        " session_id TEXT PRIMARY KEY, resumen TEXT, updated_at TEXT,"
        " turnos INTEGER DEFAULT 0)",
    ]:
        sql(statement, escribir=True)

    # WAL mejora la lectura concurrente del dashboard y de las pruebas de carga.
    con = sqlite3.connect(path, timeout=5)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
        con.commit()
    finally:
        con.close()

    if not sql("SELECT 1 FROM especies"):
        for especie, stock, huevos_dia in [
            ("gallina", 800, 300),
            ("codorniz", 1500, 400),
            ("pato", 200, 40),
            ("ganso", 20, 3),
            ("guinea", 60, 10),
        ]:
            sql(
                "INSERT INTO especies VALUES (?,?,?)",
                (especie, stock, huevos_dia),
                escribir=True,
            )
        hoy = date.today()
        for cliente, especie, cantidad, dias in [
            ("Restaurante Don Pepe", "gallina", 600, 2),
            ("Panadería La Espiga", "gallina", 1200, 5),
            ("Mayorista Andes", "codorniz", 2000, 4),
            ("Hotel Costa", "pato", 150, 3),
        ]:
            sql(
                "INSERT INTO pedidos "
                "(cliente, especie, cantidad, fecha_limite) "
                "VALUES (?,?,?,?)",
                (cliente, especie, cantidad, (hoy + timedelta(days=dias)).isoformat()),
                escribir=True,
            )


def reset_demo() -> None:
    inicializar_bd(reset=True)


def snapshot() -> dict[str, Any]:
    """Estado actual del negocio, útil para evaluar resultados de un turno."""
    especies = {
        row["nombre"]: {
            "stock": row["stock"],
            "huevos_dia": row["huevos_dia"],
        }
        for row in sql("SELECT nombre, stock, huevos_dia FROM especies")
    }
    pedidos = sql(
        "SELECT id, cliente, especie, cantidad, fecha_limite, estado "
        "FROM pedidos ORDER BY id"
    )
    movimientos = sql(
        "SELECT id, fecha, especie, delta, motivo FROM movimientos ORDER BY id"
    )
    return {
        "especies": especies,
        "pedidos": pedidos,
        "pedidos_pendientes": [
            p for p in pedidos if p.get("estado") == "pendiente"
        ],
        "movimientos": movimientos,
        "historial_count": int(
            (sql("SELECT COUNT(*) AS n FROM historial") or [{"n": 0}])[0]["n"]
        ),
        "datos_count": int(
            (sql("SELECT COUNT(*) AS n FROM datos") or [{"n": 0}])[0]["n"]
        ),
        "memoria_resumen_count": int(
            (
                sql("SELECT COUNT(*) AS n FROM memoria_resumen")
                or [{"n": 0}]
            )[0]["n"]
        ),
    }


def healthcheck() -> dict[str, Any]:
    """Comprueba que la base existe y tiene las tablas mínimas."""
    try:
        especies = sql("SELECT COUNT(*) AS n FROM especies")
        pedidos = sql("SELECT COUNT(*) AS n FROM pedidos")
        return {
            "ok": True,
            "db_path": str(get_db_path()),
            "especies": int(especies[0]["n"]),
            "pedidos": int(pedidos[0]["n"]),
        }
    except Exception as exc:  # pragma: no cover - diagnóstico
        return {
            "ok": False,
            "db_path": str(get_db_path()),
            "error": f"{type(exc).__name__}: {exc}",
        }
