"""
LLM Abstraction Layer for BLINC Agent V3

Provides a unified interface for different LLM providers:
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude)
- Local models (Ollama, vLLM)

This allows easy switching between providers without changing agent code.
"""

from .base import LLMClient, LLMResponse, LLMConfig
from .factory import get_llm_client, get_reasoning_client, get_fast_client

__all__ = [
    'LLMClient',
    'LLMResponse',
    'LLMConfig',
    'get_llm_client',
    'get_reasoning_client',
    'get_fast_client'
]
