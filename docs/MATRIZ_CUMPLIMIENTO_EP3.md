# Matriz de cumplimiento — EP3 Observabilidad

**Indicadores:** IE1, IE2, IE3, IE4, IE7, IE8.  
**Estado:** implementación base completa; las celdas marcadas `[CORRIDA REAL]` se completan con las 28 corridas.

| Indicador | Qué exige | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| IE1 (15%) | Métricas de precisión, consistencia, errores | Suite dorada, `tool_match`, `args_match`, `facts_match`, `groundedness`, consistencia por reformulaciones | `agroid/benchmarks/evaluate.py`, tabla `evaluations`, pestaña “Calidad y consistencia” | Implementado; 29 turnos reales, score 0,970 |
| IE2 (10%) | Latencia, tokens, recursos | Spans LLM/tool/retriever, tokens reales o estimados, costo real y equivalente, TTFT, tokens/s, ms/token | `llm_calls`, `ttft_measurements`, `python -m agroid.benchmarks.ttft` | Implementado; TTFT real 353–638 ms |
| IE3 (15%) | Trazabilidad jerárquica y auditoría | LangSmith + JSONL + SQLite; Session/Trace/Span/Parent; detectores de bucles, deriva, iteraciones y cuellos de botella | `agroid/observability/`, `docs/ARQUITECTURA_EP3.md`, pestaña “Explorador de trazas” | Implementado; 100 runs exportados |
| IE4 (10%) | Dashboard interactivo | Streamlit de 6 pestañas con filtros, KPIs, waterfall, costos, calidad y seguridad | `agroid/dashboard/app.py` | Implementado y verificado en navegador |
| IE7 (10%) | Escalabilidad y sostenibilidad | Proyección de costo/1.000, tasa de duplicados para caché, análisis de contención SQLite, propuestas de Redis/Postgres/model routing | `metrics.cost_projection`, `benchmarks/load.py`, informe sección 4 | Implementado; carga 40/5 y proyecciones |
| IE8 (10%) | Seguridad, ética y privacidad | PII, inyección, rate limiting, integridad SHA-256/HMAC, moderación, límites, auditoría de sesgo y XAI | `agroid/security/`, `tests/test_security.py`, pestaña “Seguridad” | Implementado; 7/7 pruebas y sesgo 4/4 |
| Cierre | Informe ≤5 páginas, reflexiones sin IA, declaración, README, repo | `docs/INFORME_TECNICO_EP3.md`, `README.md`, `.env.example`, `.gitignore`, `docs/evidencias/RESULTADOS_CORRIDAS.md` | PDF (4 páginas) + anexo (7 páginas) + repositorio | En progreso |

## Comandos de verificación

```powershell
# Pruebas sin red ni costo
python tests/test_security.py
python tests/test_observability.py
python tests/test_tools.py
python tests/test_agent_sim.py

# Suite simulada completa
python -m agroid.benchmarks.run --mode sim --suite golden

# Carga simulada
python -m agroid.benchmarks.load --requests 40 --workers 5

# Corridas reales (consumen cuota)
python -m agroid.benchmarks.run --mode real --suite router --model openrouter/free
python -m agroid.benchmarks.run --mode real --suite pinned --model nvidia/nemotron-3.5-lightning:free
python -m agroid.benchmarks.run --mode real --suite consistency --model nvidia/nemotron-3.5-lightning:free
python -m agroid.benchmarks.run --mode real --suite bias --model nvidia/nemotron-3.5-lightning:free
python -m agroid.benchmarks.run --mode real --suite post_fix --model nvidia/nemotron-3.5-lightning:free

# TTFT real
python -m agroid.benchmarks.ttft --model nvidia/nemotron-3.5-lightning:free --repetitions 2

# Exportar trazas y abrir dashboard
python -m agroid.benchmarks.export
streamlit run agroid/dashboard/app.py
```

## Evidencia pendiente de completar

- [x] Ejecutar router (8), modelo fijado (6), comparación N01 (1), consistencia (6), sesgo (4) y post-fix (4).
- [x] Ejecutar carga simulada de 40 solicitudes con 5 workers.
- [x] Medir TTFT real (353–638 ms) y throughput (38,8–160 tokens/s).
- [x] Exportar trazas de LangSmith y verificar el proyecto.
- [x] Verificar el dashboard y capturar Resumen, Rendimiento, Calidad, Traza y Seguridad.
- [x] Generar el PDF final (4 páginas) y el anexo de evidencias (7 páginas).
- [ ] Redactar las reflexiones individuales sin IA.
- [x] Ajustar la declaración de IA en `docs/DECLARACION_USO_IA.md` y en el informe.
- [ ] Revisar que no haya claves, PII ni bases crudas en el repositorio y subir a GitHub/GitLab.
