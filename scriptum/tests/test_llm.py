"""Tests for the LLM integration layer (backend.core.llm)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scriptum_ai.backend.core.llm import LLMClient, LLMError, LLMResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_settings(
    provider: str = "anthropic",
    model: str = "claude-opus-4-6",
    api_key: str = "test-key",
    base_url: str | None = None,
):
    """Build a mock AppSettings object."""
    provider_cfg = MagicMock()
    provider_cfg.default_model = model
    provider_cfg.api_key = api_key
    provider_cfg.enabled = True
    provider_cfg.base_url = base_url

    settings = MagicMock()
    settings.llm.default_provider = provider
    settings.llm.providers = {provider: provider_cfg}
    return settings


def _mock_completion_response(text: str = "ok", model: str = "claude-opus-4-6"):
    """Build a mock LiteLLM completion response."""
    choice = MagicMock()
    choice.message.content = text

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


# ---------------------------------------------------------------------------
# Model string construction
# ---------------------------------------------------------------------------


class TestModelStringConstruction:
    @patch("scriptum_ai.backend.core.llm.get_settings")
    def test_openai_model_string(self, mock_gs: MagicMock) -> None:
        mock_gs.return_value = _mock_settings(
            provider="openai", model="gpt-4-turbo", api_key="sk-test"
        )
        client = LLMClient(provider="openai")
        assert client.model_string == "gpt-4-turbo"

    @patch("scriptum_ai.backend.core.llm.get_settings")
    def test_anthropic_model_string(self, mock_gs: MagicMock) -> None:
        mock_gs.return_value = _mock_settings()
        client = LLMClient(provider="anthropic")
        assert client.model_string == "claude-opus-4-6"

    @patch("scriptum_ai.backend.core.llm.get_settings")
    def test_ollama_model_string(self, mock_gs: MagicMock) -> None:
        mock_gs.return_value = _mock_settings(
            provider="ollama",
            model="llama2",
            api_key="",
            base_url="http://localhost:11434",
        )
        client = LLMClient(provider="ollama")
        assert client.model_string == "ollama/llama2"

    @patch("scriptum_ai.backend.core.llm.get_settings")
    def test_unknown_provider_raises(self, mock_gs: MagicMock) -> None:
        settings = MagicMock()
        settings.llm.default_provider = "unknown"
        settings.llm.providers = {}
        mock_gs.return_value = settings

        with pytest.raises(LLMError, match="Unknown LLM provider"):
            LLMClient(provider="unknown")


# ---------------------------------------------------------------------------
# Complete
# ---------------------------------------------------------------------------


class TestLLMClientComplete:
    @pytest.mark.asyncio
    @patch("scriptum_ai.backend.core.llm.litellm.acompletion", new_callable=AsyncMock)
    @patch("scriptum_ai.backend.core.llm.get_settings")
    async def test_successful_completion(self, mock_gs: MagicMock, mock_acomp: AsyncMock) -> None:
        mock_gs.return_value = _mock_settings()
        mock_acomp.return_value = _mock_completion_response("hello")

        client = LLMClient()
        resp = await client.complete(messages=[{"role": "user", "content": "hi"}])

        assert isinstance(resp, LLMResponse)
        assert resp.text == "hello"
        assert resp.provider == "anthropic"
        assert resp.usage["total_tokens"] == 15
        assert resp.latency_ms > 0
        mock_acomp.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("scriptum_ai.backend.core.llm.asyncio.sleep", new_callable=AsyncMock)
    @patch("scriptum_ai.backend.core.llm.litellm.acompletion", new_callable=AsyncMock)
    @patch("scriptum_ai.backend.core.llm.get_settings")
    async def test_retry_on_rate_limit(
        self,
        mock_gs: MagicMock,
        mock_acomp: AsyncMock,
        mock_sleep: AsyncMock,
    ) -> None:
        import litellm as _litellm

        mock_gs.return_value = _mock_settings()
        # Fail twice with rate limit, succeed on third
        mock_acomp.side_effect = [
            _litellm.RateLimitError(
                message="rate limited",
                model="claude-opus-4-6",
                llm_provider="anthropic",
            ),
            _litellm.RateLimitError(
                message="rate limited",
                model="claude-opus-4-6",
                llm_provider="anthropic",
            ),
            _mock_completion_response("ok"),
        ]

        client = LLMClient(max_retries=3)
        resp = await client.complete(messages=[{"role": "user", "content": "test"}])

        assert resp.text == "ok"
        assert mock_acomp.await_count == 3
        assert mock_sleep.await_count == 2

    @pytest.mark.asyncio
    @patch("scriptum_ai.backend.core.llm.asyncio.sleep", new_callable=AsyncMock)
    @patch("scriptum_ai.backend.core.llm.litellm.acompletion", new_callable=AsyncMock)
    @patch("scriptum_ai.backend.core.llm.get_settings")
    async def test_max_retries_exceeded(
        self,
        mock_gs: MagicMock,
        mock_acomp: AsyncMock,
        mock_sleep: AsyncMock,
    ) -> None:
        import litellm as _litellm

        mock_gs.return_value = _mock_settings()
        mock_acomp.side_effect = _litellm.RateLimitError(
            message="rate limited",
            model="claude-opus-4-6",
            llm_provider="anthropic",
        )

        client = LLMClient(max_retries=3)
        with pytest.raises(LLMError, match="failed after 3 retries"):
            await client.complete(messages=[{"role": "user", "content": "test"}])

        assert mock_acomp.await_count == 3

    @pytest.mark.asyncio
    @patch("scriptum_ai.backend.core.llm.litellm.acompletion", new_callable=AsyncMock)
    @patch("scriptum_ai.backend.core.llm.get_settings")
    async def test_non_retryable_error_raises_immediately(
        self, mock_gs: MagicMock, mock_acomp: AsyncMock
    ) -> None:
        import litellm as _litellm

        mock_gs.return_value = _mock_settings()
        mock_acomp.side_effect = _litellm.AuthenticationError(
            message="invalid key",
            model="claude-opus-4-6",
            llm_provider="anthropic",
        )

        client = LLMClient()
        with pytest.raises(LLMError, match="invalid key"):
            await client.complete(messages=[{"role": "user", "content": "test"}])

        assert mock_acomp.await_count == 1  # No retry


# ---------------------------------------------------------------------------
# Stream
# ---------------------------------------------------------------------------


class TestLLMClientStream:
    @pytest.mark.asyncio
    @patch("scriptum_ai.backend.core.llm.litellm.acompletion", new_callable=AsyncMock)
    @patch("scriptum_ai.backend.core.llm.get_settings")
    async def test_streaming_yields_chunks(self, mock_gs: MagicMock, mock_acomp: AsyncMock) -> None:
        mock_gs.return_value = _mock_settings()

        # Build an async iterator of chunks
        chunks = []
        for text in ["Hello", " world", "!"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = text
            chunks.append(chunk)

        # Add a final chunk with no content
        final = MagicMock()
        final.choices = [MagicMock()]
        final.choices[0].delta.content = None
        chunks.append(final)

        async def async_iter():
            for c in chunks:
                yield c

        mock_acomp.return_value = async_iter()

        client = LLMClient()
        collected = []
        async for text in client.stream(messages=[{"role": "user", "content": "test"}]):
            collected.append(text)

        assert collected == ["Hello", " world", "!"]


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


class TestConfigResolution:
    @patch("scriptum_ai.backend.core.llm.get_settings")
    def test_reads_default_provider_from_settings(self, mock_gs: MagicMock) -> None:
        mock_gs.return_value = _mock_settings(
            provider="openai", model="gpt-4-turbo", api_key="sk-test"
        )
        client = LLMClient()  # No explicit provider
        assert client.provider == "openai"
        assert client.model == "gpt-4-turbo"

    @patch("scriptum_ai.backend.core.llm.get_settings")
    def test_explicit_params_override_settings(self, mock_gs: MagicMock) -> None:
        mock_gs.return_value = _mock_settings()
        client = LLMClient(
            provider="anthropic",
            model="claude-sonnet-4-6",
            api_key="my-key",
        )
        assert client.model == "claude-sonnet-4-6"
        assert client.model_string == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


class TestTokenCounting:
    def test_count_tokens_returns_int(self) -> None:
        count = LLMClient.count_tokens("Hello, world!")
        assert isinstance(count, int)
        assert count > 0
