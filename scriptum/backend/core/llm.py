"""LLM client wrapping LiteLLM for provider-agnostic completions.

Supports OpenAI, Anthropic, and Ollama providers with automatic
model string mapping, retry logic, and token/cost tracking.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

import litellm
from loguru import logger

from backend.core.config import get_settings

# Avoid LiteLLM raising on unsupported params across providers
litellm.drop_params = True


@dataclass
class LLMResponse:
    """Response from an LLM completion."""

    text: str = ""
    model: str = ""
    provider: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    cost_usd: float | None = None


# Re-export from the central exception hierarchy for backward compatibility
from backend.core.exceptions import LLMError  # noqa: F401, E402

# Exceptions worth retrying (transient errors)
_RETRYABLE_EXCEPTIONS = (
    litellm.RateLimitError,
    litellm.Timeout,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
)


class LLMClient:
    """Provider-agnostic LLM client using LiteLLM.

    Each agent should get its own ``LLMClient`` instance to maintain
    the agent-independence principle.

    Args:
        provider: LLM provider name. Falls back to config default.
        model: Model name. Falls back to the provider's default.
        api_key: API key override. Falls back to config.
        base_url: Base URL override (useful for Ollama).
        max_retries: Number of retries on transient errors.
        retry_base_delay: Base delay in seconds for exponential backoff.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        self._provider = provider
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

        # Resolve unset values from config
        self._resolve_config()
        self._model_string = self._build_model_string()

    def _resolve_config(self) -> None:
        """Fill in provider/model/api_key/base_url from settings when not set."""
        settings = get_settings()

        if self._provider is None:
            self._provider = settings.llm.default_provider

        provider_cfg = settings.llm.providers.get(self._provider)
        if provider_cfg is None:
            raise LLMError(f"Unknown LLM provider: {self._provider}")

        if self._model is None:
            self._model = provider_cfg.default_model
        if self._api_key is None and provider_cfg.api_key:
            self._api_key = provider_cfg.api_key
        if self._base_url is None and provider_cfg.base_url:
            self._base_url = provider_cfg.base_url

    def _build_model_string(self) -> str:
        """Map provider + model to the string LiteLLM expects.

        - openai / anthropic: model name as-is
        - ollama: ``ollama/{model}``
        """
        if self._provider == "ollama":
            return f"ollama/{self._model}"
        return self._model or ""

    @property
    def provider(self) -> str:
        return self._provider or ""

    @property
    def model(self) -> str:
        return self._model or ""

    @property
    def model_string(self) -> str:
        return self._model_string

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request with retry on transient errors.

        Returns an ``LLMResponse`` with text, usage, latency, and cost.
        Raises ``LLMError`` after exhausting retries.
        """
        kwargs: dict[str, Any] = {
            "model": self._model_string,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["api_base"] = self._base_url
        if response_format:
            kwargs["response_format"] = response_format

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                start = time.monotonic()
                response = await litellm.acompletion(**kwargs)
                elapsed_ms = (time.monotonic() - start) * 1000

                text = response.choices[0].message.content or ""
                usage = {}
                if response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens or 0,
                        "completion_tokens": response.usage.completion_tokens or 0,
                        "total_tokens": response.usage.total_tokens or 0,
                    }

                cost = self.estimate_cost(usage)

                return LLMResponse(
                    text=text,
                    model=self._model_string,
                    provider=self.provider,
                    usage=usage,
                    latency_ms=elapsed_ms,
                    cost_usd=cost,
                )

            except _RETRYABLE_EXCEPTIONS as exc:
                last_error = exc
                delay = self._retry_base_delay * (2**attempt)
                logger.warning(
                    "LLM call attempt {}/{} failed ({}), retrying in {:.1f}s",
                    attempt + 1,
                    self._max_retries,
                    type(exc).__name__,
                    delay,
                )
                await asyncio.sleep(delay)

            except Exception as exc:
                # Non-retryable error — raise immediately
                logger.error("LLM call failed (non-retryable): {}", exc)
                raise LLMError(str(exc)) from exc

        raise LLMError(f"LLM call failed after {self._max_retries} retries: {last_error}")

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream completion chunks as strings.

        Yields text deltas from the LLM response stream.
        Does not retry — if the stream fails, the error propagates.
        """
        kwargs: dict[str, Any] = {
            "model": self._model_string,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["api_base"] = self._base_url

        try:
            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:
            logger.error("LLM stream failed: {}", exc)
            raise LLMError(str(exc)) from exc

    def estimate_cost(self, usage: dict[str, int]) -> float | None:
        """Estimate cost in USD using LiteLLM's cost calculator."""
        if not usage:
            return None
        try:
            return litellm.completion_cost(
                model=self._model_string,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )
        except Exception:
            return None

    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4") -> int:
        """Count tokens in text using LiteLLM's token counter."""
        try:
            return litellm.token_counter(model=model, text=text)
        except Exception:
            # Rough fallback: ~4 chars per token
            return len(text) // 4
