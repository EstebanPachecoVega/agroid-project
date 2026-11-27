"""Planificación, adaptación y crítica para el agente AgroID.

El modo ``auto`` clasifica la consulta y elige ReAct o Plan-and-Execute. El
plan se genera con un esquema JSON y se monitorea después de la ejecución. Si
hay un error de lectura o faltan pasos, se permite **una** replanificación; las
escrituras exitosas nunca se reintentan automáticamente para evitar duplicar
pedidos, producciones o despachos.

La crítica es determinista: verifica cifras y citas contra las observaciones.
No reemplaza la revisión humana, pero deja evidencia objetiva en la traza.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from .prompts import PLANNER_EFT, render

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


@dataclass
class QueryProfile:
    intent: str
    complexity: str
    risk: str
    suggested_mode: str
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "complexity": self.complexity,
            "risk": self.risk,
            "suggested_mode": self.suggested_mode,
            "reasons": list(self.reasons),
        }


def classify_query(texto: str, has_history: bool = False) -> QueryProfile:
    """Clasificación determinista y explicable para enrutar el modo."""
    text = " ".join(str(texto or "").lower().split())
    reasons: list[str] = []
    ambiguous_markers = (
        "cuánto queda",
        "cuanto queda",
        "manda lo de ayer",
        "lo de ayer",
        "huevos pequeños",
        "huevos pequenos",
        "eso",
        "lo mismo",
        "lo anterior",
        "qué te pedí",
        "que te pedi",
    )
    write_markers = (
        "registra",
        "registrar",
        "recolect",
        "produje",
        "despacha",
        "despachar",
        "crea un pedido",
        "ingresa un pedido",
        "actualiza",
        "modifica",
        "elimina",
        "borra",
        "cambia",
    )
    complex_markers = (
        " y ",
        "luego",
        "después",
        "despues",
        "primero",
        "finalmente",
        "prioriza",
        "reprioriza",
        "déficit",
        "deficit",
        "compara",
        "evalúa",
        "evalua",
        "planifica",
        "revisa",
        "almacena",
        "recomienda",
        "urgente",
        "varios",
        "pasos",
    )
    if any(marker in text for marker in ambiguous_markers):
        reasons.append("referencia ambigua o incompleta")
        return QueryProfile(
            intent="ambiguo",
            complexity="simple",
            risk="bajo",
            suggested_mode="plan",
            reasons=reasons,
        )
    if not has_history and text in {"hola", "buenas", "ayuda"}:
        return QueryProfile(
            intent="saludo",
            complexity="simple",
            risk="bajo",
            suggested_mode="react",
            reasons=["saludo"],
        )
    writes = any(marker in text for marker in write_markers)
    if writes:
        reasons.append("incluye una escritura")
    complex_hits = [marker for marker in complex_markers if marker in text]
    if len(complex_hits) >= 2 or any(
        marker in text for marker in ("prioriza", "reprioriza", "urgente")
    ):
        reasons.append("múltiples intenciones o pasos")
    if len(text) > 180:
        reasons.append("consulta extensa")
    if writes and any(
        marker in text for marker in ("elimina", "borra", "masivo", "todo el stock")
    ):
        reasons.append("operación destructiva o masiva")
        return QueryProfile(
            intent="riesgoso",
            complexity="compuesta",
            risk="alto",
            suggested_mode="plan",
            reasons=reasons,
        )
    if complex_hits or len(reasons) >= 1 and writes:
        return QueryProfile(
            intent="escritura" if writes else "compuesta",
            complexity="compuesta",
            risk="medio" if writes else "bajo",
            suggested_mode="plan",
            reasons=reasons,
        )
    return QueryProfile(
        intent="consulta",
        complexity="simple",
        risk="bajo",
        suggested_mode="react",
        reasons=reasons or ["consulta directa"],
    )


@dataclass
class PlanStep:
    id: int
    accion: str
    herramienta: str = ""
    argumentos: dict[str, Any] = field(default_factory=dict)
    criterio_exito: str = ""
    fallback: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "accion": self.accion,
            "herramienta": self.herramienta,
            "argumentos": self.argumentos,
            "criterio_exito": self.criterio_exito,
            "fallback": self.fallback,
        }


@dataclass
class Plan:
    objetivo: str
    complejidad: str = "compuesta"
    pasos: list[PlanStep] = field(default_factory=list)
    requiere_confirmacion: bool = False
    source: str = "llm"

    def tools(self) -> list[str]:
        return [
            step.herramienta
            for step in self.pasos
            if step.herramienta and step.herramienta not in {"responder", "ninguna"}
        ]

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "objetivo": self.objetivo,
            "complejidad": self.complejidad,
            "pasos": [step.as_dict() for step in self.pasos],
            "requiere_confirmacion": self.requiere_confirmacion,
            "source": self.source,
        }

    def to_prompt(self) -> str:
        lines = [f"Objetivo: {self.objetivo}", "Pasos:"]
        for step in self.pasos:
            tool = f" [{step.herramienta}]" if step.herramienta else ""
            criterion = (
                f" — éxito: {step.criterio_exito}"
                if step.criterio_exito
                else ""
            )
            fallback = (
                f" — si falla: {step.fallback}" if step.fallback else ""
            )
            lines.append(
                f"{step.id}. {step.accion}{tool}{criterion}{fallback}"
            )
        if self.requiere_confirmacion:
            lines.append("Requiere confirmación humana antes de escribir.")
        return "\n".join(lines)


def _coerce_step(raw: dict[str, Any], index: int) -> PlanStep:
    args = raw.get("argumentos", raw.get("args", {}))
    if not isinstance(args, dict):
        args = {}
    return PlanStep(
        id=int(raw.get("id", index) or index),
        accion=str(raw.get("accion", raw.get("action", "paso"))),
        herramienta=str(
            raw.get("herramienta", raw.get("tool", "")) or ""
        ),
        argumentos=args,
        criterio_exito=str(
            raw.get("criterio_exito", raw.get("success", "")) or ""
        ),
        fallback=str(raw.get("fallback", "") or ""),
    )


def parse_plan(text: str, source: str = "llm") -> Plan:
    """Parsea JSON o, como respaldo, un plan numerado."""
    raw = str(text or "").strip()
    candidates = [raw]
    match = _JSON_BLOCK.search(raw)
    if match:
        candidates.insert(0, match.group(0))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        steps = data.get("pasos") or data.get("steps") or []
        if not isinstance(steps, list):
            continue
        return Plan(
            objetivo=str(data.get("objetivo", data.get("objective", "")) or ""),
            complejidad=str(data.get("complejidad", "compuesta")),
            pasos=[
                _coerce_step(item, index)
                for index, item in enumerate(steps, start=1)
                if isinstance(item, dict)
            ],
            requiere_confirmacion=bool(data.get("requiere_confirmacion", False)),
            source=source,
        )
    # Respaldo: líneas "1. herramienta: argumentos" o "1. texto".
    steps: list[PlanStep] = []
    for line in raw.splitlines():
        line = line.strip()
        if not re.match(r"^\d+[\.\)]\s*", line):
            continue
        content = re.sub(r"^\d+[\.\)]\s*", "", line)
        tool = ""
        for name in (
            "consultar_stock",
            "consultar_pedidos",
            "registrar_produccion",
            "registrar_pedido",
            "despachar_pedido",
            "recordar_dato",
            "evaluar_cumplimiento",
            "calcular_deficit",
            "priorizar_pedidos",
            "buscar_manual",
        ):
            if name in content:
                tool = name
                break
        steps.append(
            PlanStep(
                id=len(steps) + 1,
                accion=content,
                herramienta=tool,
            )
        )
    return Plan(
        objetivo="",
        complejidad="compuesta",
        pasos=steps,
        source="fallback",
    )


def plan_prompt(texto: str, tools: Iterable[str]) -> str:
    return render("planner_v2", tools=", ".join(tools)) + "\n\nSolicitud:\n" + texto


def _call_payload(call: Any) -> dict[str, Any]:
    if isinstance(call, dict):
        return call
    return {
        "tool": getattr(call, "tool_name", ""),
        "status": getattr(call, "status", ""),
        "result": getattr(call, "result_summary", ""),
        "args": getattr(call, "args", {}),
    }


def monitor_plan(
    plan: Plan | None,
    tool_calls: Iterable[dict[str, Any]],
    response: str,
    status: str,
    iterations: int,
    max_iterations: int,
) -> dict[str, Any]:
    """Decisión determinista de continuación/replanificación/cierre."""
    calls = [_call_payload(call) for call in (tool_calls or [])]
    errors = [call for call in calls if call.get("status") == "error"]
    writes = [
        call
        for call in calls
        if call.get("tool")
        in {
            "registrar_produccion",
            "registrar_pedido",
            "despachar_pedido",
            "recordar_dato",
        }
        and call.get("status") == "success"
    ]
    if writes:
        return {
            "decision": "cerrar",
            "motivo": "hubo una escritura exitosa; no se reintenta para evitar duplicados",
            "pasos_faltantes": [],
            "riesgo": "medio",
        }
    if status in {"error", "max_iterations"} or errors:
        return {
            "decision": "replanificar",
            "motivo": (
                "error de ejecución o herramienta; se requiere un plan corregido"
            ),
            "pasos_faltantes": [],
            "riesgo": "alto" if status != "success" else "medio",
        }
    if not (response or "").strip():
        return {
            "decision": "replanificar",
            "motivo": "respuesta vacía",
            "pasos_faltantes": [],
            "riesgo": "medio",
        }
    # Una respuesta no vacía sin herramientas puede ser una aclaración, una
    # consulta de memoria o un rechazo seguro; no se fuerza una replanificación
    # solo porque el plan sugerido nombraba herramientas.
    if not calls:
        return {
            "decision": "cerrar",
            "motivo": "respuesta entregada sin herramientas; no se reintenta",
            "pasos_faltantes": [],
            "riesgo": "bajo",
        }
    if plan and plan.pasos:
        expected = set(plan.tools())
        actual = {call.get("tool") for call in calls if call.get("tool")}
        missing = sorted(expected - actual)
        if missing and iterations >= max_iterations:
            return {
                "decision": "replanificar",
                "motivo": "faltan herramientas del plan y se agotaron las iteraciones",
                "pasos_faltantes": missing,
                "riesgo": "alto",
            }
        if missing and not calls:
            return {
                "decision": "replanificar",
                "motivo": "el plan esperaba herramientas y no se ejecutó ninguna",
                "pasos_faltantes": missing,
                "riesgo": "medio",
            }
        return {
            "decision": "cerrar",
            "motivo": "el plan se cubrió o la respuesta ya resuelve la consulta",
            "pasos_faltantes": missing,
            "riesgo": "bajo",
        }
    return {
        "decision": "cerrar",
        "motivo": "no hay plan activo",
        "pasos_faltantes": [],
        "riesgo": "bajo",
    }


def _numbers(text: Any) -> list[float]:
    values = []
    for token in _NUMBER.findall(str(text or "")):
        try:
            values.append(float(token.replace(".", "").replace(",", ".")))
        except ValueError:
            continue
    return values


def critic_check(
    response: str,
    tool_calls: Iterable[dict[str, Any]],
    plan: Plan | None = None,
) -> dict[str, Any]:
    """Crítica determinista de cifras y citas."""
    calls = [_call_payload(call) for call in (tool_calls or [])]
    source_text = " ".join(
        str(call.get("result", "")) for call in calls
    )
    source_numbers = _numbers(source_text)
    response_numbers = _numbers(response)
    unsupported = [
        number
        for number in response_numbers
        if source_numbers
        and not any(abs(number - candidate) < 0.01 for candidate in source_numbers)
    ]
    citation_needed = any(
        word in str(response).lower()
        for word in (
            "recomiendo",
            "se recomienda",
            "conviene",
            "almacen",
            "refriger",
            "temperatura",
            "humedad",
            "incub",
            "bioseguridad",
        )
    )
    has_citation = bool(re.search(r"\[(M|E)\d{2}\]", str(response or "")))
    citations_missing = citation_needed and not has_citation
    problems = []
    if unsupported:
        problems.append("hay cifras sin respaldo en las observaciones")
    if citations_missing:
        problems.append("faltan citas [Mxx]/[Exx] en una recomendación técnica")
    return {
        "ok": not problems,
        "problemas": problems,
        "cifras_sin_respaldo": unsupported,
        "citas_faltantes": citations_missing,
        "sugerencia": (
            "revisar cifras y citar la fuente recuperada"
            if problems
            else "sin observaciones"
        ),
        "plan_source": plan.source if plan else "",
    }
