"""
OpenAI LLM Client Implementation
"""

import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI

from .base import LLMClient, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """OpenAI API client implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = OpenAI(api_key=config.api_key, base_url=config.api_base)

    REASONING_MODEL_PREFIXES = ("o3", "o4")

    def _is_reasoning_model(self, model: str) -> bool:
        return any(model.startswith(p) for p in self.REASONING_MODEL_PREFIXES)

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        model_override: Optional[str] = None
    ) -> LLMResponse:
        """Generate a completion from messages."""
        try:
            model = model_override or self.config.model
            is_reasoning = self._is_reasoning_model(model)

            kwargs = {
                "model": model,
                "messages": messages,
            }

            if is_reasoning:
                kwargs["max_completion_tokens"] = max_tokens or self.config.max_tokens
            else:
                kwargs["temperature"] = temperature if temperature is not None else self.config.temperature
                kwargs["max_tokens"] = max_tokens if max_tokens is not None else self.config.max_tokens

            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                finish_reason=response.choices[0].finish_reason or "stop",
                raw_response=response
            )

        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            raise

    def complete_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate a completion with tool calling support."""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature if temperature is not None else self.config.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.config.max_tokens
            )

            message = response.choices[0].message

            # Handle tool calls
            if message.tool_calls:
                # Return tool calls as JSON-like content
                tool_calls = []
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })

                return LLMResponse(
                    content=message.content or "",
                    model=response.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    finish_reason="tool_calls",
                    raw_response={"tool_calls": tool_calls, "message": message}
                )

            return LLMResponse(
                content=message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0
                },
                finish_reason=response.choices[0].finish_reason or "stop",
                raw_response=response
            )

        except Exception as e:
            logger.error(f"OpenAI tool completion error: {e}")
            raise
