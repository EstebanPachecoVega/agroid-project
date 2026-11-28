# Defensa EFT · Guion de 10 minutos

**AgroID Huevos — ISY0101**  
**Integrantes:** Esteban Pacheco Vega y Javier Perez Mora  
**Formato:** defensa individual o compartida, máximo 10 minutos.  
**Deck:** `docs/defensa_eft/diapositivas.pptx` · 15 láminas (14 + anexo).  
**Tiempo objetivo:** 9:00; máximo 10:00. Si te pasas, tienes 1 minuto de margen.

> No leas palabra por palabra. Usa las notas del orador del PPTX y esta tabla como mapa. Si la defensa es individual, cada integrante debe poder responder todo; el énfasis indica dónde profundizar.

## Mapa de tiempos

| # | Lámina | Tiempo | Acumulado | Idea fuerza | Énfasis |
|---:|---|---:|---:|---|---|
| 1 | Portada | 0:15 | 0:15 | Qué entregamos y cómo lo sabemos | Esteban |
| 2 | Caso y problema | 0:40 | 0:55 | Inventario disperso, decisión sin traza | Javier |
| 3 | Arquitectura EFT | 0:45 | 1:40 | Cinco capas, seguridad antes del LLM | Esteban |
| 4 | Resultados reales EFT | 0:45 | 2:25 | 0,956 con brechas medibles | Esteban |
| 5 | Hallazgos por caso | 0:40 | 3:05 | E04 y citas explican la pérdida | Javier |
| 6 | Prompts versionados | 0:40 | 3:45 | v1 0,90 → v2 1,00 | Javier |
| 7 | RAG híbrido | 0:40 | 4:25 | 24 fragmentos, integridad y citas | Javier |
| 8 | Planificación adaptativa | 0:50 | 5:15 | Clasificar, planificar, monitorear y replanificar | Javier |
| 9 | Dashboard EFT | 0:45 | 6:00 | La evidencia se filtra y se audita | Esteban |
| 10 | LangSmith y traza E03 | 0:40 | 6:40 | El tiempo se va en el LLM | Esteban |
| 11 | Demo pregrabada o chat | 0:40 | 7:20 | Tres paneles o 1–2 consultas | Javier |
| 12 | Seguridad y ética | 0:40 | 8:00 | 7/7 pruebas y límites declarados | Javier |
| 13 | Mejoras y roadmap | 0:35 | 8:35 | Cada propuesta nace de una métrica | Javier |
| 14 | Conclusión | 0:25 | 9:00 | Observable, corregible, con límites | Esteban |
| A | Anexo | — | — | Tabla y Q&A de respaldo | Ambos |

## Glosario de casos y consultas

### Casos EFT

| Código | Nombre completo | Qué evalúa |
|---|---|---|
| E01 | RAG externo: temperatura y vida útil USDA | Recuperar y citar una fuente externa |
| E02 | RAG híbrido: almacenamiento de codorniz | Contrastar manual interno con FAO |
| E03 | Complejo: déficit y priorización de pedidos | Calcular déficit y priorizar con dos tools |
| E04 | Ambiguo: «¿Cuánto queda?» | Aclarar antes de consultar |
| E05 | Complejo: pedido urgente de Clínica Sur | Registrar pedido y repriorizar |
| E06 | Adversarial: fuga del prompt del sistema | Bloquear sin tools ni tokens |
| E07 | Memoria: Hotel Costa y déficit | Recuperar hechos tras `reset_memories()` |
| E08 | RAG externo: Codex, huevos rotos y trazabilidad | Citar una fuente técnica externa |

### Consultas RAG

| Código | Nombre completo | Tipo |
|---|---|---|
| R01 | ¿Qué temperatura de refrigeración recomienda el USDA? | externo |
| R02 | ¿Cuánto duran los huevos crudos en refrigeración? | híbrido |
| R03 | ¿Cómo almacenar huevos de codorniz? | híbrido |
| R04 | ¿Qué dice el Codex sobre huevos rotos y trazabilidad? | externo |
| R05 | ¿Cómo se clasifican los huevos por calidad y ovoscopía? | híbrido |
| R06 | ¿Cuál es la tasa de postura de la codorniz? | interno |
| R07 | ¿Cómo priorizar pedidos grandes con poco stock? | interno |
| R08 | ¿Qué cuidados requieren los huevos de pato y ganso? | híbrido |
| R09 | ¿Cómo se almacenan los huevos fértiles de incubación? | híbrido |
| R10 | ¿Qué recomienda la FDA sobre la temperatura de transporte? | externo |

## Antes de empezar

- Abrir el PPTX en modo presentación y probar las notas del orador.
- Tener el dashboard abierto en `http://localhost:8501/?run=real-eft-20261127&solo_reales=1`.
- Tener LangSmith abierto en la traza de E03 (déficit + priorización).
- Tener a mano `docs/defensa_eft/qa.md` y `docs/evidencias_eft/RESULTADOS_EFT.md`.
- Plan B: todas las evidencias están en el deck; no se depende de internet.

## 0:00–0:15 · Portada

**Qué decir.** “Buenos días. Somos Esteban Pacheco y Javier Perez. Presentamos AgroID Huevos, un agente de inventario con RAG híbrido, planificación adaptativa y observabilidad. La pregunta no es solo si responde bien, sino cómo lo sabemos y qué corregiríamos.”

**Qué mostrar.** Portada. Una sola frase, sin leer el título completo.

**Transición.** “El caso nace de un problema concreto: decidir inventario con información dispersa.”

## 0:15–0:55 · Caso y problema

**Qué decir.** “AgroID Huevos es una PYME avícola verosímil, con datos simulados. Stock, producción y pedidos viven en lugares distintos; la priorización depende de la experiencia y no deja traza; el conocimiento técnico queda fuera del flujo. El agente debe responder tres preguntas: qué pedido priorizar, cuánto producir y cómo almacenar. No es un cliente real y no se presenta como producción.”

**Qué mostrar.** Lámina 2: tres dolores, tres preguntas y las métricas del alcance (5 especies, 10 herramientas, 24 fragmentos, 8 casos).

**Transición.** “Para resolverlo, separamos el sistema en capas y pusimos seguridad antes del modelo.”

## 0:55–1:40 · Arquitectura EFT

**Qué decir.** “La arquitectura tiene cinco capas. Control: usuario, seguridad y router. La seguridad redacta PII, detecta inyección y aplica límites antes del LLM. El router decide ReAct o Plan. Orquestación: AgentExecutor con modelo fijo. Conocimiento: 10 herramientas, RAG híbrido, memoria y citas. Persistencia: SQLite de negocio, observabilidad y dashboard. Cada turno deja trace_id, spans, tokens, costo, fuentes y decisiones de seguridad.”

**Qué mostrar.** Lámina 3: diagrama de arquitectura; señalar Seguridad, Router, RAG y Observabilidad.

**Transición.** “Con esa arquitectura, veamos qué obtuvimos en la corrida real.”

## 1:40–2:25 · Resultados reales EFT

**Qué decir.** “La corrida real EFT usó 8 casos y nemotron free. Score 0,956; tool match 0,938; groundedness 0,810; citas 0,667. Fueron 40.432 tokens, 8,1 segundos de media, 17,1 de P95, costo real cero y equivalente 0,0064 dólares. E06 (adversarial: fuga de prompt) se bloqueó sin herramientas ni tokens. La lectura honesta: el agente usa bien las herramientas, pero todavía cita una fuente aunque recupere tres.”

**Qué mostrar.** Lámina 4: cuatro métricas, latencia por caso y panel de lectura.

**Transición.** “Ese promedio esconde qué casos explican la pérdida.”

## 2:25–3:05 · Hallazgos por caso

**Qué decir.** “E04, la consulta ambigua «¿Cuánto queda?», bajó a 0,750 porque consultó stock y pedidos sin pedir aclaración. E07, la de memoria de Hotel Costa, recuperó el dato pero la groundedness fue 0,500. La brecha sistemática son las citas: 0,667. E08, RAG externo de Codex, sí llegó a 1,00, así que el problema es de prompt y verificación, no de recuperación.”

**Qué mostrar.** Gráfico por caso; detenerse en E04 y E07.

**Transición.** “Por eso revisamos los prompts y el RAG por separado.”

## 3:05–3:45 · Prompts versionados

**Qué decir.** “El prompt no es una frase genérica. La v1 tenía 17 líneas y sacó 0,90; la v2 tiene 34 y sacó 1,00 en la rúbrica de siete dimensiones. Agregó jerarquía de fuentes, citas [Mxx]/[Exx], política de herramientas, ambigüedad y criterios de prueba. La regresión funcional se mantuvo en 0,996.”

**Qué mostrar.** Lámina 6: comparación v1/v2 y fragmento real de `system_v2`.

**Transición.** “El RAG es el que alimenta esas citas.”

## 3:45–4:25 · RAG híbrido

**Qué decir.** “El diagrama muestra el RAG de punta a punta: manual interno y corpus externo pasan por integridad SHA-256/HMAC, índice TF-IDF, recuperación top-k por fuente, seguridad, merge/rerank y citas [Mxx]/[Exx]. La respuesta se evalúa y deja evidencia. Obtuvimos recall@3 0,867 y 9 de 10 consultas con fuente externa. La salida citada de E01 se muestra en la demo, lámina 11.”

**Qué mostrar.** Lámina 7: diagrama RAG; señalar integración, seguridad y citas.

**Transición.** “Con ese contexto, el agente puede consultar, escribir y planificar.”

## 4:25–5:15 · Planificación adaptativa

**Qué decir.** “El diagrama de planificación muestra el ciclo: clasificador, ReAct o Plan, AgentExecutor, herramientas, monitor, decisión, crítico, respuesta y métricas. Las 10 herramientas y la memoria se explican en la arquitectura; acá el foco es cómo se decide y se replanifica. La regla clave: si una escritura ya salió bien, no se reintenta; la replanificación vuelve al plan, no a la respuesta. La traza E03 con 19,93 segundos y 9.154 tokens se ve en la lámina 10.”

**Qué mostrar.** Lámina 8: diagrama de planificación; señalar el ciclo y la replanificación.

**Transición.** “Esa traza se puede ver en el dashboard y en LangSmith.”

## 5:15–6:00 · Dashboard EFT

**Qué decir.** “El dashboard tiene siete pestañas. A la izquierda, el resumen de la corrida real: 8 trazas, 87,5% de éxito, 40.432 tokens y P95 de 15,7 segundos. A la derecha, la tabla de calidad: tool match 0,9375, groundedness 0,8099, score 0,956 y citas 0,6667. Abajo, RAG y planificación: 5 fragmentos externos, 4 internos, cobertura 66,7% y cero replanificaciones. Todo se filtra por corrida, grupo, categoría y modo.”

**Qué mostrar.** Lámina 9: captura de Resumen y Calidad; señalar los filtros.

**Transición.** “Para entender el tiempo, bajamos a la traza y a LangSmith.”

## 6:00–6:40 · LangSmith y traza real

**Qué decir.** “Esta es la traza real de E03 (déficit + priorización) en LangSmith, capturada hoy. El turno completo dura 18,44 segundos y consume 9.154 tokens. El planificador se lleva 9,94 segundos; luego dos tools SQL de 0,03 segundos y tres llamadas más al LLM, con la última de 6,16 segundos. En total, cuatro llamadas LLM y dos herramientas. El waterfall confirma lo mismo: el cuello es el modelo, no SQLite.”

**Qué mostrar.** Lámina 10: traza E03 (déficit + priorización) y waterfall; señalar 9,94 s y 0,03 s.

**Transición.** “Con esta evidencia, la demo se reemplaza por tres salidas pregrabadas.”

## 6:40–7:20 · Demo pregrabada o chat interactivo

**Qué decir.** “No ejecutamos Colab en vivo: sería muy largo y depende de la cuota. La demo son tres evidencias. RAG: la consulta al USDA devuelve [E05] y la respuesta correcta. Plan y tools: E03 (déficit + priorización) muestra calcular_deficit y priorizar_pedidos, con trace_id. Memoria y replan: Hotel Costa sobrevive al reset y la prueba de fallo deja replan_count=1. Si piden escribir, abrimos la ventana de chat y hacemos 1–2 consultas; no los 8 casos. Si falla la API, cambiamos a modo simulado en la misma ventana.”

**Qué mostrar.** Lámina 11: tres paneles; si piden live, abrir `Abrir_AgroID.bat`, consultar déficit y RAG, y volver al deck.

**Transición.** “La última capa es seguridad y ética.”

## 7:20–8:00 · Seguridad y ética

**Qué decir.** “Seis controles: PII redactada antes del LLM y la telemetría; detección de inyección; rate limiting; integridad SHA-256/HMAC del corpus; límite de tres escrituras por turno; bloqueo de fuga del prompt. La suite aprobó 7 de 7: 5 ataques bloqueados y 4 consultas legítimas sin falsos positivos. E06 se bloqueó con cero herramientas y cero tokens. Limitación: el detector es heurístico; no cubre paráfrasis nuevas ni ataques multimodales. Por eso hablamos de NIST, OWASP y human-in-the-loop.”

**Qué mostrar.** Lámina 12: seis controles y 7/7.

**Transición.** “Con eso, ¿qué mejoraríamos?”

## 8:00–8:35 · Mejoras y roadmap

**Qué decir.** “Las mejoras salen de los datos. Primero, citas obligatorias y un crítico que bloquee respuestas sin fuente: hoy 0,667. Segundo, aclarar antes de consultar: E04 («¿Cuánto queda?») ejecutó una herramienta extra. Tercero, modelo fijo o routing por complejidad: en la EP3 el router cambió 7 de 8 veces. Cuarto, PostgreSQL y Redis para producción: SQLite con WAL resistió 40 solicitudes con 5 workers, pero no es para múltiples réplicas. Quinto, human-in-the-loop para escrituras de alto valor. El roadmap va de 0 a 12 meses.”

**Qué mostrar.** Lámina 13: tabla observación → propuesta → métrica y timeline.

**Transición.** “Cierro con la conclusión.”

## 8:35–9:00 · Conclusión

**Qué decir.** “El proyecto demuestra que un agente de inventario puede ser útil si se lo rodea de ingeniería: herramientas que validan, RAG con citas, memoria con resumen, planificación con replanificación, observabilidad y seguridad. La corrida real EFT de 0,956 y la EP3 de 0,970 muestran un desempeño alto en un escenario acotado; no prueban que sea productivo. Las brechas son claras: citas 0,667, E04 ambiguo, groundedness 0,810 y dependencia de modelos free. La conclusión no es ‘el agente funciona’, sino ‘el agente es observable, corregible y tiene límites conocidos’. Gracias; quedamos para preguntas.”

**Qué mostrar.** Lámina 14: tres mensajes y cita de cierre.

## Énfasis por integrante

- **Esteban:** arquitectura, observabilidad, LangSmith, trazas, dashboard y seguridad.
- **Javier:** caso, prompts, RAG, planificación, métricas de calidad, costo y roadmap.
- Ambos deben poder responder por la demo, las cifras y las limitaciones.

## Señales de que estás bien de tiempo

- Minuto 1:40: terminaste arquitectura.
- Minuto 4:25: mostraste prompts y RAG.
- Minuto 5:15: mostraste agente, memoria y plan.
- Minuto 6:40: mostraste dashboard y LangSmith.
- Minuto 8:00: mostraste seguridad.
- Minuto 8:35: estás cerrando.

Si vas atrasado, recorta la demo de memoria o el waterfall; no recortes resultados, seguridad ni conclusión.

## Si sobra tiempo

- Abre el anexo (lámina 15) y muestra la tabla completa.
- Responde con `qa.md`, sección “¿Dónde está la evidencia?”.
- Menciona la diferencia entre la captura EP3 de LangSmith y la traza EFT: la primera muestra la instrumentación; la segunda, la corrida de esta entrega.
