# Defensa EFT · Paquete de materiales

**Deck principal:** `docs/defensa_eft/diapositivas.pptx`  
**Formato:** 20 × 11,25 in (16:9), 15 láminas: 14 de presentación + anexo.  
**Tiempo objetivo:** 9:00; máximo 10:00.  
**Diseño:** réplica del sistema visual de la PPT de la EP3 (navy `#0B2545`, amarillo `#FDB913`, Calibri, barra lateral y pie). Las láminas 3, 7 y 8 usan los diagramas ejecutivos en PNG; el resto se construyó con shapes nativos.

## Contenido

| Archivo | Uso |
|---|---|
| `diapositivas.pptx` | Deck editable con notas del orador y tiempos por lámina. |
| `guion_10min.md` | Guion minuto a minuto, tabla de tiempos y énfasis por integrante. |
| `demo.md` | Demo pregrabada, chat interactivo y plan B. |
| `qa.md` | 31 preguntas probables, respuestas y mapa de evidencia. |
| `evidencias/` | Capturas del dashboard, LangSmith, gráficos y waterfall. |
| `evidencias/preview/` | PNG de las 15 láminas para revisión rápida. |
| `evidencias/README.md` | Procedencia de cada captura y gráfico. |
| `../../agroid/chat_app.py` | Ventana de chat web sobre Streamlit. |
| `../../Abrir_Chat.bat` | Abre solo el chat en `http://localhost:8502`. |
| `../../Abrir_AgroID.bat` | Abre chat + dashboard. |
| `README.md` | Este archivo. |

## Orden de las 15 láminas

1. Portada.
2. Caso y problema.
3. Arquitectura EFT.
4. Resultados reales EFT.
5. Hallazgos por caso.
6. Prompts versionados.
7. RAG híbrido.
8. Planificación adaptativa.
9. Dashboard EFT.
10. LangSmith y traza real E03.
11. Demo pregrabada.
12. Seguridad y ética.
13. Mejoras y roadmap.
14. Conclusión.
15. Anexo: tabla de 8 casos y preguntas de respaldo.

## Chat web (ventana interactiva)

Para que el profesor escriba sin usar terminal:

1. Doble clic en `Abrir_Chat.bat` (solo chat) o `Abrir_AgroID.bat` (chat + dashboard).
2. Se abre `http://localhost:8502`.
3. Elige modo `auto`, `react` o `plan`.
4. Escribe la consulta y pulsa **Enviar consulta**.
5. La respuesta muestra tools, tokens, plan, fuentes RAG y trace.
6. El botón **Abrir esta consulta en el dashboard** lleva a la traza filtrada.

El lanzador deja una consola minimizada por servidor. No la cierres mientras uses la app.

La ventana usa `run_turn` y las mismas herramientas del agente. No es un mockup. Las escrituras modifican la base de demostración; para volver al estado inicial usa **Datos de demo → Restaurar datos de demo**.

## Cómo ensayar

1. Abrir el PPTX y probar las notas del orador.
2. Ensayar con cronómetro: 9:00 objetivo, 10:00 máximo.
3. Abrir `Abrir_AgroID.bat` o el dashboard en `http://localhost:8501`.
4. Abrir LangSmith en la traza `visual-E03` (opcional).
5. Probar el chat web con 1–2 consultas y el plan B sin internet usando solo el deck o el modo simulado.

## Cómo regenerar

```bash
python docs/generar_graficos_defensa.py
python docs/generar_ppt_eft.py
```

El generador usa las capturas de `docs/defensa_eft/evidencias/` y los datos de `docs/evidencias_eft/`. Si cambias una cifra, actualiza el JSON y vuelve a ejecutar ambos comandos.

## Si hay que recortar

- No recortes resultados, seguridad ni conclusión.
- Puedes saltar el detalle de la traza o el panel 3 de la demo.
- Si el tiempo apremia, menciona el hallazgo del router y las citas sin abrir el anexo.

## Nota sobre la captura de LangSmith

La traza E03 y la lista de trazas son de la corrida EFT del 27/11/2026. La captura de overview de la EP3 se conserva solo como evidencia histórica de la instrumentación; el deck final usa la traza EFT real.
