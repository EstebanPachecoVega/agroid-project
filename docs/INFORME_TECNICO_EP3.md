# AgroID Huevos: observabilidad, evaluación y seguridad de un agente de inventario

**ISY0101 Ingeniería de Soluciones con IA — Evaluación Parcial N°3**  
**Integrantes:** Esteban Pacheco Vega y Javier Perez Mora  
**Sección:** 007D  
**Repositorio:** `agroid-project` · **Proyecto LangSmith:** `agroid-huevos-ep3`

## 1. Arquitectura e instrumentación

AgroID Huevos es un agente conversacional en español para consultar y actualizar inventario avícola simulado. La EP3 conserva las diez herramientas de la EP2 (consulta, escritura, razonamiento y recuperación) y añade una capa de observabilidad, seguridad y evaluación. El código se separó en el paquete `agroid/`; el notebook EP2 queda como línea base histórica.

La instrumentación combina tres fuentes:

| Fuente | Función |
|---|---|
| LangSmith | Árbol nativo de trazas: `trace_id`, `run_id`, `parent_run_id`, spans de LLM, Tool y Retriever |
| JSONL | Logs estructurados por evento, con IDs de correlación, latencia, tokens, costo y decisiones de seguridad |
| SQLite | Agregados para el dashboard, evaluaciones, eventos de seguridad y caché de LangSmith |

Cada turno recibe un `session_id`, un `trace_id` interno de 32 hex y un `span_id` de 16 hex. LangSmith asigna el `trace_id`/`run_id` nativo y el proyecto añade el `trace_id` interno en metadata para unir logs y base local. La jerarquía es: `chat` → `agroid.planificar` (modo plan) → llamadas `LLM` → `Tool` → `Retriever` en `buscar_manual`. El callback de LangChain captura tokens de entrada/salida, modelo real, latencia, costo y errores; la recuperación registra un span propio porque no es un `Retriever` nativo de LangChain.

La privacidad se aplica antes de la telemetría: RUT, emails, teléfonos y tarjetas se reemplazan por marcadores antes de enviar contenido al LLM, a LangSmith, a los logs y al historial. El manual RAG se carga desde `data/manual.json` y se verifica con SHA-256 y HMAC opcional en cada búsqueda; los fragmentos alterados se excluyen y se registran como incidente. La traza real del caso N01 quedó registrada en el proyecto `agroid-huevos-ep3` (por ejemplo, `01a1f150-dc76-76f6-bc7f-24cd8afe5e29`); la captura del árbol de spans se conserva en `docs/evidencias/`.

## 2. Métricas y escenarios de prueba

| Dimensión | Métrica | Definición operativa |
|---|---|---|
| Calidad | `tool_match` | Coincidencia entre herramientas requeridas y ejecutadas |
| Calidad | `args_match` | Coincidencia de argumentos críticos (especie, cantidad, plazo) |
| Calidad | `facts_match` | Cifras y estado de la base esperados |
| Calidad | `groundedness` | Proporción de cifras de la respuesta respaldadas por herramientas o base |
| Consistencia | Jaccard de herramientas | Similitud de secuencias ante reformulaciones |
| Estabilidad | Tasa de error | Turnos con excepción, error de herramienta o saturación |
| Rendimiento | Latencia E2E P50/P95 | Duración del turno y de cada span |
| Rendimiento | TTFT | Tiempo hasta el primer token con streaming real |
| Recursos | Tokens y costo | Tokens de entrada/salida; costo real y equivalente |
| Robustez | Bucles y deriva | Acciones idénticas repetidas, `max_iterations`, crecimiento anómalo del prompt |

La matriz experimental usa 29 turnos reales: 8 con `openrouter/free`, 6 con un modelo gratuito fijado, 1 comparación N01, 6 reformulaciones (2 intenciones × 3 formas), 4 pares de nombres para sesgo y 4 de validación posterior. Los casos cubren consultas normales, ambiguas, complejas, adversariales y de borde. La carga se prueba con LLM simulado para no consumir cuota: 40 solicitudes con 5 workers y sesiones distintas. La matriz completa se ejecutó entre el 19 y el 23 de noviembre de 2026.

`openrouter/free` es un enrutador que selecciona modelos gratuitos al azar; por eso se compara con un modelo fijado. Esta comparación es el hilo conductor: si el router cambia de modelo, la consistencia y la latencia pueden degradarse aunque el prompt sea idéntico.

| Corrida real | Turnos | Éxito | Score | Tool match | Groundedness | Modelos distintos | Trazas con cambio | Latencia media |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Router libre | 8 | 8/8 | 0,931 | 0,854 | 0,896 | 10 | 7/8 | 24,4 s |
| Modelo fijado (`ling-3.2-flash:free`) | 6 | 6/6 | 1,000 | 1,000 | 1,000 | 1 | 0/6 | 16,1 s |
| N01 aislado, router | 2 | 2/2 | 0,879 | 0,750 | 0,933 | 2 | 2/2 | 35,8 s |
| N01 aislado, fijado | 1 | 1/1 | 0,793 | 0,500 | 0,933 | 1 | 0/1 | 31,2 s |

| Corrida real | Turnos | Éxito | Score | Tool match | Groundedness | Modelo fijado | Observación |
|---|---:|---:|---:|---:|---:|---|---|
| Consistencia | 6 | 6/6 | 0,994 | 1,000 | 0,938 | `nemotron-3.5-lightning:free` | Jaccard C01/C02 = 1,0 |
| Sesgo | 4 | 4/4 | 1,000 | 1,000 | 1,000 | `nemotron-3.5-lightning:free` | B01/B02 usan la misma herramienta |
| Post-fix | 4 | 4/4 | 0,978 | 1,000 | 0,779 | `nemotron-3.5-lightning:free` | Añade “4–7 °C” no respaldado |
| Total real | 29 | 29/29 | 0,970 | 0,943 | 0,926 | — | 139.773 tokens |

La consistencia real fue perfecta en secuencia de herramientas (C01 y C02, Jaccard 1,0) y los pares de sesgo usaron la misma herramienta y argumentos, sin diferencias de latencia atribuibles al nombre (1,8–3,5 s). La caída de *groundedness* en post-fix se explica porque el modelo añadió “4–7 °C” al fragmento de codorniz, que no contenía esa cifra; es un caso de conocimiento general no respaldado por el retriever y una mejora concreta para el *prompt* o para la recuperación.

La medición TTFT con streaming se hizo con `cohere/north-mini-code:free`: 353–638 ms hasta el primer token, 6,25–25,77 ms por token y 38,8–160 tokens/s. El modelo fijado `ling-3.2-flash:free` devolvió 429 en seis intentos de streaming; los errores quedaron registrados en `ttft_measurements` y no se ocultaron. Para las suites posteriores se adoptó `nvidia/nemotron-3.5-lightning:free`: `ling` siguió con 429 y `cohere` dejó de estar disponible en OpenRouter (404). Esa rotación de modelos gratuitos es parte del hallazgo de sostenibilidad.

**Nota:** el score inicial de la corrida fijada fue 0,733. La auditoría de trazas detectó dos falsos negativos del evaluador: `recordar_dato` usó la clave `cliente_Hotel_Costa_especie`, semánticamente equivalente a “Hotel Costa”, y el caso de entradas inválidas fue rechazado sin llamar herramientas. Se normalizaron separadores y se aceptó el rechazo seguro; los `facts_match` se conservaron porque fueron validados contra la base real. El detalle queda en `agroid/benchmarks/rescore.py`.

## 3. Trazabilidad, auditoría y dashboard

El dashboard Streamlit tiene seis pestañas: Resumen, Rendimiento, Calidad y consistencia, Costos y tokens, Explorador de trazas y Seguridad. Lee SQLite y permite filtrar por corrida, grupo experimental, categoría, modo del agente y tipo de corrida; los filtros `Solo corridas reales` y `Excluir intentos con error` separan la evidencia limpia de las pruebas y de los fallos de proveedor. El explorador muestra un waterfall con la duración de cada span y una tabla con `span_id`, `parent_span_id`, tipo, estado y `run_id` de LangSmith. También expone la entrada/salida redactada, los tokens, el costo y las anomalías.

La auditoría busca tres fallos típicos de agentes probabilísticos:

1. **Bucles de razonamiento:** acciones idénticas repetidas dentro del turno; se marcan como `loop`.
2. **Deriva de contexto:** el prompt crece más de 1,5× entre la primera y la última llamada del turno; se marca `context_drift`.
3. **Cuellos de botella:** herramientas o recuperación por sobre umbrales; se listan los spans más lentos.

El dashboard acumuló 126 trazas, 86,5 % de éxito, 11,9 % de error, P95 de 21,7 s, 240.583 tokens y USD 0,0313 de costo equivalente. La tasa de error incluye el intento de consistencia que recibió 429 del proveedor y los seis intentos TTFT fallidos; no se ocultaron. Los 29 turnos reales evaluados suman score 0,970, *tool match* 0,943 y *groundedness* 0,926, con 139.773 tokens. Los hallazgos principales fueron:

| Hallazgo | Evidencia | Interpretación |
|---|---|---|
| El router cambió de modelo dentro del turno | 7 de 8 trazas; 10 modelos distintos | La variabilidad no es solo de prompt: el proveedor cambia el modelo |
| Fijar el modelo elimina el cambio, no la variabilidad de herramientas | N01 fijado usó `consultar_stock` extra; tool_match 0,50 | La selección de herramientas sigue siendo una fuente de error |
| Falsos negativos del evaluador | N05 args 0,0 y N06 tool 0,0 en la primera pasada | Auditar las métricas es tan importante como auditar el agente |
| Consistencia real | C01/C02 Jaccard 1,0; 6/6 éxito | El modelo fijado no cambió de herramienta ante reformulaciones |
| Sesgo | B01/B02 misma herramienta y argumentos | Sin evidencia de sesgo por nombre en esta muestra pequeña |
| Groundedness post-fix | 0,779; “4–7 °C” no estaba en el fragmento recuperado | El modelo añade conocimiento general; endurecer el *grounding* |
| Rotación de modelos gratuitos | `ling` 429; `cohere` 404; se adoptó `nemotron` | La disponibilidad gratuita es un riesgo de sostenibilidad |
| Outlier de latencia | N07 router: 62,0 s; resto 1,8–38 s | Los modelos gratuitos tienen latencias muy dispares |
| Carga simulada | 40 solicitudes, 5 workers, 0 errores, P50 258 ms, P95 921 ms | SQLite con WAL resiste este volumen; no prueba concurrencia masiva |

Las capturas y los resultados por turno están en `docs/evidencias/`: `RESULTADOS_CORRIDAS.md`, `resultados_turnos.csv`, `resultados_consolidados.json`, el anexo `ANEXO_EVIDENCIAS.pdf` y las imágenes `captura_dashboard_resumen.jpeg`, `captura_dashboard_rendimiento.jpeg`, `captura_dashboard_calidad.jpeg`, `captura_dashboard_costos.jpeg`, `captura_dashboard_traza_router.jpeg` y `captura_dashboard_seguridad.jpeg`. El anexo incorpora las vistas directas de LangSmith: `captura_langsmith_01_overview.png` (actividad de 7 días y uso por modelo/herramienta), `captura_langsmith_02_tracing.png` (listado de trazas reales), `captura_langsmith_03_monitoring_traces.png` (evolución de trazas), `captura_langsmith_04_monitoring_llm_calls.png` (llamadas LLM), `captura_langsmith_05_monitoring_tools.png` (herramientas), `captura_langsmith_06_monitoring_run_types.png` (tipos de ejecución) y `captura_langsmith_07_monitoring_cost_tokens.png` (costo y tokens). El waterfall de la traza router muestra cinco modelos distintos en un mismo turno y un tiempo dominado por las llamadas LLM; las herramientas SQL y el retriever aportan milisegundos.

## 4. Optimización, escalabilidad y ética

**Seguridad y ética.** Se implementaron capas complementarias: detección ponderada de inyección, delimitación del mensaje del usuario, política de herramientas con máximo de escrituras, rate limiting por sesión/global, anonimización de PII, moderación, integridad del manual y bloqueo de respuestas que filtren el prompt del sistema. La suite `tests/test_security.py` aprobó 7/7 pruebas: cinco ataques de inyección bloqueados, cuatro consultas de negocio sin falsos positivos, PII redactada, límites de rate limiting, integridad SHA-256/HMAC y detección de un fragmento alterado. En la suite funcional, los dos casos adversariales quedaron bloqueados sin escrituras ni tokens. La limitación es que el detector es heurístico: no cubre paráfrasis nuevas ni ataques multimodales.

**Escalabilidad.** Las propuestas se derivan de los datos, no de intuiciones. La consistencia real (Jaccard 1,0 en C01/C02) y los pares de sesgo (misma herramienta y argumentos) muestran que el problema principal no es el nombre del cliente sino la selección de herramientas y el *grounding*. La rotación de modelos gratuitos (`ling` 429, `cohere` 404) obliga a tratar la disponibilidad como una variable operativa, no como un supuesto.

| Observación | Propuesta | Métrica de respaldo |
|---|---|---|
| Contención de SQLite en carga | PostgreSQL para estado y Redis para memoria/rate limit | Errores `database is locked`, P95 bajo concurrencia |
| Consultas duplicadas | Caché semántica | Tasa de entradas duplicadas del dashboard |
| Costo por categoría | Model routing: modelo ligero para consultas simples | Costo equivalente por grupo |
| Prompt con tokens redundantes | Compresión del system prompt y del plan | Tokens de entrada por turno |
| Recuperación lenta | Precomputar embeddings o índice local | Latencia del span `retriever` |

El costo real es $0 mientras se usen modelos gratuitos; el “costo equivalente” usa `google/gemini-2.5-flash-lite` ($0,10/$0,40 por millón de tokens) solo como referencia para comparar y proyectar. Con los datos observados, el router promedia USD 0,000935 por turno (USD 0,94 por 1.000 turnos) y el modelo fijado USD 0,000419 (USD 0,42 por 1.000), aunque las canastas de casos no son idénticas; por eso se reporta como observación, no como causalidad. El router consumió 5.928 tokens/turno y el fijado 3.454, una diferencia que justifica probar *model routing* por complejidad. La tasa de duplicados del 53 % en la evidencia es artificio de las repeticiones y paráfrasis del benchmark, no tráfico orgánico; una caché semántica requiere medir consultas reales antes de prometer ahorros.

## 5. Conclusiones, reflexiones y referencias

La observabilidad permite convertir fallos silenciosos en evidencia: el router gratuito puede cambiar de modelo, las herramientas pueden repetirse, el contexto puede crecer y la latencia puede concentrarse en un span. La combinación LangSmith + JSONL + SQLite permite auditar sin depender de una sola plataforma, y el dashboard traduce las trazas en decisiones de diseño.

**Reflexión individual — Esteban Pacheco Vega.** [Redactar sin IA: qué aprendió sobre instrumentación, trazabilidad y análisis de fallos; qué aportó al proyecto.]

**Reflexión individual — Javier Perez Mora.** [Redactar sin IA: qué aprendió sobre evaluación, seguridad y escalabilidad; qué aportó al proyecto.]

**Declaración de uso de IA.** El equipo utilizó OpenCode (asistente de IA; modelo DeepSeek V4.1 Flash) entre el 18 y el 23 de noviembre de 2026 como apoyo en la implementación y revisión del paquete `agroid/`, las pruebas automatizadas, el dashboard y el anexo de evidencias; además de redacción y edición del informe, búsqueda y contraste de referencias, y generación de diagramas. Las decisiones de alcance, arquitectura, criterios de evaluación, validación de resultados y las reflexiones individuales fueron realizadas por los integrantes. Las cifras, tablas y capturas provienen de corridas reales ejecutadas por el equipo y fueron contrastadas con SQLite y LangSmith. El uso se declara conforme a la normativa de IA de Duoc UC (Bibliotecas Duoc UC, 2026).

### Referencias

Bibliotecas Duoc UC. (2026). *Uso de inteligencia artificial en trabajos académicos*. https://bibliotecas.duoc.cl/ia

LangChain. (2026). *LangSmith documentation*. https://docs.smith.langchain.com/

LangChain. (2026). *Callbacks*. https://python.langchain.com/docs/concepts/callbacks/

National Institute of Standards and Technology. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)*. https://doi.org/10.6028/NIST.AI.100-1

OpenRouter. (2026). *API reference: Limits*. https://openrouter.ai/docs/api-reference/limits

OWASP. (2025). *OWASP Top 10 for LLM applications*. https://genai.owasp.org/llm-top-10/

SQLite. (2026). *Write-ahead logging*. https://www.sqlite.org/wal.html

Streamlit. (2026). *Streamlit documentation*. https://docs.streamlit.io/
