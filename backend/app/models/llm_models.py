"""
Shared LLM model instances used by geo_loader_service, geo_ranking_service,
survival_analysis_service, and differential_expression_service.

Keys are loaded from environment variables only. Models are always created so
callers can reference model_dict without None-checks; a missing key will
produce an auth error at the first API call, with a clear startup log message.
"""

import logging
import os
from pathlib import Path
from typing import Literal

from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.anthropic import AnthropicProvider

logger = logging.getLogger(__name__)

_SERVICES_DIR = Path(__file__).parent.parent / "services"


def _load_key(env_var: str, filename: str) -> str:
    value = os.environ.get(env_var, "")
    if not value:
        key_file = _SERVICES_DIR / filename
        if key_file.exists():
            value = key_file.read_text().strip()
            logger.info("Loaded %s from file", env_var)
    if not value:
        logger.error("%s not set — API calls will fail with auth errors", env_var)
    return value


mistral_key = _load_key("MISTRAL_KEY", "mistral_key.txt")
anthropic_key = _load_key("ANTHROPIC_KEY", "anthropic_key.txt")

mistral_model = MistralModel(
    "mistral-small-latest",
    provider=MistralProvider(api_key=mistral_key or "missing"),
)

anthropic_model = AnthropicModel(
    "claude-haiku-4-5-20251001",
    provider=AnthropicProvider(api_key=anthropic_key or "missing"),
)

ModelType = Literal["anthropic", "mistral"]

model_dict: dict[ModelType, MistralModel | AnthropicModel] = {
    "mistral": mistral_model,
    "anthropic": anthropic_model,
}
