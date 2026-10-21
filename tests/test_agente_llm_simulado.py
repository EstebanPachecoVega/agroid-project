"""Prueba del flujo completo del cuaderno con un LLM SIMULADO (no usa API keys ni créditos, no hace llamadas de red).
Valida: herramientas, memoria corta/larga, planificador, manejo de errores y persistencia. NO evalúa la calidad de razonamiento
de un LLM real: el modelo simulado sigue reglas fijas. Uso:  python tests/test_agente_llm_simulado.py AgroID_Huevos_Agente_EP2.ipynb
"""
import sys, os, re, json, tempfile, uuid
import nbformat
import openai, langchain_openai
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class LLMSimulado(BaseChatModel):
    """Imita a un LLM con tool calling mediante reglas por palabra clave."""
    @property
    def _llm_type(self): return "simulado"

    def _generate(self, messages, stop=None, run_manager=None, **kw):
        sistema = messages[0].content if isinstance(messages[0], SystemMessage) else ""
        if sistema.startswith("PLANIFICADOR"):
            return self._r("1. calcular_deficit\n2. priorizar_pedidos\n3. responder")
        ult = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
        pedido = messages[ult].content.split("\n\nPlan sugerido")[0].lower()
        pasos = [m for m in messages[ult + 1:] if isinstance(m, ToolMessage)]
        guion = self._guion(pedido)
        if len(pasos) < len(guion):
            nombre, args = guion[len(pasos)]
            msg = AIMessage(content="", tool_calls=[{"name": nombre, "args": args, "id": f"c{len(pasos)}"}])
            return ChatResult(generations=[ChatGeneration(message=msg)])
        if "qué te pedí recordar" in pedido:
            previos = [m.content for m in messages[:ult] if isinstance(m, HumanMessage)]
            return self._r(f"[SIM] Datos en memoria: {sistema[sistema.find('Datos recordados'):]} | consultas previas visibles: {len(previos)}")
        return self._r("[SIM] " + " || ".join(str(m.content)[:120] for m in pasos) if pasos else "[SIM] sin herramientas")

    @staticmethod
    def _r(t): return ChatResult(generations=[ChatGeneration(message=AIMessage(content=t))])

    @staticmethod
    def _guion(p):
        if "entre codorniz y pato" in p: return [("evaluar_cumplimiento", {"cantidad_requerida": 1800, "especies": "codorniz,pato", "dias": 5})]
        if "recolectar" in p: return [("registrar_produccion", {"especie": "gallina", "cantidad": 500})]
        if "déficit" in p and "retomando" not in p: return [("calcular_deficit", {"dias": 0})]
        if "prioriza los pedidos" in p: return [("priorizar_pedidos", {}), ("buscar_manual", {"consulta": "almacenar huevos de codorniz"})]
        if "recuerda que" in p: return [("recordar_dato", {"clave": "Hotel Costa", "valor": "solo acepta huevos de pato"})]
        if "dragón" in p: return [("registrar_produccion", {"especie": "dragón", "cantidad": 50}), ("registrar_produccion", {"especie": "pato", "cantidad": -20})]
        if "urgente" in p: return [("registrar_pedido", {"cliente": "Clínica Sur", "especie": "gallina", "cantidad": 900, "dias_plazo": 1}), ("priorizar_pedidos", {})]
        return []

    def bind_tools(self, tools, **kw): return self


def main(ruta_nb):
    os.environ.update({"LLM_API_KEY": "clave-falsa-de-prueba", "LLM_BASE_URL": "http://127.0.0.1:9/v1"})
    langchain_openai.ChatOpenAI = lambda **kw: LLMSimulado()
    class _SinRed:                      # fuerza el respaldo TF-IDF sin tocar la red
        def __init__(self, **kw): raise ConnectionError("sin red (prueba)")
    openai.OpenAI = _SinRed
    nb = nbformat.read(ruta_nb, as_version=4)
    ns, tmp = {"__name__": "__main__"}, tempfile.mkdtemp()
    for c in nb.cells:
        if c.cell_type != "code" or "input(" in c.source: continue
        fuente = "\n".join((l[:len(l) - len(l.lstrip())] + "pass") if l.lstrip().startswith(("!", "%")) else l
                           for l in c.source.splitlines())
        fuente = fuente.replace('CARPETA = "./datos_agroid"', f'CARPETA = r"{tmp}"')
        exec(compile(fuente, "celda", "exec"), ns)
    sql, chat, MEMORIAS = ns["sql"], ns["chat"], ns["MEMORIAS"]
    # --- verificaciones sobre el estado final de la demo ---
    stock = {r["nombre"]: r["stock"] for r in sql("SELECT nombre, stock FROM especies")}
    assert stock["gallina"] == 800 + 500, stock                      # escritura del escenario 2
    assert stock["pato"] == 200, "los errores del escenario 6 no deben alterar el stock"
    assert sql("SELECT valor FROM datos WHERE clave='Hotel Costa'")[0]["valor"].startswith("solo acepta")
    assert sql("SELECT 1 FROM pedidos WHERE cliente='Clínica Sur'")
    assert len(sql("SELECT 1 FROM historial WHERE session_id='usuario1'")) == 16   # 8 turnos x 2 mensajes
    MEMORIAS.clear()                                                # reinicio de runtime
    r = chat("Retomando: ¿qué te pedí recordar sobre Hotel Costa y qué hablamos sobre el déficit?", "usuario1", verbose=False)
    assert "solo acepta huevos de pato" in r and "previas visibles: 5" in r, r   # datos largos + ventana k=5 reconstruida
    r2 = chat("Retomando: ¿qué te pedí recordar sobre Hotel Costa?", "otra_sesion", verbose=False)
    assert "(ninguno)" in r2, r2                                    # aislamiento entre sesiones
    # --- fallo del LLM: el agente no debe caerse ---
    class _Roto:
        def invoke(self, *a, **k): raise RuntimeError("429 rate limit")
    ns["ejecutor"] = _Roto()
    assert chat("hola", "usuario1", verbose=False).startswith("⚠️")
    print("\n✅ PRUEBAS CON LLM SIMULADO: TODAS PASARON | modo recuperación:", ns["RAG"].modo)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "AgroID_Huevos_Agente_EP2.ipynb")
