# Defensa EFT · Preguntas y respuestas

**Uso:** leer una vez, practicar en voz alta y llevar solo las ideas fuerza. No memorizar párrafos completos. Cada respuesta incluye una evidencia concreta.

## ¿Dónde está la evidencia?

| Pregunta | Archivo o captura | Dato |
|---|---|---|
| Resultados de los 8 casos | `docs/evidencias_eft/resultados_eft.json` / `.csv` | score 0,956; 7 éxito + 1 bloqueo |
| RAG | `rag_eval_20261127-125855.json` | recall@3 0,867; 24 fragmentos |
| Prompts | `prompt_eval_20261127-124003.json` | v1 0,90 → v2 1,00; regresión 0,996 |
| Planificación | `planning_eval_20261127-124005.json` | react/plan/auto 0,994 |
| Dashboard | `docs/defensa_eft/evidencias/dashboard_*.png` | resumen, calidad, RAG y traza |
| LangSmith | `langsmith_eft_trace_e03.png` y `langsmith_eft_list.png` | traza E03: 18,44 s; 9.154 tokens |
| Traza y spans | `chart_waterfall_e03.png` + `data/observability.db` | 4 LLM + 2 tools |
| Seguridad | `tests/test_security.py` | 7/7 pruebas |
| Notebook | `AgroID_Huevos_EFT.ipynb` | salidas reales/simuladas |

**Captura de LangSmith.** La traza de E03 se capturó del proyecto `agroid-huevos-ep3` el 27/11/2026. La lista muestra 4 trazas reales EFT y varias simuladas. Es evidencia real, no un mockup.

**Diferencia de latencias.** La suite `real-eft-20261127` registró E03 en 10,64 s; la corrida corta `real-eft-visual-20261127` registró 18,44 s. Son ejecuciones distintas del mismo caso: la variabilidad del modelo free es parte del hallazgo. No se debe mezclar una cifra con la otra.

**Diferencia de conteos.** El dashboard está filtrado a `real-eft-20261127` (8 trazas). LangSmith muestra 19 trazas del proyecto porque incluye la corrida real, la visual y las simuladas. El filtro por `run_id` o `session_id` explica la diferencia.


## Sobre el caso y el alcance

**1. ¿Por qué AgroID Huevos y no un caso genérico?**  
Porque permite integrar inventario, pedidos, producción, déficit, RAG y seguridad en un flujo verificable. El caso es verosímil y los datos son simulados; no se presenta como cliente real. La evidencia está en la sección 2 y en el notebook.

**2. ¿Cuál es el problema organizacional exacto?**  
La decisión de inventario con información dispersa: stock, producción, pedidos y conocimiento técnico. El agente no “adivina”: consulta la base, calcula y cita. El KPI principal es cumplimiento de pedidos y déficit proyectado.

**3. ¿Qué queda fuera del alcance?**  
ERP real, facturación, logística, pago, sensores, fine-tuning, app móvil y producción multi-tenant. Se declara en la sección 2.7 y en el anexo F.

## Sobre prompts y RAG

**4. ¿Por qué un catálogo de prompts y no un solo string?**  
Porque permite versionar, auditar y comparar. El system v2 agrega jerarquía de fuentes, citas, política de escritura, ambigüedad y seguridad. La rúbrica pasó de 0,90 a 1,00 y la regresión funcional se mantuvo en 0,996. Evidencia: `agroid/prompts.py`, `prompt_eval`.

**5. ¿Por qué RAG y no fine-tuning?**  
Porque el conocimiento cambia (manual, normativa, precios) y necesitamos citas y control de integridad. Fine-tuning no garantiza citas ni actualización. RAG es más barato y auditable para este caso.

**6. ¿Cómo combinan fuentes internas y externas?**  
El manual interno tiene 10 fragmentos; el corpus externo tiene 14 paráfrasis citadas de FAO, USDA, Codex, UGA, American Egg Board e INIA. La recuperación procura una fuente interna y una externa, deduplica y cita `[Mxx]`/`[Exx]`. Evidencia: `rag_eval` recall@3 0,867 y 9/10 casos con fuente externa.

**7. ¿Cómo evitan que un documento envenenado instruya al agente?**  
Cada corpus tiene manifiesto SHA-256/HMAC; si un fragmento cambia, se excluye. Además, `scan_untrusted` revisa instrucciones escondidas y el prompt trata el contenido como información, no como instrucción. Evidencia: `test_rag_hybrid.py`, `integrity.py`.

**8. ¿Qué pasa si no hay embeddings?**  
Se usa TF-IDF como respaldo léxico y se declara. No es búsqueda semántica; por eso la evaluación se hizo en TF-IDF para reproducibilidad. En producción se precomputarían embeddings.

## Sobre el agente, memoria y planificación

**9. ¿Por qué LangChain?**  
Porque `AgentExecutor` y los callbacks ya resuelven tool calling, spans y LangSmith. Smolagents era una alternativa, pero el equipo ya tenía la base LangChain y podía instrumentarla. La deuda es `langchain_classic`; se documenta.

**10. ¿Cómo funciona la memoria?**  
Tres niveles: ventana de 5 pares, resumen rodante cada 6 turnos y hechos persistentes por `session_id`. La prueba inserta 12 turnos, limpia RAM y recupera “Hotel Costa” desde SQLite. Evidencia: `memory.py`, `test_memory_long_flow.py`.

**11. ¿Cómo evitan que la replanificación duplique un pedido?**  
El monitor no reintenta si hubo una escritura exitosa. Solo replanifica ante error de lectura, respuesta vacía o fallo de herramienta, y máximo una vez. Evidencia: `planning.py`, prueba de inyección de fallo con `replan_count=1`.

**12. ¿Plan-and-Execute es mejor que ReAct?**  
No siempre. En la comparación simulada, ambos mantienen score 0,994; `plan` consume más tokens por la llamada de planificación. `auto` usa plan solo cuando la consulta es compuesta, ambigua o riesgosa. La decisión es un compromiso costo/estructura.

## Sobre observabilidad y resultados

**13. ¿Cómo miden groundedness?**  
Extraen las cifras de la respuesta y verifican si aparecen en las observaciones de herramientas o en el snapshot de la base. Es una métrica conservadora; no evalúa calidad redaccional. Evidencia: `evaluate.py`, `resultados_eft.json`.

**14. ¿Por qué la cobertura de citas es solo 0,667?**  
Porque el modelo cita una fuente aunque recupere tres. Es una brecha de prompt/grounding, no de recuperación. La acción es exigir cita por párrafo y un crítico que bloquee respuestas sin fuente. Es uno de los hallazgos principales.

**15. ¿Cómo sé que la evaluación es válida?**  
Porque se auditó el evaluador: se detectaron falsos negativos en N05/N06 y se corrigieron en `rescore.py`. Además, se contrastan cifras contra SQLite y LangSmith. La muestra es pequeña; se declara.

**16. ¿Por qué el router cambia de modelo?**  
Porque `openrouter/free` enruta aleatoriamente entre modelos gratuitos. En la EP3 cambió en 7 de 8 trazas; al fijar `nemotron`, la consistencia subió a Jaccard 1,0. Evidencia: tabla EP3 y capturas de LangSmith. En EFT se usó modelo fijado para reducir esa variable.

**17. ¿Qué significa el P95 de 15,7 s del dashboard EFT?**  
Es el percentil 95 de las 8 trazas reales de `real-eft-20261127`, con modelo free y un caso bloqueado. La media fue 8,1 s y el máximo 17,1 s. No es un SLO de producción; es una fotografía de la corrida. La EP3 tenía un P95 histórico de 21,7 s sobre 126 trazas.

## Sobre seguridad y ética

**18. ¿Cómo protegen PII?**  
RUT, email, teléfono y tarjetas se redactan antes del LLM, LangSmith, logs e historial. Evidencia: `test_security.py`, `pii.py`; en el notebook se ve `[EMAIL_1]`, `[RUT_1]`, `[TELEFONO_1]`.

**19. ¿Cómo bloquean prompt injection?**  
Patrones ponderados, delimitadores, política de herramientas y bloqueo de salida con fuga del prompt. La suite aprobó 7/7; E06 se bloqueó sin tokens ni herramientas. Limitación: heurística, no cubre paráfrasis nuevas.

**20. ¿Cuál es el riesgo ético más importante?**  
La automatización de una decisión de inventario sin humano. El agente puede priorizar mal o alucinar una recomendación. Por eso se propone human-in-the-loop para escrituras de alto valor, trazabilidad y validación profesional.

## Sobre mejoras y escalabilidad

**21. ¿Qué harían con más tiempo?**  
Citas obligatorias, aclaración de ambigüedad, modelo fuerte de validación, PostgreSQL/Redis, autenticación, caché semántica y pruebas con usuarios reales. El roadmap está en la sección 7.3.

**22. ¿Cómo escalarían a 1.000 usuarios?**  
Separar API, workers, RAG y observabilidad; PostgreSQL para estado; Redis para rate limit/caché; cola para tareas largas; gateway con autenticación y cuotas. SQLite no alcanza para múltiples réplicas.

**23. ¿Cómo reducen costo?**  
Modelo fijado o routing por complejidad, caché semántica, compresión de prompts y embeddings precomputados. El router consumió 5.928 tokens/turno vs 3.454 del fijado; esa diferencia justifica routing.

**24. ¿Qué no está resuelto?**  
La confirmación humana, la retención/borrado de datos, el fallback automático de proveedor, la evaluación con modelo de gama alta y la validación legal/sanitaria. Se declara en el anexo F.

## Preguntas trampa

**25. “¿Entonces el agente es production-ready?”**  
No. Es un prototipo observable y corregible. Falta autenticación, PostgreSQL/Redis, human-in-the-loop, retención, SLA y validación con usuarios. Decirlo con claridad suma credibilidad.

**26. “Si el modelo free falla, ¿el sistema se cae?”**  
El turno devuelve un error clasificado y no oculta el incidente; el dashboard lo muestra. No hay fallback automático todavía; es una mejora del roadmap.

**27. “¿Por qué no usaron un modelo más potente?”**  
Se dejó preparada la suite `validation` con `LLM_MODEL_STRONG`, pero el equipo optó por no incurrir en costo. La comparación router vs fijado ya muestra el efecto de estabilizar el modelo; la validación con gama alta es trabajo inmediato.

**28. “¿No es peligroso que el agente escriba en la base?”**  
Sí, por eso hay límite de 3 escrituras, validación, ambigüedad y confirmación humana propuesta. En la demo, las escrituras son simuladas y la traza queda registrada.

**29. “¿La captura de LangSmith es de esta entrega o de la EP3?”**  
La traza E03 y la lista son de la corrida EFT del 27/11/2026 (`visual-E03`). La captura de overview de la EP3 se usó como referencia histórica de la instrumentación, pero el deck final usa la traza EFT real.

**30. “¿Por qué no hacen la demo en vivo?”**  
Porque los 8 casos reales consumen cuota y tiempo. La demo pregrabada muestra RAG, plan/tools y memoria/replan con salidas reales. Si piden live, abrimos la ventana de chat (`Abrir_AgroID.bat`) y hacemos 1–2 consultas: déficit y RAG. Si falla la API, cambiamos a **Simulado** en la misma ventana.

**31. “¿Por qué no entregan PDF de las diapositivas?”**  
Porque el formato solicitado y editable es PPTX. El deck incluye notas del orador, guion y tiempos; el PDF anterior se retiró para no dejar una versión desactualizada. Las capturas y gráficos quedan en `docs/defensa_eft/evidencias/`.
