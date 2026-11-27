# Defensa EFT · Demo pregrabada

**Objetivo:** mostrar el flujo completo en 40 segundos, sin Colab en vivo y sin depender de internet.  
**Formato:** tres paneles con salidas reales del notebook y de la corrida EFT.  
**Plan B:** si el docente pide live, ejecutar solo E01 en modo simulado durante 20 segundos.

## Antes de presentar

- [ ] PPTX abierto en la lámina 11.
- [ ] Dashboard abierto en `http://localhost:8501/?run=real-eft-20261127&solo_reales=1`.
- [ ] LangSmith abierto en la traza `visual-E03` (opcional, para preguntas).
- [ ] `docs/evidencias_eft/resultados_eft.json` a mano.
- [ ] Plan B probado: `python -m agroid.benchmarks.run --mode sim --suite eft --limit 1`.

## Guion de 40 segundos

### 0:00–0:12 · RAG

**Frase.** “La primera evidencia es RAG. La consulta pide la temperatura del USDA y el agente responde con cita externa [E05], no de memoria.”

**Mostrar.** Panel 1: consulta, recuperación `[E05] [E06] [M01]`, respuesta y verificación `recall@3 0,867`.

### 0:12–0:26 · Plan y herramientas

**Frase.** “La segunda es planificación. E03 ejecuta `calcular_deficit` y `priorizar_pedidos`, deja `trace_id` y consume 9.154 tokens. El plan se ve en la traza.”

**Mostrar.** Panel 2: plan de tres pasos, traza y resultado.

### 0:26–0:40 · Memoria y replanificación

**Frase.** “La tercera es memoria. Hotel Costa sobrevive a `reset_memories()` y la prueba de fallo deja `replan_count=1`, sin reintentar la escritura. La seguridad bloquea E06 sin tokens.”

**Mostrar.** Panel 3: antes/después, prueba de fallo y bloqueo.

## Plan B · 20 segundos si piden live

1. Abrir terminal en la raíz del repo.
2. Ejecutar:

```bash
python -m agroid.benchmarks.run --mode sim --suite eft --limit 1
```

3. Mostrar en el notebook o en la salida:
   - `trace_id`
   - `status=success`
   - herramienta usada
   - `tokens`
4. Cerrar con: “El modo simulado demuestra el flujo; la evidencia real está en el deck y en `resultados_eft.json`.”

No ejecutar los 8 casos en vivo: consume cuota y supera el tiempo de la defensa.

## Si falla algo

| Falla | Plan B |
|---|---|
| No hay internet | Usar el deck y el notebook ya ejecutado; no se requiere red. |
| Streamlit no abre | Mostrar las capturas de `docs/defensa_eft/evidencias/`. |
| LangSmith no carga | Usar `langsmith_eft_trace_e03.png` y el waterfall del deck. |
| El modelo free da 429 | Declararlo: ya está documentado; usar modo simulado. |
| Se acaba el tiempo | Saltar el panel 3; priorizar RAG, plan y bloqueo de seguridad. |

## Frase de cierre

“La demo muestra el flujo; la evidencia muestra que el flujo es medible. Lo que sigue es la interpretación de los resultados y las mejoras.”
