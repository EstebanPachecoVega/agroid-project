"""Pruebas de planificación, monitoreo y crítica determinista."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agroid.planning import (
    Plan,
    PlanStep,
    classify_query,
    critic_check,
    monitor_plan,
    parse_plan,
)


def test_classifier_routes_ambiguity_to_plan():
    profile = classify_query("¿Cuánto queda?")
    assert profile.intent == "ambiguo"
    assert profile.suggested_mode == "plan"


def test_classifier_routes_compound_query_to_plan():
    profile = classify_query(
        "Revisa el déficit y luego prioriza los pedidos pendientes."
    )
    assert profile.complexity == "compuesta"
    assert profile.suggested_mode == "plan"


def test_classifier_routes_simple_read_to_react():
    profile = classify_query("¿Cuánto stock hay de gallina?")
    assert profile.suggested_mode == "react"


def test_parse_json_plan():
    raw = """
    {"objetivo":"revisar stock","complejidad":"compuesta","pasos":[
      {"id":1,"accion":"consultar","herramienta":"consultar_stock","argumentos":{"especie":"gallina"},"criterio_exito":"stock visible","fallback":"pedir especie"}
    ],"requiere_confirmacion":false}
    """
    plan = parse_plan(raw)
    assert plan.objetivo == "revisar stock"
    assert len(plan.pasos) == 1
    assert plan.pasos[0].herramienta == "consultar_stock"
    assert plan.pasos[0].argumentos["especie"] == "gallina"


def test_parse_numbered_fallback():
    plan = parse_plan("1. calcular_deficit\n2. priorizar_pedidos\n3. responder")
    assert len(plan.pasos) == 3
    assert plan.pasos[0].herramienta == "calcular_deficit"
    assert plan.pasos[1].herramienta == "priorizar_pedidos"


def test_monitor_does_not_retry_successful_writes():
    plan = Plan(
        objetivo="registrar pedido",
        pasos=[PlanStep(1, "registrar", "registrar_pedido")],
    )
    decision = monitor_plan(
        plan,
        [{"tool": "registrar_pedido", "status": "success"}],
        "Pedido registrado.",
        "success",
        1,
        8,
    )
    assert decision["decision"] == "cerrar"
    assert "duplicados" in decision["motivo"]


def test_monitor_replans_on_tool_error():
    plan = Plan(
        objetivo="consultar",
        pasos=[PlanStep(1, "consultar", "consultar_stock")],
    )
    decision = monitor_plan(
        plan,
        [{"tool": "consultar_stock", "status": "error"}],
        "",
        "success",
        1,
        8,
    )
    assert decision["decision"] == "replanificar"


def test_critic_detects_unsupported_numbers_and_missing_citation():
    critic = critic_check(
        "El stock es 99 y recomiendo refrigerar a 2 °C.",
        [{"tool": "consultar_stock", "result": "stock 800", "status": "success"}],
    )
    assert critic["ok"] is False
    assert 99.0 in critic["cifras_sin_respaldo"]
    assert critic["citas_faltantes"] is True


def test_adaptive_replan_after_tool_error():
    import os
    import tempfile
    from pathlib import Path

    from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

    from agroid.agent import reset_memories, run_turn
    from agroid.benchmarks.sim_llm import SimulatedLLM
    from agroid.config import reload_settings
    from agroid.db import inicializar_bd, set_db_path
    from agroid.observability import store

    tmp = Path(tempfile.mkdtemp(prefix="agroid-replan-"))
    os.environ["AGROID_DATA_DIR"] = str(
        Path(__file__).resolve().parents[1] / "data"
    )
    os.environ["AGROID_LOGS_DIR"] = str(tmp / "logs")
    reload_settings()
    set_db_path(tmp / "agroid.db")
    store.set_obs_db_path(tmp / "observability.db")
    store.reset_store()
    inicializar_bd(reset=True)
    reset_memories()

    class FallibleLLM(SimulatedLLM):
        failed: bool = False

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            system = ""
            for message in messages:
                if isinstance(message, SystemMessage):
                    system = str(message.content)
                    break
            if system.startswith("PLANIFICADOR"):
                return super()._generate(messages, stop, run_manager, **kwargs)
            tool_messages = [
                message for message in messages if isinstance(message, ToolMessage)
            ]
            if not self.failed and not tool_messages:
                self.failed = True
                message = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "consultar_stock",
                            "args": {"especie": "dragón"},
                            "id": "bad-call",
                        }
                    ],
                )
                return self._chat_result(message, messages)
            return super()._generate(messages, stop, run_manager, **kwargs)

    result = run_turn(
        "¿Cuánto stock hay de gallina?",
        session_id="replan-test",
        modo="plan",
        category="planificacion",
        experiment_group="test",
        model="simulado",
        llm=FallibleLLM(),
    )
    assert result.status == "success", result.as_dict()
    assert result.replan_count >= 1
    assert "consultar_stock" in result.tool_names


def main():
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"{len(tests)} pruebas nuevas aprobadas.")


if __name__ == "__main__":
    main()
