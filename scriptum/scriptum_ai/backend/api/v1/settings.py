"""Settings API endpoints.

Manages application configuration: LLM providers, MCP tools, API keys,
and preferences. Supports connection testing and Ollama model discovery.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, Body, Depends
from loguru import logger

from scriptum_ai.backend.api.deps import get_request_id
from scriptum_ai.backend.core.config import (
    LLMProviderConfig,
    get_settings,
    load_settings,
    save_settings,
    settings_to_api_response,
)
from scriptum_ai.backend.core.llm import LLMClient
from scriptum_ai.backend.schemas.review import (
    SettingsResponse,
    SettingsUpdateRequest,
    TestConnectionRequest,
    TestConnectionResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_current_settings(
    request_id: str = Depends(get_request_id),
) -> dict:
    """Get the current application settings.

    Returns the full configuration (LLM providers, MCP tools, APIs, preferences)
    with API keys masked for security.
    """
    settings = load_settings()
    logger.debug("Settings loaded for request {}", request_id)
    return settings_to_api_response(settings)


@router.put("")
async def update_settings(
    payload: SettingsUpdateRequest = Body(...),
    request_id: str = Depends(get_request_id),
) -> dict:
    """Update application settings.

    Accepts a partial settings object and merges with existing configuration.
    API keys are encrypted before storage.
    """
    current = load_settings()
    updates = payload.model_dump(exclude_unset=True)

    _merge_updates(current, updates)

    save_settings(current)
    # Bust the cached singleton so subsequent reads pick up changes
    get_settings.cache_clear()

    logger.info("Settings updated (request {})", request_id)
    return {"message": "Settings updated successfully."}


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    payload: TestConnectionRequest,
    request_id: str = Depends(get_request_id),
) -> TestConnectionResponse:
    """Test a connection to an LLM provider.

    Creates an ephemeral LLMClient with the supplied credentials and sends
    a lightweight test prompt. Returns success status and latency.
    """
    try:
        client = LLMClient(
            provider=payload.provider,
            model=payload.model,
            api_key=payload.api_key,
        )
        start = time.monotonic()
        response = await client.complete(
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=5,
            temperature=0.0,
        )
        latency = (time.monotonic() - start) * 1000
        logger.info(
            "Connection test succeeded for {} (request {})",
            payload.provider,
            request_id,
        )
        return TestConnectionResponse(
            success=True,
            latency_ms=latency,
            model_info=response.model,
            error=None,
        )
    except Exception as exc:
        logger.warning(
            "Connection test failed for {} (request {}): {}",
            payload.provider,
            request_id,
            exc,
        )
        return TestConnectionResponse(
            success=False,
            latency_ms=None,
            model_info=None,
            error=str(exc),
        )


@router.get("/ollama/models")
async def get_ollama_models(
    request_id: str = Depends(get_request_id),
) -> dict:
    """List available models from a running Ollama instance.

    Queries the Ollama REST API at the configured base_url for
    all locally available models.
    """
    settings = load_settings()
    ollama_cfg = settings.llm.providers.get("ollama", LLMProviderConfig())
    base_url = ollama_cfg.base_url

    if not base_url:
        return {"models": [], "error": "Ollama base_url not configured"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            logger.debug("Found {} Ollama models (request {})", len(models), request_id)
            return {"models": models, "error": None}
    except Exception as exc:
        logger.warning("Failed to query Ollama models: {}", exc)
        return {"models": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_updates(current: Any, updates: dict) -> None:
    """Recursively merge *updates* into the *current* Pydantic model."""
    for key, value in updates.items():
        if not hasattr(current, key):
            continue
        current_val = getattr(current, key)
        if isinstance(value, dict) and isinstance(current_val, dict):
            # Dict of sub-models (e.g. providers)
            for sub_key, sub_value in value.items():
                if sub_key in current_val and isinstance(sub_value, dict):
                    _merge_updates(current_val[sub_key], sub_value)
                else:
                    current_val[sub_key] = sub_value
        elif isinstance(value, dict) and hasattr(current_val, "model_fields"):
            _merge_updates(current_val, value)
        else:
            setattr(current, key, value)
