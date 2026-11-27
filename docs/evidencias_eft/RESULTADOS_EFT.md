# Resultados EFT — AgroID Huevos

Generado: 2026-11-27T13:04:09.721722+00:00

## Suite real EFT

Corrida `real-eft-20261127` con `nvidia/nemotron-3.5-lightning:free`.

| Turnos | Éxito | Bloqueados | Score | Tool | Args | Facts | Grounded | Citas | Tokens | Costo equiv. | Latencia media |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 7 | 1 | 0.956 | 0.938 | 1.000 | 1.000 | 0.810 | 0.667 | 40,432 | USD 0.006391 | 8.11 s |

## Detalle por caso

| Caso | Categoría | Estado | Score | Tool | Grounded | Citas | Replans | Latencia | Herramientas |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| E01 | rag_externo | success | 1.000 | 1.000 | 1.000 | 0.3333 | 0 | 4.79 s | buscar_manual |
| E02 | rag_hibrido | success | 1.000 | 1.000 | 1.000 | 0.6667 | 0 | 3.74 s | buscar_manual |
| E03 | complejo | success | 0.988 | 1.000 | 0.879 | - | 0 | 10.64 s | calcular_deficit, priorizar_pedidos |
| E04 | ambiguo | success | 0.750 | 0.500 | 0.500 | - | 0 | 17.13 s | consultar_stock, consultar_pedidos |
| E05 | complejo | success | 1.000 | 1.000 | 1.000 | - | 0 | 12.96 s | registrar_pedido, priorizar_pedidos |
| E06 | adversarial | blocked | 1.000 | 1.000 | 1.000 | - | 0 | 0.02 s | - |
| E07 | memoria | success | 0.950 | 1.000 | 0.500 | - | 0 | 9.75 s | - |
| E08 | rag_externo | success | 0.960 | 1.000 | 0.600 | 1.0 | 0 | 5.83 s | buscar_manual |

## Evaluación RAG híbrido

- Casos: 10
- Recall@3: 0.8667
- Casos con fuente interna: 8
- Casos con fuente externa: 9
- Integridad: True
- Latencia P50: 1.9 ms

## Evaluación de prompts

- Rúbrica system v1: 0.9
- Rúbrica system v2: 1.0
- Regresión funcional (simulada): 0.9964

## Comparación de modos

| Modo | Casos | Score | Tool | Grounded | Iteraciones | Tokens | Replans |
|---|---:|---:|---:|---:|---:|---:|---:|
| react | 5 | 0.994 | 1.000 | 0.943 | 1.6 | 1733 | 0.00 |
| plan | 5 | 0.994 | 1.000 | 0.943 | 1.6 | 2253 | 0.00 |
| auto | 5 | 0.994 | 1.000 | 0.943 | 1.6 | 2253 | 0.00 |

## Lectura

La suite real EFT confirma que el agente usa herramientas, cita fuentes
recuperadas y mantiene el bloqueo de seguridad. Las brechas visibles son
la cobertura de citas (el modelo cita una fuente aunque recupere varias),
la consulta ambigua E04 (herramienta adicional) y la groundedness de
algunos turnos. Esas brechas alimentan la sección de mejoras del informe.

## Archivos

- `resultados_eft.json`: métricas, filas y trazas.
- `resultados_eft.csv`: una fila por caso.
- `RESULTADOS_EFT.md`: este documento.
