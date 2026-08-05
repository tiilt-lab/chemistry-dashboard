"""
Base LLM Client Interface

Defines the abstract interface for LLM providers.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM clients."""
    provider: str = "openai"  # openai, anthropic, ollama
    model: str = "gpt-4.1-mini"
    temperature: float = 0.1
    max_tokens: int = 1000
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    # Model presets for different tasks
    REASONING_MODELS = {
        "openai": "gpt-4.1",
        "anthropic": "claude-sonnet-4-20250514",
        "ollama": "llama3.1:70b"
    }

    FAST_MODELS = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-3-5-20241022",
        "ollama": "llama3.1:8b"
    }

    @classmethod
    def from_env(cls, task: str = "reasoning") -> "LLMConfig":
        """Create config from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "openai")

        if task == "reasoning":
            model = os.getenv("LLM_REASONING_MODEL", cls.REASONING_MODELS.get(provider, "gpt-4o"))
        else:
            model = os.getenv("LLM_FAST_MODEL", cls.FAST_MODELS.get(provider, "gpt-4o-mini"))

        return cls(
            provider=provider,
            model=model,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            api_key=os.getenv("OPENAI_API_KEY") if provider == "openai"
                    else os.getenv("ANTHROPIC_API_KEY") if provider == "anthropic"
                    else None,
            api_base=os.getenv("LLM_API_BASE")
        )


@dataclass
class LLMResponse:
    """Standardized response from LLM."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    raw_response: Any = None

    def to_json(self) -> Optional[Dict]:
        """Parse content as JSON if possible."""
        try:
            return json.loads(self.content)
        except json.JSONDecodeError:
            return None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        model_override: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate a completion from messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: Optional format specification (e.g., {"type": "json_object"})
            model_override: Optional model to use instead of default

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    def complete_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a completion with tool/function calling support.

        Args:
            messages: List of message dicts
            tools: List of tool definitions in OpenAI format
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            LLMResponse with tool calls or content
        """
        pass

    def chat(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> LLMResponse:
        """
        Simple chat interface with system and user messages.

        Args:
            system: System prompt
            user: User message
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: Optional format specification

        Returns:
            LLMResponse with generated content
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        return self.complete(messages, temperature, max_tokens, response_format)

    def json_chat(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Chat that returns parsed JSON.

        Args:
            system: System prompt (should instruct to return JSON)
            user: User message

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        response = self.chat(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        return response.to_json()
