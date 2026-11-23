"""Herramientas del agente AgroID Huevos.

Cada herramienta valida entradas, captura excepciones y devuelve texto. Las
escrituras pasan por un límite por turno y los textos libres se revisan contra
inyección. La recuperación registra un span ``retriever`` propio.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from time import perf_counter
from typing import Any

from langchain_classic.agents import tool

from .context import (
    get_session_id,
    get_tool_context,
    get_turn_state,
)
from .db import ESPECIES, norm_especie, sql
from .observability import store
from .observability.logging import get_logger
from .observability.tracing import (
    current_run_info,
    record_span,
    utc_now,
)
from .rag import get_rag
from .security.injection import scan
from .security.pii import redact, redact_obj


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _entero(valor: Any, nombre: str) -> int:
    return int(valor)


def _dias_hasta(fecha_iso: str) -> int:
    return max(0, (date.fromisoformat(fecha_iso) - date.today()).days)


def _status(text: Any) -> str:
    return (
        "error"
        if str(text).strip().lower().startswith(("error", "⚠"))
        else "success"
    )


def _record(name: str, args: Any, output: Any) -> None:
    try:
        get_tool_context().record(name, redact_obj(args), _status(output))
    except Exception:
        pass


def _security_event(
    event_type: str,
    detail: dict[str, Any],
    action: str,
    severity: str = "warning",
) -> None:
    state = get_turn_state()
    try:
        store.insert_security_event(
            {
                "trace_id": getattr(state, "trace_id", ""),
                "session_id": get_session_id(),
                "event_type": event_type,
                "severity": severity,
                "detail": detail,
                "action_taken": action,
            }
        )
        get_logger().log(
            "security.event",
            level="WARNING",
            event_type=event_type,
            detail=detail,
            action_taken=action,
            trace_id=getattr(state, "trace_id", ""),
            session_id=get_session_id(),
        )
    except Exception:
        pass


def _reject_injection(text: Any, field: str) -> str | None:
    result = scan(str(text or ""))
    if result.blocked:
        _security_event(
            "tool_injection",
            {
                "field": field,
                "score": result.score,
                "matches": result.matches,
            },
            "tool_call_rejected",
        )
        return (
            f"Error: el contenido de '{field}' contiene instrucciones no "
            "permitidas. Reformula el dato como información del negocio."
        )
    return None


# ----------------------------------------------------------------------
# Consulta
# ----------------------------------------------------------------------
@tool
def consultar_stock(especie: str = "todas") -> str:
    """Consulta el stock actual de huevos y la producción diaria esperada.
    'especie' puede ser gallina, codorniz, pato, ganso, guinea o 'todas'."""
    args = {"especie": especie}
    out = ""
    try:
        invalid = _reject_injection(especie, "especie")
        if invalid:
            out = invalid
        elif str(especie).strip().lower() in ("", "todas", "todo", "todos"):
            out = _j(
                sql(
                    "SELECT nombre AS especie, stock, huevos_dia "
                    "FROM especies"
                )
            )
        else:
            normalized = norm_especie(especie)
            if not normalized:
                out = (
                    f"Error: especie '{especie}' no reconocida. "
                    f"Opciones: {', '.join(ESPECIES)}."
                )
            else:
                out = _j(
                    sql(
                        "SELECT nombre AS especie, stock, huevos_dia "
                        "FROM especies WHERE nombre=?",
                        (normalized,),
                    )
                )
    except Exception as exc:
        out = f"Error al consultar stock: {exc}"
    _record("consultar_stock", args, out)
    return out


@tool
def consultar_pedidos(estado: str = "pendiente") -> str:
    """Lista los pedidos de clientes. 'estado' puede ser 'pendiente',
    'cumplido' o 'todos'."""
    args = {"estado": estado}
    out = ""
    try:
        invalid = _reject_injection(estado, "estado")
        if invalid:
            out = invalid
        elif str(estado).lower() == "todos":
            rows = sql("SELECT * FROM pedidos ORDER BY fecha_limite")
            out = _j(rows) if rows else "No hay pedidos registrados."
        else:
            rows = sql(
                "SELECT * FROM pedidos WHERE estado=? ORDER BY fecha_limite",
                (str(estado).lower(),),
            )
            out = _j(rows) if rows else "No hay pedidos con ese estado."
    except Exception as exc:
        out = f"Error al consultar pedidos: {exc}"
    _record("consultar_pedidos", args, out)
    return out


# ----------------------------------------------------------------------
# Escritura
# ----------------------------------------------------------------------
@tool
def registrar_produccion(especie: str, cantidad: int) -> str:
    """Registra huevos recién recolectados y SUMA esa cantidad al stock de la
    especie. Usar cuando el usuario diga que recolectó o produjo huevos."""
    args = {"especie": especie, "cantidad": cantidad}
    out = ""
    try:
        limit = get_tool_context().guard_write("registrar_produccion")
        if limit:
            out = limit
        else:
            invalid = _reject_injection(especie, "especie")
            if invalid:
                out = invalid
            else:
                normalized = norm_especie(especie)
                number = _entero(cantidad, "cantidad")
                if not normalized:
                    out = (
                        f"Error: especie '{especie}' no reconocida. "
                        f"Opciones: {', '.join(ESPECIES)}. No se modificó nada."
                    )
                elif number <= 0 or number > 100000:
                    out = (
                        f"Error: cantidad inválida ({number}); debe estar "
                        "entre 1 y 100000. No se modificó nada."
                    )
                else:
                    sql(
                        "UPDATE especies SET stock = stock + ? "
                        "WHERE nombre=?",
                        (number, normalized),
                        escribir=True,
                    )
                    sql(
                        "INSERT INTO movimientos "
                        "(fecha, especie, delta, motivo) VALUES (?,?,?,?)",
                        (
                            date.today().isoformat(),
                            normalized,
                            number,
                            "producción",
                        ),
                        escribir=True,
                    )
                    get_tool_context().confirm_write()
                    stock = sql(
                        "SELECT stock FROM especies WHERE nombre=?",
                        (normalized,),
                    )[0]["stock"]
                    out = (
                        f"OK: se sumaron {number} huevos de {normalized}. "
                        f"Stock actual de {normalized}: {stock}."
                    )
    except Exception as exc:
        out = f"Error al registrar producción: {exc}. No se modificó nada."
    _record("registrar_produccion", args, out)
    return out


@tool
def registrar_pedido(
    cliente: str, especie: str, cantidad: int, dias_plazo: int
) -> str:
    """Registra un pedido nuevo de un cliente: especie, cantidad de huevos y
    plazo en días desde hoy."""
    args = {
        "cliente": cliente,
        "especie": especie,
        "cantidad": cantidad,
        "dias_plazo": dias_plazo,
    }
    out = ""
    try:
        limit = get_tool_context().guard_write("registrar_pedido")
        if limit:
            out = limit
        else:
            invalid = _reject_injection(cliente, "cliente") or _reject_injection(
                especie, "especie"
            )
            if invalid:
                out = invalid
            else:
                normalized = norm_especie(especie)
                number = _entero(cantidad, "cantidad")
                days = _entero(dias_plazo, "dias_plazo")
                client = redact(str(cliente)).text.strip()
                if not normalized:
                    out = (
                        f"Error: especie '{especie}' no reconocida. "
                        f"Opciones: {', '.join(ESPECIES)}."
                    )
                elif number <= 0 or days < 0 or not client:
                    out = (
                        "Error: se requiere cliente, cantidad > 0 y plazo "
                        ">= 0 días. No se registró el pedido."
                    )
                else:
                    limit_date = (
                        date.today() + timedelta(days=days)
                    ).isoformat()
                    pedido_id = sql(
                        "INSERT INTO pedidos "
                        "(cliente, especie, cantidad, fecha_limite) "
                        "VALUES (?,?,?,?)",
                        (client, normalized, number, limit_date),
                        escribir=True,
                    )
                    get_tool_context().confirm_write()
                    out = (
                        f"OK: pedido #{pedido_id} registrado ({client}: "
                        f"{number} huevos de {normalized}, entrega antes de "
                        f"{limit_date})."
                    )
    except Exception as exc:
        out = f"Error al registrar pedido: {exc}. No se registró nada."
    _record("registrar_pedido", args, out)
    return out


@tool
def despachar_pedido(pedido_id: int) -> str:
    """Despacha un pedido pendiente: descuenta el stock y lo marca como
    cumplido. Falla si el stock no alcanza."""
    args = {"pedido_id": pedido_id}
    out = ""
    try:
        limit = get_tool_context().guard_write("despachar_pedido")
        if limit:
            out = limit
        else:
            pid = _entero(pedido_id, "pedido_id")
            rows = sql("SELECT * FROM pedidos WHERE id=?", (pid,))
            if not rows:
                out = f"Error: no existe el pedido #{pid}."
            else:
                pedido = rows[0]
                if pedido["estado"] != "pendiente":
                    out = (
                        f"Error: el pedido #{pid} ya está "
                        f"'{pedido['estado']}'."
                    )
                else:
                    stock = sql(
                        "SELECT stock FROM especies WHERE nombre=?",
                        (pedido["especie"],),
                    )[0]["stock"]
                    if stock < pedido["cantidad"]:
                        out = (
                            f"Error: stock insuficiente de "
                            f"{pedido['especie']}: hay {stock}, el pedido "
                            f"requiere {pedido['cantidad']} (faltan "
                            f"{pedido['cantidad'] - stock}). No se despachó."
                        )
                    else:
                        sql(
                            "UPDATE especies SET stock = stock - ? "
                            "WHERE nombre=?",
                            (pedido["cantidad"], pedido["especie"]),
                            escribir=True,
                        )
                        sql(
                            "UPDATE pedidos SET estado='cumplido' WHERE id=?",
                            (pid,),
                            escribir=True,
                        )
                        sql(
                            "INSERT INTO movimientos "
                            "(fecha, especie, delta, motivo) "
                            "VALUES (?,?,?,?)",
                            (
                                date.today().isoformat(),
                                pedido["especie"],
                                -pedido["cantidad"],
                                f"despacho pedido #{pid}",
                            ),
                            escribir=True,
                        )
                        get_tool_context().confirm_write()
                        out = (
                            f"OK: pedido #{pid} despachado a "
                            f"{pedido['cliente']}. Stock restante de "
                            f"{pedido['especie']}: "
                            f"{stock - pedido['cantidad']}."
                        )
    except Exception as exc:
        out = f"Error al despachar: {exc}. No se modificó nada."
    _record("despachar_pedido", args, out)
    return out


@tool
def recordar_dato(clave: str, valor: str) -> str:
    """Guarda en la memoria de largo plazo un dato o preferencia que el usuario
    pide recordar (por ejemplo una condición de un cliente). Persiste dentro de
    la misma sesión."""
    args = {"clave": clave, "valor": valor}
    out = ""
    try:
        limit = get_tool_context().guard_write("recordar_dato")
        if limit:
            out = limit
        else:
            invalid = _reject_injection(clave, "clave") or _reject_injection(
                valor, "valor"
            )
            if invalid:
                out = invalid
            else:
                safe_key = redact(str(clave)).text[:60]
                safe_value = redact(str(valor)).text[:300]
                sql(
                    "INSERT OR REPLACE INTO datos VALUES (?,?,?)",
                    (get_session_id(), safe_key, safe_value),
                    escribir=True,
                )
                get_tool_context().confirm_write()
                out = f"OK: recordaré '{safe_key}': {safe_value}."
    except Exception as exc:
        out = f"Error al guardar el dato: {exc}"
    _record("recordar_dato", args, out)
    return out


# ----------------------------------------------------------------------
# Razonamiento
# ----------------------------------------------------------------------
@tool
def evaluar_cumplimiento(
    cantidad_requerida: int, especies: str, dias: int = 0
) -> str:
    """Evalúa si se puede reunir 'cantidad_requerida' de huevos sumando el
    stock de una o varias especies (ej. especies='codorniz,pato') más la
    producción esperada en 'dias' días. Devuelve si cumple y el déficit."""
    args = {
        "cantidad_requerida": cantidad_requerida,
        "especies": especies,
        "dias": dias,
    }
    out = ""
    try:
        invalid = _reject_injection(especies, "especies")
        required = _entero(cantidad_requerida, "cantidad_requerida")
        days = max(0, _entero(dias, "dias"))
        if invalid:
            out = invalid
        elif required <= 0:
            out = "Error: la cantidad requerida debe ser mayor que 0."
        else:
            species_list: list[str] = []
            for token in str(especies).replace(" y ", ",").split(","):
                normalized = norm_especie(token)
                if normalized and normalized not in species_list:
                    species_list.append(normalized)
            if not species_list:
                out = (
                    f"Error: no reconocí ninguna especie en '{especies}'. "
                    f"Opciones: {', '.join(ESPECIES)}."
                )
            else:
                detail, today_total, projected = [], 0, 0
                for normalized in species_list:
                    row = sql(
                        "SELECT stock, huevos_dia FROM especies "
                        "WHERE nombre=?",
                        (normalized,),
                    )[0]
                    production = row["huevos_dia"] * days
                    detail.append(
                        {
                            "especie": normalized,
                            "stock": row["stock"],
                            "produccion_en_plazo": production,
                        }
                    )
                    today_total += row["stock"]
                    projected += row["stock"] + production
                out = _j(
                    {
                        "requerido": required,
                        "dias": days,
                        "disponible_hoy": today_total,
                        "proyectado_al_plazo": projected,
                        "cumple_solo_con_stock": today_total >= required,
                        "cumple_con_produccion": projected >= required,
                        "deficit_con_stock": max(0, required - today_total),
                        "deficit_con_produccion": max(0, required - projected),
                        "detalle": detail,
                    }
                )
    except Exception as exc:
        out = f"Error al evaluar cumplimiento: {exc}"
    _record("evaluar_cumplimiento", args, out)
    return out


@tool
def calcular_deficit(dias: int = 0) -> str:
    """Calcula el déficit por especie comparando los pedidos PENDIENTES con el
    stock actual más la producción esperada. 'dias' = horizonte en días; si es
    0 se usa el plazo del último pedido pendiente de cada especie."""
    args = {"dias": dias}
    out = ""
    try:
        days = max(0, _entero(dias, "dias"))
        result = []
        for species in ESPECIES:
            pending = sql(
                "SELECT cantidad, fecha_limite FROM pedidos "
                "WHERE estado='pendiente' AND especie=?",
                (species,),
            )
            if not pending:
                continue
            row = sql(
                "SELECT stock, huevos_dia FROM especies WHERE nombre=?",
                (species,),
            )[0]
            demand = sum(item["cantidad"] for item in pending)
            horizon = days or max(
                _dias_hasta(item["fecha_limite"]) for item in pending
            )
            projected = row["stock"] + row["huevos_dia"] * horizon
            result.append(
                {
                    "especie": species,
                    "demanda_pendiente": demand,
                    "stock": row["stock"],
                    "horizonte_dias": horizon,
                    "disponible_proyectado": projected,
                    "deficit_hoy": max(0, demand - row["stock"]),
                    "deficit_proyectado": max(0, demand - projected),
                }
            )
        out = (
            _j(result)
            if result
            else "No hay pedidos pendientes: no hay demanda ni déficit."
        )
    except Exception as exc:
        out = f"Error al calcular déficit: {exc}"
    _record("calcular_deficit", args, out)
    return out


@tool
def priorizar_pedidos() -> str:
    """Ordena los pedidos pendientes por fecha límite (y luego por tamaño) e
    indica cuáles se pueden cumplir con el stock y la producción esperada,
    cuáles solo parcialmente y cuánto falta."""
    out = ""
    try:
        pending = sql(
            "SELECT * FROM pedidos WHERE estado='pendiente' "
            "ORDER BY fecha_limite, cantidad"
        )
        if not pending:
            out = "No hay pedidos pendientes."
        else:
            committed: dict[str, int] = {}
            plan = []
            for pedido in pending:
                row = sql(
                    "SELECT stock, huevos_dia FROM especies "
                    "WHERE nombre=?",
                    (pedido["especie"],),
                )[0]
                capacity = row["stock"] + row["huevos_dia"] * _dias_hasta(
                    pedido["fecha_limite"]
                )
                free = capacity - committed.get(pedido["especie"], 0)
                covered = max(0, min(pedido["cantidad"], free))
                committed[pedido["especie"]] = committed.get(
                    pedido["especie"], 0
                ) + covered
                state = (
                    "cumplible"
                    if covered == pedido["cantidad"]
                    else ("parcial" if covered > 0 else "no cumplible")
                )
                plan.append(
                    {
                        "prioridad": len(plan) + 1,
                        "pedido": pedido["id"],
                        "cliente": pedido["cliente"],
                        "especie": pedido["especie"],
                        "cantidad": pedido["cantidad"],
                        "fecha_limite": pedido["fecha_limite"],
                        "estado": state,
                        "faltante": pedido["cantidad"] - covered,
                    }
                )
            out = _j(plan)
    except Exception as exc:
        out = f"Error al priorizar pedidos: {exc}"
    _record("priorizar_pedidos", {}, out)
    return out


# ----------------------------------------------------------------------
# RAG
# ----------------------------------------------------------------------
@tool
def buscar_manual(consulta: str) -> str:
    """Busca en el manual de manejo de huevos (almacenamiento, equivalencias
    entre especies, tasas de postura, planificación, higiene, incubación).
    Úsala para recomendaciones o datos técnicos, no para cifras del inventario."""
    args = {"consulta": consulta}
    out = ""
    start = perf_counter()
    started_at = utc_now()
    rag = None
    try:
        invalid = _reject_injection(consulta, "consulta")
        if invalid:
            out = invalid
        else:
            rag = get_rag()
            hits = rag.buscar_detallado(str(consulta), k=2)
            if not hits:
                out = "El manual no contiene información sobre esa consulta."
            else:
                warning = ""
                if not rag.integrity.ok:
                    warning = (
                        "Aviso: el manual no superó la verificación de "
                        f"integridad ({rag.integrity.reason}); se excluyeron "
                        "los fragmentos alterados.\n"
                    )
                out = warning + "\n".join(
                    f"[{hit.score:.2f}] ({hit.fragment_id}) {hit.texto}"
                    for hit in hits
                )
    except Exception as exc:
        out = f"Error al consultar el manual: {exc}"
    finally:
        duration = round((perf_counter() - start) * 1000, 2)
        if rag is not None:
            info = current_run_info()
            record_span(
                get_turn_state(),
                name="retriever.buscar_manual",
                kind="retriever",
                started_at=started_at,
                ended_at=utc_now(),
                duration_ms=duration,
                parent_span_id=info.get("langsmith_run_id"),
                status="success" if not _status(out) == "error" else "error",
                attributes={
                    "mode": rag.modo,
                    "integrity_ok": rag.integrity.ok,
                    "query_chars": len(str(consulta)),
                },
                langsmith_run_id=info.get("langsmith_run_id"),
                allow_external_parent=True,
            )
    _record("buscar_manual", args, out)
    return out


TOOLS = [
    consultar_stock,
    consultar_pedidos,
    registrar_produccion,
    registrar_pedido,
    despachar_pedido,
    recordar_dato,
    evaluar_cumplimiento,
    calcular_deficit,
    priorizar_pedidos,
    buscar_manual,
]

for _tool in TOOLS:
    _tool.handle_validation_error = lambda error: (
        "Error: argumentos inválidos ("
        + "; ".join(
            f"{'.'.join(map(str, item['loc']))}: {item['msg']}"
            for item in error.errors()
        )
        + "). Corrígelos y reintenta. No se modificó nada."
    )

TOOL_NAMES = [item.name for item in TOOLS]
WRITE_TOOLS = {
    "registrar_produccion",
    "registrar_pedido",
    "despachar_pedido",
    "recordar_dato",
}
