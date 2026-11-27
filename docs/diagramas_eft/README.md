# Diagramas EFT · dos estilos para comparar

Esta carpeta contiene dos familias de diagramas generadas desde el mismo modelo lógico. La idea es que puedas abrir, comparar y elegir sin tocar todavía el informe ni las diapositivas.

## Abrir la comparación

Abre **`index.html`** en el navegador. Muestra los cuatro pares en grande, con enlace a cada PNG.

También puedes abrir **`comparacion.png`**, que resume los ocho diagramas en una sola imagen.

También puedes abrir directamente:

| Diagrama | Técnico minimalista | Ejecutivo con swimlanes |
|---|---|---|
| Arquitectura | `tecnico/diagrama_arquitectura.png` | `ejecutivo/diagrama_arquitectura.png` |
| RAG híbrido | `tecnico/diagrama_rag_hibrido.png` | `ejecutivo/diagrama_rag_hibrido.png` |
| Planificación | `tecnico/diagrama_planificacion.png` | `ejecutivo/diagrama_planificacion.png` |
| Trazas | `tecnico/diagrama_trazas.png` | `ejecutivo/diagrama_trazas.png` |

Cada uno tiene también versión `.svg` para editar o imprimir sin pérdida.

## Recomendación

- **Informe:** técnico minimalista. Es más sobrio, ocupa menos y deja que el texto del informe tenga protagonismo.
- **Defensa:** ejecutivo con swimlanes. Se lee mejor proyectado y separa responsabilidades.
- Si quieres un solo estilo para todo, el **ejecutivo** es más claro en pantalla grande; el **técnico** es más limpio en papel.

## Configuración aplicada por defecto

Para no dejar el informe con los diagramas anteriores, se aplicó esta combinación:

- `docs/diagrama_*.png` → **técnico minimalista**, usado por el informe PDF.
- `docs/defensa_eft/diapositivas.pdf` → **ejecutivo con swimlanes**, usado en la defensa.

Si prefieres todo técnico o todo ejecutivo, se cambia copiando los PNG/SVG elegidos sobre `docs/diagrama_*.png` y regenerando el PDF y las diapositivas. Los dos estilos quedan completos en esta carpeta.

## Diferencias entre estilos

| Aspecto | Técnico minimalista | Ejecutivo con swimlanes |
|---|---|---|
| Fondo | Blanco, sin bandas | Bandas de responsabilidad |
| Cajas | Más compactas | Más grandes y con acento lateral |
| Flechas | Finas, ortogonales | Más gruesas, ortogonales |
| Lectura | Papel / informe | Proyección / reunión |
| Densidad | Mayor | Menor, más aireada |
| Riesgo | Puede verse pequeño en PDF | Puede verse más cargado en papel |

## Qué se corrigió

- Flechas con puertos de borde, no desde el centro de las cajas.
- Routing ortogonal para evitar diagonales que atraviesan cajas.
- Arquitectura: `Seguridad → Router → Agente`, `Agente → Herramientas/RAG/Memoria`, `Memoria → SQLite negocio`, `Observabilidad → Dashboard`. Se eliminó la flecha incorrecta `Dashboard → SQLite negocio`.
- RAG: fuentes separadas hacia `Integridad`, `Seguridad` antes del merge, `Respuesta → Evaluación → Evidencia` en el sentido correcto.
- Planificación: `Clasificador → ReAct/Plan → AgentExecutor → Herramientas → Monitor → Decisión`; la replanificación vuelve al plan, no a la respuesta.
- Trazas: un solo bus de observabilidad alimenta JSONL, SQLite y LangSmith; el dashboard lee SQLite. Ya no hay un mapeo falso `LLM → JSONL`, `Tool → SQLite`, etc.
- Etiquetas con fondo blanco y separación para evitar superposición.
- Leyenda consistente: sólido = flujo principal; punteado = telemetría/verificación.

## Qué falta decidir

1. Qué estilo quieres para el informe.
2. Si quieres el mismo estilo para las diapositivas o el contraste técnico/ejecutivo.
3. Si aceptas que reemplace los PNG actuales `docs/diagrama_*.png` por los elegidos y reconstruya el PDF y las diapositivas.

Los diagramas anteriores ya fueron reemplazados por la versión técnica en el informe y por la ejecutiva en las diapositivas. Si prefieres otra combinación, se cambia copiando los PNG elegidos y regenerando el PDF y las diapositivas.
