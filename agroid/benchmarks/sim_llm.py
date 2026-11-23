"""LLM simulado determinista para pruebas sin red ni costo.

No evalúa calidad real: sigue un guion por palabras clave para ejercitar el
flujo completo, las herramientas, la memoria, la observabilidad y la seguridad.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult


class SimulatedLLM(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "agroid-simulado"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "SimulatedLLM":
        return self

    def _generate(
        self,
        messages: list[Any],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        system = ""
        for message in messages:
            if isinstance(message, SystemMessage):
                system = str(message.content)
                break
        if system.startswith("PLANIFICADOR"):
            return self._result(
                "1. consultar_stock\n2. calcular_deficit\n3. responder",
                messages,
            )

        last_human_index = max(
            (
                index
                for index, message in enumerate(messages)
                if isinstance(message, HumanMessage)
            ),
            default=0,
        )
        request = str(messages[last_human_index].content)
        request = request.split("\n\nPlan sugerido")[0].lower()
        steps = [
            message
            for message in messages[last_human_index + 1 :]
            if isinstance(message, ToolMessage)
        ]
        script = self._script(request, system, messages, last_human_index)

        if len(steps) < len(script):
            name, args = script[len(steps)]
            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": name,
                        "args": args,
                        "id": f"call_{len(steps)}_{name}",
                    }
                ],
            )
            return self._chat_result(message, messages)
        if "qué te pedí recordar" in request:
            start = system.find("Datos recordados")
            memory = system[start : start + 200] if start >= 0 else "(sin datos)"
            previous = [
                str(message.content)[:80]
                for message in messages[:last_human_index]
                if isinstance(message, HumanMessage)
            ]
            text = (
                f"[SIM] Datos en memoria: {memory} | "
                f"consultas previas visibles: {len(previous)}"
            )
        elif "ignora" in request or "system override" in request:
            text = (
                "[SIM] No puedo ignorar las reglas ni ejecutar acciones "
                "destructivas. Puedo ayudarte con inventario y pedidos."
            )
        elif not steps:
            text = (
                "[SIM] Necesito más detalle para responder: ¿qué especie, "
                "cantidad o período necesitas?"
            )
        else:
            text = "[SIM] " + " || ".join(
                str(message.content)[:120] for message in steps
            )
        return self._result(text, messages)

    @staticmethod
    def _chat_result(message: AIMessage, messages: list[Any]) -> ChatResult:
        prompt_tokens = max(
            1, sum(len(str(getattr(m, "content", m))) for m in messages) // 4
        )
        output_tokens = max(1, len(str(message.content)) // 4)
        message.usage_metadata = {
            "input_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": prompt_tokens + output_tokens,
        }
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _result(self, text: str, messages: list[Any]) -> ChatResult:
        return self._chat_result(AIMessage(content=text), messages)

    @staticmethod
    def _script(
        request: str,
        system: str,
        messages: list[Any],
        last_human_index: int,
    ) -> list[tuple[str, dict[str, Any]]]:
        if "ignora" in request or "system override" in request:
            return []
        if "entre codorniz y pato" in request or "1800" in request or "1.800" in request:
            return [
                (
                    "evaluar_cumplimiento",
                    {
                        "cantidad_requerida": 1800,
                        "especies": "codorniz,pato",
                        "dias": 5,
                    },
                )
            ]
        if "recolect" in request or "produje" in request:
            return [("registrar_produccion", {"especie": "gallina", "cantidad": 500})]
        if "déficit" in request and "retomando" not in request:
            return [("calcular_deficit", {"dias": 0})]
        if "falta para cumplir" in request or "revisa el déficit" in request:
            return [("calcular_deficit", {"dias": 0})]
        if "prioriza los pedidos" in request:
            return [
                ("priorizar_pedidos", {}),
                ("buscar_manual", {"consulta": "almacenar huevos de codorniz"}),
            ]
        if "recuerda que" in request:
            return [
                (
                    "recordar_dato",
                    {
                        "clave": "Hotel Costa",
                        "valor": "solo acepta huevos de pato",
                    },
                )
            ]
        if "dragón" in request:
            return [
                (
                    "registrar_produccion",
                    {"especie": "dragón", "cantidad": 50},
                ),
                (
                    "registrar_produccion",
                    {"especie": "pato", "cantidad": -20},
                ),
            ]
        if "registra" in request and "-20" in request:
            return [
                (
                    "registrar_produccion",
                    {"especie": "pato", "cantidad": -20},
                )
            ]
        if "urgente" in request or "clínica sur" in request:
            return [
                (
                    "registrar_pedido",
                    {
                        "cliente": "Clínica Sur",
                        "especie": "gallina",
                        "cantidad": 900,
                        "dias_plazo": 1,
                    },
                ),
                ("priorizar_pedidos", {}),
            ]
        if (
            "pedido" in request
            or " pide " in request
            or " solicita " in request
        ) and any(
            species in request
            for species in ("gallina", "codorniz", "pato", "ganso", "guinea")
        ):
            quantity = 300 if "300" in request else 200
            days = 2 if "pasado mañana" in request else 1
            species = next(
                (
                    item
                    for item in ("gallina", "codorniz", "pato", "ganso", "guinea")
                    if item in request
                ),
                "gallina",
            )
            return [
                (
                    "registrar_pedido",
                    {
                        "cliente": "cliente",
                        "especie": species,
                        "cantidad": quantity,
                        "dias_plazo": days,
                    },
                )
            ]
        if "cuánto queda" in request or "cuanto queda" in request:
            return [("consultar_stock", {"especie": "todas"})]
        if "pedidos" in request and "déficit" not in request:
            return [("consultar_pedidos", {"estado": "pendiente"})]
        if "almacen" in request or "manual" in request:
            return [("buscar_manual", {"consulta": "almacenamiento de huevos"})]
        if "retomando" in request or "qué te pedí recordar" in request:
            return []
        return []


def build_simulated_llm() -> SimulatedLLM:
    return SimulatedLLM()
