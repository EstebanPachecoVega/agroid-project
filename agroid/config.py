"""Configuración central de AgroID Huevos (EP3).

Las credenciales se leen de variables de entorno o de un archivo ``.env`` local.
Nunca se imprimen ni se escriben en los logs.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

try:  # python-dotenv es opcional en tiempo de ejecución
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent

if load_dotenv is not None:
    load_dotenv(ROOT / ".env", override=False)


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class Settings:
    """Configuración inmutable de una ejecución.

    Los tests pueden cambiar ``AGROID_DATA_DIR`` y ``AGROID_LOGS_DIR`` antes de
    llamar a :func:`get_settings` para usar directorios temporales.
    """

    def __init__(self) -> None:
        self.root = ROOT
        self.data_dir = Path(
            os.getenv("AGROID_DATA_DIR", str(ROOT / "data"))
        ).expanduser().resolve()
        self.logs_dir = Path(
            os.getenv("AGROID_LOGS_DIR", str(ROOT / "logs"))
        ).expanduser().resolve()
        self.evidence_dir = Path(
            os.getenv("AGROID_EVIDENCE_DIR", str(ROOT / "docs" / "evidencias"))
        ).expanduser().resolve()
        for directory in (self.data_dir, self.logs_dir, self.evidence_dir):
            directory.mkdir(parents=True, exist_ok=True)

        self.db_path = self.data_dir / "agroid_huevos.db"
        self.obs_db_path = self.data_dir / "observability.db"
        self.manual_path = self.data_dir / "manual.json"
        self.manifest_path = self.data_dir / "manual_manifest.json"

        # Proveedor LLM (OpenRouter por defecto).
        self.llm_api_key = (
            os.getenv("LLM_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or ""
        ).strip()
        self.llm_base_url = os.getenv(
            "LLM_BASE_URL", "https://openrouter.ai/api/v1"
        ).strip()
        self.llm_model = os.getenv("LLM_MODEL", "openrouter/free").strip()
        self.llm_model_pinned = os.getenv(
            "LLM_MODEL_PINNED", "nvidia/nemotron-3.5-lightning:free"
        ).strip()
        self.llm_embed_model = os.getenv(
            "LLM_EMBED_MODEL", "openai/text-embedding-3-small"
        ).strip()
        self.temperature = _float(os.getenv("AGROID_TEMPERATURE"), 0.0)

        # LangSmith.
        self.langsmith_api_key = os.getenv("LANGSMITH_API_KEY", "").strip()
        self.langsmith_project = os.getenv(
            "LANGSMITH_PROJECT", "agroid-huevos-ep3"
        ).strip()
        self.langsmith_endpoint = os.getenv(
            "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
        ).strip()
        self.langsmith_tracing_requested = _bool(
            os.getenv("LANGSMITH_TRACING"), True
        )

        # Límites del agente y de seguridad.
        self.max_iterations = _int(
            os.getenv("AGROID_MAX_ITERATIONS"), 8
        )
        self.max_input_chars = _int(
            os.getenv("AGROID_MAX_INPUT_CHARS"), 2000
        )
        self.max_output_tokens = _int(
            os.getenv("AGROID_MAX_OUTPUT_TOKENS"), 800
        )
        self.max_tool_writes = _int(
            os.getenv("AGROID_MAX_TOOL_WRITES"), 3
        )
        self.rate_limit_per_minute = _int(
            os.getenv("AGROID_RATE_LIMIT_PER_MINUTE"), 15
        )
        self.rate_limit_turns_per_day = _int(
            os.getenv("AGROID_RATE_LIMIT_TURNS_PER_DAY"), 45
        )
        self.max_concurrent = _int(
            os.getenv("AGROID_MAX_CONCURRENT"), 3
        )
        self.injection_block_threshold = _float(
            os.getenv("AGROID_INJECTION_BLOCK_THRESHOLD"), 0.6
        )
        self.injection_flag_threshold = _float(
            os.getenv("AGROID_INJECTION_FLAG_THRESHOLD"), 0.3
        )

        # Modelo de referencia para el costo equivalente (no se usa para inferir).
        self.reference_model = os.getenv(
            "AGROID_REFERENCE_MODEL", "google/gemini-2.5-flash-lite"
        ).strip()
        self.reference_input_per_mtok = _float(
            os.getenv("AGROID_REFERENCE_INPUT_PER_MTOK"), 0.10
        )
        self.reference_output_per_mtok = _float(
            os.getenv("AGROID_REFERENCE_OUTPUT_PER_MTOK"), 0.40
        )

        # Precios por millón de tokens para modelos pagados conocidos.
        default_prices = {
            "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
            "openai/gpt-4.1-nano": {"input": 0.10, "output": 0.40},
            "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "deepseek/deepseek-chat": {"input": 0.2574, "output": 1.0287},
            "meta-llama/llama-3.3-70b-instruct": {
                "input": 0.71,
                "output": 0.71,
            },
        }
        custom_prices = os.getenv("AGROID_PRICE_TABLE", "").strip()
        if custom_prices:
            try:
                parsed = json.loads(custom_prices)
                if isinstance(parsed, dict):
                    default_prices.update(parsed)
            except json.JSONDecodeError:
                pass
        self.price_table: dict[str, dict[str, float]] = default_prices

        # Firma opcional del manifiesto del manual.
        self.manifest_hmac_key = os.getenv(
            "AGROID_MANIFEST_HMAC_KEY", ""
        ).strip()

    # ------------------------------------------------------------------
    # LangSmith
    # ------------------------------------------------------------------
    def configure_langsmith(self) -> bool:
        """Configura las variables que LangChain lee para trazar en LangSmith.

        Devuelve ``True`` si el trazado queda habilitado. Si no hay clave, el
        agente sigue funcionando con logs JSON y SQLite locales.
        """
        enabled = bool(self.langsmith_tracing_requested and self.langsmith_api_key)
        os.environ["LANGSMITH_TRACING"] = "true" if enabled else "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if enabled else "false"
        os.environ["LANGSMITH_PROJECT"] = self.langsmith_project
        os.environ["LANGSMITH_ENDPOINT"] = self.langsmith_endpoint
        if self.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
        return enabled

    @property
    def langsmith_enabled(self) -> bool:
        return bool(self.langsmith_tracing_requested and self.langsmith_api_key)

    # ------------------------------------------------------------------
    # Costos
    # ------------------------------------------------------------------
    @staticmethod
    def is_free_model(model: str) -> bool:
        model = (model or "").strip().lower()
        return model == "openrouter/free" or model.endswith(":free")

    def cost_for(
        self,
        model: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
    ) -> dict[str, Any]:
        """Calcula costo real y costo equivalente.

        - Los modelos ``:free`` y ``openrouter/free`` tienen costo real 0.
        - El costo equivalente usa un modelo pagado de referencia para poder
          comparar consumo y proyectar escalabilidad.
        - Si el modelo pagado no está en la tabla, el costo real queda en 0 y
          se marca ``cost_estimated=True``.
        """
        prompt = max(0, int(prompt_tokens or 0))
        completion = max(0, int(completion_tokens or 0))
        model = (model or self.llm_model).strip()

        actual = 0.0
        estimated = False
        if not self.is_free_model(model):
            prices = self.price_table.get(model)
            if prices:
                actual = (
                    prompt / 1_000_000 * float(prices.get("input", 0.0))
                    + completion / 1_000_000 * float(prices.get("output", 0.0))
                )
            else:
                estimated = True

        equivalent = (
            prompt / 1_000_000 * self.reference_input_per_mtok
            + completion / 1_000_000 * self.reference_output_per_mtok
        )
        return {
            "cost_usd": round(actual, 8),
            "cost_equivalent_usd": round(equivalent, 8),
            "cost_estimated": estimated,
            "reference_model": self.reference_model,
        }

    # ------------------------------------------------------------------
    # Resumen seguro (sin credenciales)
    # ------------------------------------------------------------------
    def safe_summary(self) -> dict[str, Any]:
        return {
            "llm_base_url": self.llm_base_url,
            "llm_model": self.llm_model,
            "llm_model_pinned": self.llm_model_pinned,
            "llm_key_configured": bool(self.llm_api_key),
            "langsmith_enabled": self.langsmith_enabled,
            "langsmith_project": self.langsmith_project,
            "db_path": str(self.db_path),
            "obs_db_path": str(self.obs_db_path),
            "logs_dir": str(self.logs_dir),
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Limpia la caché; útil en tests que cambian variables de entorno."""
    get_settings.cache_clear()
    return get_settings()
