# Análisis de riesgos, seguridad y uso responsable — EFT

**Proyecto:** AgroID Huevos · **Asignatura:** ISY0101 · **Entrega:** EFT  
**Alcance:** prototipo académico con datos simulados. No es asesoría legal ni sanitaria.

## 1. Marco de referencia

El análisis se alinea con:

- **NIST AI RMF 1.0** (Gobernar, Mapear, Medir, Gestionar).
- **OWASP Top 10 for LLM Applications** (inyección, fuga de datos, envenenamiento, manejo inseguro de salida, consumo excesivo, etc.).
- **Ley 19.628** sobre protección de la vida privada y **Ley 21.719**, que introduce un régimen más exigente de datos personales y una Agencia de Protección de Datos. La vigencia de la Ley 21.719 estaba fijada para 2026 y existe un proyecto para postergarla a 2027; antes de producción se debe revisar el estado normativo y la asesoría legal.
- **Codex Alimentarius CXC 15-1976**, **USDA FSIS** y **FDA 21 CFR 118** para el contenido técnico de huevos, con la advertencia de que el corpus son paráfrasis y no reemplaza la fuente original.

## 2. Matriz de riesgos

| Riesgo | Probabilidad | Impacto | Control implementado | Riesgo residual | Responsable |
|---|---|---|---|---|---|
| *Prompt injection* | Alta | Alto | Patrones ponderados, delimitadores, política de herramientas, bloqueo de fuga. | Paráfrasis nuevas o ataques multimodales. | Ingeniería. |
| Fuga de PII | Media | Alto | Redacción antes de LLM, LangSmith, logs e historial. | PII en adjuntos o imágenes. | Privacidad. |
| *Data poisoning* | Media | Alto | SHA-256/HMAC, `scan_untrusted`, exclusión de fragmentos. | Fuente externa comprometida. | Contenido. |
| Escritura no autorizada | Media | Alto | Límite de 3 escrituras, validación, ambigüedad. | Falta confirmación humana. | Operaciones. |
| Alucinación | Alta | Medio | Herramientas, citas, crítico, groundedness. | Conocimiento general no respaldado. | Calidad. |
| Sesgo | Media | Medio | Pares de nombres, revisión. | Muestra pequeña. | Ética. |
| Caída del proveedor | Alta | Medio | Modelo fijado, errores conservados, fallback propuesto. | Sin SLA en free. | Plataforma. |
| Costo excesivo | Media | Medio | Modelos free, límites, proyección. | Modelo pagado sin tope. | Finanzas. |
| Dependencia de librerías | Media | Medio | Versiones fijadas, tests. | CVEs futuras. | Ingeniería. |
| Mal uso | Baja | Alto | Moderación, dominio, rate limit. | Usuario decidido. | Seguridad. |

## 3. Controles implementados

| Control | Implementación | Evidencia |
|---|---|---|
| PII | RUT, email, teléfono y tarjetas redactados. | `tests/test_security.py`; notebook. |
| Inyección | Patrones + delimitadores + política. | 5 ataques bloqueados; E06. |
| Rate limiting | Por sesión/global, cuota diaria y concurrencia. | `rate_limit.py`; test. |
| Integridad RAG | SHA-256/HMAC por fragmento; exclusión. | `integrity.py`; `test_rag_hybrid.py`. |
| Moderación | Categorías dañinas y tema ajeno. | `moderation.py`; test. |
| Límites | 8 iteraciones, 3 escrituras, 2.000 caracteres, 800 tokens. | `config.py`; tests. |
| Fuga de prompt | `leaks_system_prompt` + reemplazo de respuesta. | `test_security.py`. |
| Trazabilidad | `trace_id`, spans, fuentes, plan y crítico. | Dashboard; LangSmith. |

## 4. Brechas para producción

1. **Confirmación humana** en escrituras de alto valor (> 1.000 unidades) o despachos críticos.
2. **Autenticación y autorización** por rol; hoy el prototipo es local.
3. **Rate limiter distribuido** (Redis) en lugar de memoria.
4. **PostgreSQL** con réplicas y backups; SQLite no escala a múltiples réplicas.
5. **Retención y borrado** de datos; derecho de supresión.
6. **Acuerdo de no entrenamiento** con el proveedor del modelo; revisar transferencia internacional.
7. **Fallback automático** de proveedor y *circuit breaker*.
8. **Monitoreo 24/7**, alertas y SLOs.
9. **Validación legal y sanitaria** del contenido técnico.
10. **Evaluación de impacto** y revisión de sesgos con muestra representativa.

## 5. Dilemas éticos

- **Automatización de decisiones:** el agente puede priorizar mal un pedido; la decisión final debe ser humana.
- **Transparencia:** el usuario debe saber que interactúa con un agente y que los datos son simulados.
- **Privacidad:** los nombres y contactos son datos personales; se redactan, pero el proveedor podría retener prompts.
- **Sesgo:** la muestra de pares de nombres es pequeña; no se puede afirmar ausencia de sesgo.
- **Costo ambiental:** los modelos free consumen energía; la eficiencia también es ética.
- **Falsa seguridad alimentaria:** una recomendación de almacenamiento no reemplaza la validación profesional ni la normativa.

## 6. Recomendaciones

1. Implementar *human-in-the-loop* antes de producción.
2. Exigir cita por párrafo y bloquear respuestas sin fuente.
3. Auditar sesgos con una muestra más amplia.
4. Documentar retención, consentimiento y base de licitud.
5. Usar un proveedor con acuerdo de no entrenamiento y región de datos.
6. Agregar *fallback* y *timeout* por proveedor.
7. Revisar el corpus externo con un profesional avícola.
8. Mantener el principio de “el agente propone, la persona decide”.
