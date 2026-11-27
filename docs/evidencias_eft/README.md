# Evidencia EFT

Esta carpeta contiene la evidencia generada por la suite EFT, la evaluación RAG, la evaluación de prompts y la comparación de planificación. Los datos sensibles se redactan antes de guardarse.

## Archivos principales

| Archivo | Contenido |
|---|---|
| `RESULTADOS_EFT.md` | Resumen legible de la suite real EFT. |
| `resultados_eft.json` | Métricas, filas y trazas de la suite real. |
| `resultados_eft.csv` | Una fila por caso. |
| `rag_eval_*.json` / `.csv` | Recall@3, fuentes, latencia e integridad. |
| `prompt_eval_*.json` / `.csv` | Rúbrica v1/v2 y regresión funcional. |
| `planning_eval_*.json` / `.csv` | Comparación react/plan/auto. |
| `bench_sim-eft-*.csv` / `.jsonl` | Suite simulada. |
| `bench_real-eft-*.csv` / `.jsonl` | Suite real (puede contener solo el último lote si se usó `--resume`). |
| `bench_real-eft-20261127_completo.csv` / `.jsonl` | Suite real EFT completa (8 casos) consolidada desde `resultados_eft.json`. |
| `summary_*.json` | KPIs de la corrida. |
| `progress_*.json` | Progreso de la corrida real. |

## Cómo regenerar

```bash
python tests/run_all.py
python -m agroid.benchmarks.run --mode sim --suite eft --reset
python -m agroid.benchmarks.rag_eval
python -m agroid.benchmarks.prompt_eval
python -m agroid.benchmarks.planning_eval
python docs/consolidar_resultados_eft.py
python docs/importar_evidencia_eft.py
```

## Suite real

```bash
python -m agroid.benchmarks.run --mode real --suite eft --limit 8 \
  --model nvidia/nemotron-3.5-lightning:free --run-id real-eft-20261127
```

Si la corrida se corta, usar `--resume` con el mismo `--run-id`. El costo real de los modelos free es USD 0; el costo equivalente es una estimación con un modelo pagado de referencia.

## Sanitización

- Las trazas guardan `input_redacted` y `output_redacted`.
- La PII se redacta antes de LangSmith, JSONL, SQLite e historial.
- No se guardan claves, tokens de API ni bases crudas en Git.
- Las capturas del dashboard pueden contener rutas locales; se revisan antes de publicar.

## Nota

La suite real EFT se ejecutó con `nvidia/nemotron-3.5-lightning:free`. La comparación con un modelo de gama alta quedó preparada en la suite `validation` (`LLM_MODEL_STRONG`) pero no se ejecutó para no incurrir en costo. Esa limitación se declara en el informe.
