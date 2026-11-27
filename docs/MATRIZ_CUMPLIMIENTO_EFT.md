# Matriz de cumplimiento EFT

**Proyecto:** AgroID Huevos · **Asignatura:** ISY0101 · **Entrega:** EFT  
**Integrantes:** Esteban Pacheco Vega y Javier Perez Mora · **Sección:** 007D

| Indicador | Qué exige | Dónde se evidencia | Estado |
|---|---|---|---|
| IL1.1 | Formula prompts ajustando estructura y contenido. | `agroid/prompts.py`, sección 3.3, `prompt_eval`, notebook celdas 5. | Cumple. Rúbrica v2 1,00; regresión 0,996. |
| IL1.2 | RAG con fuentes internas y externas. | `agroid/rag.py`, `data/external_corpus.json`, `rag_eval`, sección 3.4. | Cumple. Recall@3 0,867; 9/10 con fuente externa. |
| IL1.3 | Arquitectura con LLM, recuperación y control de contexto. | Secciones 3.1 y 3.5; `context_budget.py`; diagramas. | Cumple. |
| IL1.4 | Justifica diseño, trazabilidad y limitaciones. | Sección 3.6; matriz de decisiones; `ARQUITECTURA_EFT.md`. | Cumple. |
| IL2.1 | Agente con herramientas de consulta, escritura y razonamiento. | `agroid/tools.py`, sección 4.1, tests. | Cumple. 10 herramientas. |
| IL2.2 | Memoria y recuperación de contexto. | `agroid/memory.py`, sección 4.2, `test_memory_long_flow.py`. | Cumple. Ventana + resumen + SQLite. |
| IL2.3 | Planificación y adaptación. | `agroid/planning.py`, sección 4.3, `planning_eval`, prueba de fallo. | Cumple. Replanificación acotada. |
| IL2.4 | Documenta orquestación y flujo. | Sección 4.4; `ARQUITECTURA_EFT.md`; notebook. | Cumple. |
| IL3.1 | Métricas de precisión, latencia y consistencia. | Sección 5; dashboard; `resultados_eft.json`. | Cumple. |
| IL3.2 | Analiza logs y trazas. | Sección 5.5; LangSmith, JSONL, SQLite, dashboard. | Cumple. |
| IL3.3 | Seguridad, ética y privacidad. | Sección 6; `ANALISIS_RIESGOS_EFT.md`; tests. | Cumple con brecha de confirmación humana. |
| IL3.4 | Mejoras basadas en datos. | Sección 7; roadmap y SLOs. | Cumple. |
| IE1–IE15 | Rúbrica de encargo y defensa. | Informe, notebook y `docs/defensa_eft/`. | Cubierto por secciones y materiales. |

## Evidencia principal

| Archivo | Qué contiene |
|---|---|
| `docs/INFORME_EFT.md` / `.pdf` | Informe académico de 22 páginas. |
| `AgroID_Huevos_EFT.ipynb` | Notebook autocontenido ejecutado. |
| `docs/evidencias_eft/resultados_eft.json` | Suite real EFT. |
| `docs/evidencias_eft/rag_eval_*.json` | Evaluación RAG. |
| `docs/evidencias_eft/prompt_eval_*.json` | Rúbrica y regresión de prompts. |
| `docs/evidencias_eft/planning_eval_*.json` | Comparación react/plan/auto. |
| `docs/defensa_eft/` | Guion, Q&A, demo y diapositivas. |
| `tests/` | 50 pruebas automatizadas. |

## Comandos de verificación

```bash
python tests/run_all.py
python -m agroid.benchmarks.run --mode sim --suite eft
python -m agroid.benchmarks.rag_eval
python -m agroid.benchmarks.prompt_eval
python -m agroid.benchmarks.planning_eval
python -m agroid.cli eft
streamlit run agroid/dashboard/app.py
```

## Brechas declaradas

- Cobertura de citas 0,667 en la suite real: el modelo cita una fuente aunque recupere tres.
- E04 ambiguo ejecutó una herramienta adicional.
- Groundedness EFT 0,810, por debajo del SLO 0,85.
- No se ejecutó la suite `validation` con modelo de gama alta por decisión de costo.
- Falta confirmación humana para escrituras de alto valor.
- El prototipo no es productivo: falta autenticación, PostgreSQL/Redis, retención y SLA.
