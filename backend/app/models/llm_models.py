"""
Shared LLM models and configurations
Prevents circular imports between services
"""

import logging
import os
from typing import Literal
from httpx import AsyncClient
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.providers.anthropic import AnthropicProvider

logger = logging.getLogger(__name__)

# Initialize client and model (singleton pattern)
model_client = AsyncClient(timeout=3600)

# Load API key
mistral_key = os.environ.get("MISTRAL_KEY", "")
if not mistral_key:
    try:
        with open("app/services/mistral_key.txt") as f:
            mistral_key = f.read().rstrip()
            logger.info("Mistral API key loaded from file")
    except FileNotFoundError:
        logger.warning("No Mistral API key found - using environment fallback")
        mistral_key = os.environ.get("LLM_API_KEY", "")

if not mistral_key:
    logger.error(
        "No Mistral API key found. Set MISTRAL_KEY environment variable or create mistral_key.txt file"
    )
    # Don't raise error here to allow imports, will fail when actually used
    mistral_key = "dummy_key_for_import"

anthropic_key = os.environ.get("ANTHROPIC_KEY", "")
if not anthropic_key:
    try:
        with open("app/services/anthropic_key.txt") as f:
            anthropic_key = f.read().rstrip()
            logger.info("Anthropic API key loaded from file")
    except FileNotFoundError:
        logger.warning("No Anthropic API key found - using environment fallback")
        anthropic_key = os.environ.get("LLM_API_KEY", "")

if not anthropic_key:
    logger.error(
        "No Anthropic API key found. Set ANTHROPIC_KEY environment variable or create anthropic_key.txt file"
    )
    # Don't raise error here to allow imports, will fail when actually used
    anthropic_key = "dummy_key_for_import"

# Create the model instances

mistral_model = MistralModel(
    "mistral-small-latest",
    provider=MistralProvider(
        api_key=mistral_key,
        base_url="https://api.mistral.ai",
        http_client=model_client,
    ),
)

# Create the model instance
anthropic_model = AnthropicModel(
    "claude-sonnet-4-5",
    provider=AnthropicProvider(
        api_key=anthropic_key,
        http_client=model_client,
    ),
)

logger.info("LLM models initialized")


async def close_model_client():
    """Close the Model HTTP client"""
    try:
        if hasattr(model_client, "aclose"):
            await model_client.aclose()
            logger.info("Model client closed")
    except Exception as e:
        logger.warning(f"Error closing Model client: {e}")


ModelType = Literal["anthropic", "mistral"]

model_dict = {"mistral": mistral_model, "anthropic": anthropic_model}
