"""AgroID Huevos - agente de inventario con observabilidad (EP3).

El paquete separa la lógica del notebook en módulos testeables:

- ``config``: configuración y precios de referencia.
- ``db``: persistencia SQLite del negocio.
- ``rag``: recuperación sobre el manual con verificación de integridad.
- ``tools``: herramientas expuestas al LLM.
- ``agent``: orquestación, memoria, seguridad y trazas.
- ``observability``: logs JSON, almacenamiento, callbacks y métricas.
- ``security``: PII, inyección, rate limiting, moderación e integridad.
- ``benchmarks``: suite dorada, carga y exportación de LangSmith.
- ``dashboard``: tablero Streamlit.
"""

__version__ = "3.0.0"
