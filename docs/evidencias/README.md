# Evidencias EP3

Esta carpeta guarda la evidencia sanitizada para el informe y el repositorio.

## Resultados consolidados

```powershell
python -m agroid.benchmarks.results
python docs/generar_anexo_evidencias.py
```

- `RESULTADOS_CORRIDAS.md`: resumen de las 29 corridas reales, consistencia, sesgo, TTFT, carga e incidentes.
- `resultados_turnos.csv`: una fila por turno evaluado.
- `resultados_consolidados.json`: detalle estructurado para el dashboard y el informe.
- `ANEXO_EVIDENCIAS.pdf`: anexo visual con el resumen y las seis capturas del tablero.

## Generar evidencia

```powershell
# 1. Suite funcional simulada
python -m agroid.benchmarks.run --mode sim --suite golden

# 2. Carga simulada
python -m agroid.benchmarks.load --requests 40 --workers 5

# 3. Corridas reales (repartir por la cuota gratuita)
python -m agroid.benchmarks.run --mode real --suite router --model openrouter/free
python -m agroid.benchmarks.run --mode real --suite pinned --model nvidia/nemotron-3.5-lightning:free
python -m agroid.benchmarks.run --mode real --suite consistency --model nvidia/nemotron-3.5-lightning:free
python -m agroid.benchmarks.run --mode real --suite bias --model nvidia/nemotron-3.5-lightning:free
python -m agroid.benchmarks.run --mode real --suite post_fix --model nvidia/nemotron-3.5-lightning:free

# 4. TTFT con streaming
python -m agroid.benchmarks.ttft --model nvidia/nemotron-3.5-lightning:free --repetitions 2

# 5. Exportar trazas de LangSmith
python -m agroid.benchmarks.export
```

## Capturas necesarias

- Árbol de spans en LangSmith (al menos un turno con LLM, Tool y Retriever).
- Dashboard: Resumen, Rendimiento, Calidad, Costos, Explorador y Seguridad.
- Waterfall de un turno complejo.
- Tabla de eventos de seguridad.
- Resultado de la prueba de carga.

## Reglas de sanitización

- No incluir `.env`, claves, tokens ni capturas con credenciales.
- Revisar que las respuestas no contengan RUT, emails ni teléfonos reales.
- No commitear `data/*.db` ni `logs/*.jsonl` sin revisar.
- Los archivos `*.jsonl` y `*.csv` de esta carpeta están en `.gitignore`; si se decide versionar una muestra, revisarla y quitar datos sensibles.
- Las capturas de LangSmith deben mostrar el proyecto `agroid-huevos-ep3`, no la cuenta completa.

## Nombres sugeridos

```text
bench_<run_id>.jsonl / .csv
summary_<run_id>.json
load_<run_id>.json / .csv
ttft_<timestamp>.json
langsmith_<project>_<timestamp>.jsonl
captura_langsmith_trace.png
captura_dashboard_resumen.png
captura_dashboard_calidad.png
captura_dashboard_seguridad.png
```
