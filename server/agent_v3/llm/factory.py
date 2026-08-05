"""
LLM Client Factory

Creates appropriate LLM client based on configuration.
"""

import logging
from typing import Optional

from .base import LLMClient, LLMConfig
from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# Cache clients by config hash for reuse
_client_cache = {}


def get_llm_client(config: Optional[LLMConfig] = None, task: str = "reasoning") -> LLMClient:
    """
    Get an LLM client based on configuration.

    Args:
        config: Optional explicit configuration
        task: Task type for default model selection ("reasoning" or "fast")

    Returns:
        Configured LLM client
    """
    if config is None:
        config = LLMConfig.from_env(task=task)

    # Create cache key
    cache_key = f"{config.provider}:{config.model}:{config.api_base}"

    if cache_key in _client_cache:
        return _client_cache[cache_key]

    # Create client based on provider
    if config.provider == "openai":
        client = OpenAIClient(config)
    elif config.provider == "anthropic":
        # Lazy import for optional Anthropic support
        try:
            from .anthropic_client import AnthropicClient
            client = AnthropicClient(config)
        except ImportError:
            logger.warning("Anthropic SDK not installed, falling back to OpenAI")
            config.provider = "openai"
            config.model = LLMConfig.REASONING_MODELS["openai"]
            client = OpenAIClient(config)
    elif config.provider == "ollama":
        # Use OpenAI client with custom base URL for Ollama
        config.api_base = config.api_base or "http://localhost:11434/v1"
        client = OpenAIClient(config)
    else:
        logger.warning(f"Unknown provider {config.provider}, falling back to OpenAI")
        config.provider = "openai"
        client = OpenAIClient(config)

    _client_cache[cache_key] = client
    logger.info(f"Created LLM client: {config.provider}/{config.model}")

    return client


def get_reasoning_client() -> LLMClient:
    """Get client optimized for reasoning tasks (larger model)."""
    return get_llm_client(task="reasoning")


def get_fast_client() -> LLMClient:
    """Get client optimized for fast tasks (smaller model)."""
    return get_llm_client(task="fast")


def clear_client_cache():
    """Clear the client cache (for testing)."""
    global _client_cache
    _client_cache = {}
