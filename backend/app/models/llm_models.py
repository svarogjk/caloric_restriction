"""
Shared LLM model instances used by geo_loader_service, geo_ranking_service,
survival_analysis_service, and differential_expression_service.

Keys are loaded from environment variables only. Models are always created so
callers can reference model_dict without None-checks; a missing key will
produce an auth error at the first API call, with a clear startup log message.
"""

import logging
import os
from typing import Literal

from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.anthropic import AnthropicProvider

logger = logging.getLogger(__name__)

mistral_key = os.environ.get("MISTRAL_KEY", "")
if not mistral_key:
    logger.error("MISTRAL_KEY not set — Mistral API calls will fail with auth errors")

anthropic_key = os.environ.get("ANTHROPIC_KEY", "")
if not anthropic_key:
    logger.warning("ANTHROPIC_KEY not set — Anthropic API calls will fail with auth errors")

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
