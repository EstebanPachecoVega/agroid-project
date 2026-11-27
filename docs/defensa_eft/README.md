# Defensa EFT · Paquete de materiales

Esta carpeta es independiente del informe. Puedes eliminarla sin afectar el PDF ni el notebook; solo tendrías que quitar la referencia del anexo E si decides no entregarla.

## Contenido

| Archivo | Uso |
|---|---|
| `guion_10min.md` | Guion minuto a minuto, con énfasis por integrante. |
| `qa.md` | 28 preguntas probables con respuestas y evidencia. |
| `demo.md` | Demo paso a paso y planes de respaldo. |
| `diapositivas.pdf` | 11 diapositivas para proyectar. |
| `README.md` | Este archivo. |

## Cómo ensayar

1. Leer el guion una vez completo.
2. Ensayar con cronómetro: 10 minutos máximo.
3. Ensayar la demo con el notebook ya ejecutado y el dashboard abierto.
4. Probar el plan B sin internet.
5. Responder 5 preguntas aleatorias de `qa.md` en voz alta.

## Orden sugerido de diapositivas

1. Portada.
2. Caso y problema.
3. Solución y arquitectura.
4. Prompts y RAG.
5. Agente, memoria y planificación.
6. Demo.
7. Observabilidad y resultados.
8. Análisis de trazas.
9. Seguridad y ética.
10. Mejoras y escalabilidad.
11. Conclusión y cierre.

## Si hay que recortar

- No recortes resultados ni conclusión.
- Puedes recortar la demo de memoria y el waterfall.
- Puedes saltar la diapositiva de análisis de trazas si el tiempo apremia, pero menciona el hallazgo del router.

## Cómo eliminar

```powershell
Remove-Item -Recurse -Force docs\defensa_eft
```

Luego elimina la fila “Defensa” del anexo E del informe y reconstruye el PDF:

```powershell
python docs\generar_informe_eft.py
```
