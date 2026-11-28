# Checklist de entrega EFT

**Proyecto:** AgroID Huevos · **Asignatura:** ISY0101 · **Entrega:** EFT  
**Integrantes:** Esteban Pacheco Vega y Javier Perez Mora · **Sección:** 007D

## Entregables

- [x] Informe EFT en Markdown: `docs/INFORME_EFT.md`.
- [x] Informe EFT en PDF: `docs/INFORME_EFT.pdf` (26 páginas).
- [x] Notebook autocontenido: `AgroID_Huevos_EFT.ipynb` (122 celdas, ejecutado sin errores).
- [x] Evidencia EFT: `docs/evidencias_eft/`.
- [x] Defensa: `docs/defensa_eft/` (PPTX de 15 láminas, guion, Q&A y demo pregrabada).
- [x] Chat web: `agroid/chat_app.py` + `Abrir_Chat.bat` / `Abrir_AgroID.bat`.
- [x] Matriz de cumplimiento: `docs/MATRIZ_CUMPLIMIENTO_EFT.md`.
- [x] Análisis de riesgos: `docs/ANALISIS_RIESGOS_EFT.md`.
- [x] Arquitectura: `docs/ARQUITECTURA_EFT.md`.
- [x] Declaración de IA: `docs/DECLARACION_USO_IA.md` y Anexo D del informe.
- [x] README actualizado.

## Verificación técnica

- [x] `python tests/run_all.py` → 51 pruebas aprobadas.
- [x] Suite simulada EFT → 8 casos, score 0,996, 0 errores.
- [x] Suite real EFT → 8 casos, score 0,956, 7 éxito + 1 bloqueado.
- [x] RAG eval → recall@3 0,867, integridad OK.
- [x] Prompt eval → v1 0,90 / v2 1,00, regresión 0,996.
- [x] Planning eval → react/plan/auto 0,994.
- [x] Notebook ejecutado con `nbconvert` sin errores.
- [x] Dashboard inicia y muestra 7 pestañas sin excepciones.
- [x] Chat web inicia en `8502` y ejecuta una consulta real/simulada.
- [x] PDF generado con portada, índice, figuras, tablas, referencias y anexos.

## Verificación de contenido

- [x] Caso organizacional con contexto, procesos, stakeholders, requerimientos y desafíos.
- [x] Formulación de prompts con catálogo, rúbrica y regresión.
- [x] RAG interno + externo con citas y control de integridad.
- [x] Arquitectura y control de contexto.
- [x] Justificación de modelos/herramientas y límites.
- [x] Agente con consulta, escritura y razonamiento.
- [x] Memoria con ventana, resumen y persistencia.
- [x] Planificación adaptativa con replanificación.
- [x] Observabilidad, trazabilidad y dashboard.
- [x] Seguridad, ética, privacidad y normativa.
- [x] Mejoras, SLOs, roadmap y escalabilidad.
- [x] Conclusiones y reflexiones individuales.
- [x] Referencias APA 7.
- [x] Anexos y matriz de cumplimiento.

## Verificación de integridad académica

- [x] Declaración de uso de IA en el informe.
- [x] Reflexiones individuales mantenidas con la voz de cada autor.
- [x] Cifras y tablas respaldadas por evidencia.
- [x] Limitaciones declaradas (citas, ambigüedad, groundedness, modelo fuerte no ejecutado).
- [x] Caso declarado como verosímil con datos simulados.

## Verificación de seguridad

- [x] No hay claves en el repositorio (solo `.env.example`).
- [x] `.env` está en `.gitignore`.
- [x] Las bases SQLite y logs están en `.gitignore`.
- [x] La PII se redacta antes de LLM, logs y trazas.
- [x] Los tests usan correos ficticios.

## Comandos finales

```bash
python tests/run_all.py
python -m agroid.benchmarks.run --mode sim --suite eft
python -m agroid.benchmarks.rag_eval
python -m agroid.benchmarks.prompt_eval
python -m agroid.benchmarks.planning_eval
python docs/generar_notebook_eft.py
python docs/generar_informe_eft.py
python docs/generar_ppt_eft.py
```

## Archivos que se suben a AVA

1. `docs/INFORME_EFT.pdf`.
2. `AgroID_Huevos_EFT.ipynb`.
3. Defensa (si se solicita): `docs/defensa_eft/diapositivas.pptx`.
4. Opcional: repositorio o enlace, si el docente lo solicita.

## Antes de enviar

- Revisar que el nombre del docente y la fecha estén correctos.
- Revisar que las reflexiones individuales tengan el nombre y la voz de cada integrante.
- Confirmar que el informe PDF abre, que el PPTX abre con notas y que el notebook ejecuta en Colab.
- Enviar copia al correo del docente dentro del plazo.
