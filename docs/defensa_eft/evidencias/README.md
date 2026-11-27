# Evidencias del deck EFT

Esta carpeta alimenta `docs/defensa_eft/diapositivas.pptx`. No contiene datos nuevos: organiza capturas y gráficos derivados de la corrida real y del dashboard.

## Capturas reales

| Archivo | Origen | Uso |
|---|---|---|
| `dashboard_overview.png` | Dashboard Streamlit, filtro `real-eft-20261127` + solo reales | Lámina 9 |
| `dashboard_quality_panel.png` | Dashboard, pestaña Calidad y consistencia | Lámina 9 |
| `dashboard_rag.png` | Dashboard, pestaña RAG y planificación | Evidencia de respaldo |
| `dashboard_trace.png` | Dashboard, explorador de trazas | Evidencia de respaldo |
| `langsmith_eft_trace_e03.png` | LangSmith, proyecto `agroid-huevos-ep3`, traza `visual-E03`, 27/11/2026 | Lámina 10 |
| `langsmith_eft_list.png` | LangSmith, lista de trazas EFT y simuladas | Evidencia de respaldo |

La captura de LangSmith **no es un mockup**: muestra la traza real de E03 con 18,44 s, 9.154 tokens, el planificador, dos tools y cuatro llamadas LLM. La lista incluye las 4 trazas reales de la corrida EFT y las simuladas del notebook.

## Gráficos generados

| Archivo | Fuente |
|---|---|
| `chart_casos.png` | `docs/evidencias_eft/resultados_eft.json` |
| `chart_latencia.png` | `docs/evidencias_eft/resultados_eft.json` |
| `chart_rag.png` | `docs/evidencias_eft/rag_eval_20261127-125855.json` |
| `chart_waterfall_e03.png` | spans de `data/observability.db`, traza `visual-E03` |

Las láminas 3, 7 y 8 usan `diagram_diagrama_arquitectura.png`, `diagram_diagrama_rag_hibrido.png` y `diagram_diagrama_planificacion.png`, recortados desde `docs/diagramas_eft/ejecutivo/` para ocupar el ancho completo sin el título ni la leyenda internos.

Se regeneran con:

```bash
python docs/generar_graficos_defensa.py
```

## Activos de portada

`cover_egg.png` y `cover_logo.png` se extrajeron de la PPTX de la EP3 para conservar la identidad visual. No son evidencia de resultados.

## Vista previa

`preview/slide01.png` … `preview/slide15.png` son renders de las 15 láminas para revisión rápida. No reemplazan al PPTX.

## Nota metodológica

- La suite completa tiene 8 casos (`real-eft-20261127`).
- La traza E03 del deck es de una corrida corta adicional (`real-eft-visual-20261127`), ejecutada para obtener spans y captura de LangSmith. Por eso su latencia (18,44 s) no coincide con la de la suite (10,64 s): son ejecuciones distintas del mismo caso.
- El costo real de la corrida fue USD 0; el costo equivalente se calcula con un modelo de referencia y no es un cobro.
