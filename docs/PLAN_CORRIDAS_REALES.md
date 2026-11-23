# Plan de corridas reales — completado

La cuenta de OpenRouter tiene menos de 10 créditos: **50 solicitudes/día** para modelos `:free`. El runner consulta la cuota antes de empezar y se detiene si no alcanza.

## Estado final

| Fecha | Suite | Turnos | Resultado |
|---|---|---:|---|
| 19-nov | Router `openrouter/free` | 8 | score 0,931; 10 modelos; 7/8 trazas con cambio |
| 19-nov | Fijado `ling-3.2-flash:free` | 6 | score 1,000 tras corregir el evaluador |
| 19-nov | Comparación N01 | 1 | score 0,793; el fijado añadió una consulta extra |
| 23-nov | Consistencia `nemotron-3.5-lightning:free` | 6 | score 0,994; Jaccard C01/C02 = 1,0 |
| 23-nov | Sesgo `nemotron-3.5-lightning:free` | 4 | score 1,000; misma herramienta en cada par |
| 23-nov | Post-fix `nemotron-3.5-lightning:free` | 4 | score 0,978; groundedness 0,779 |
| 19/23-nov | TTFT `cohere/north-mini-code:free` | 4 mediciones | 353–638 ms; 38,8–160 tokens/s |
| 19-nov | Carga simulada | 40 | 0 errores; P50 258 ms; P95 921 ms |
| **Total real** | | **29** | **score 0,970; 139.773 tokens** |

## Incidencias registradas

- `inclusionai/ling-3.2-flash:free` devolvió 429 en la suite de consistencia del 23-nov y en 6 intentos de TTFT.
- `cohere/north-mini-code:free` dejó de estar disponible en OpenRouter (404) después de las mediciones TTFT.
- Se adoptó `nvidia/nemotron-3.5-lightning:free`, validado con tool calling, para consistencia, sesgo y post-fix.
- Los fallos se conservan en SQLite y en la evidencia; no se ocultaron.

## Cierre pendiente

```powershell
# Exportar trazas de LangSmith
python -m agroid.benchmarks.export --days 7 --limit 100

# Regenerar el PDF y verificar el límite de 5 páginas
python docs/generar_informe_pdf.py

# Dashboard
streamlit run agroid/dashboard/app.py
```

- [ ] Escribir las reflexiones individuales sin IA.
- [ ] Ajustar la declaración de IA según la política de la asignatura.
- [ ] Revisar que `.env`, `data/*.db`, `logs/` y los JSONL crudos no estén rastreados.
- [ ] Commit y push a GitHub/GitLab.
- [ ] Enviar por AVA y correo al docente.
