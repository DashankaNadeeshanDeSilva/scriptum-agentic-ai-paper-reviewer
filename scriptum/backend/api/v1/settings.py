"""Settings API endpoints.

Manages application configuration: LLM providers, MCP tools, API keys,
and preferences. Supports connection testing and Ollama model discovery.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from loguru import logger

from backend.api.deps import get_request_id
from backend.core.config import (
    get_settings,
    load_settings,
    save_settings,
    settings_to_api_response,
)
from backend.schemas.review import (
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

    Sends a lightweight test prompt and reports latency.
    Full implementation arrives in Phase 2 (Step 2.3) once LiteLLM is wired in.
    """
    # TODO: Send test prompt via LiteLLM (Phase 2, Step 2.3)
    return TestConnectionResponse(
        success=False,
        latency_ms=None,
        model_info=None,
        error="Not yet implemented. Configure in Step 2.3.",
    )


@router.get("/ollama/models")
async def get_ollama_models(
    request_id: str = Depends(get_request_id),
) -> dict:
    """List available models from a running Ollama instance.

    Queries the Ollama API at the configured base_url and returns
    all locally available models.
    """
    # TODO: Query Ollama REST API at configured base_url/api/tags (Phase 2)
    return {
        "models": [],
        "error": "Not yet implemented. Configure in Step 2.3.",
    }


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
        elif isinstance(value, dict) and hasattr(current_val, "__fields__"):
            _merge_updates(current_val, value)
        else:
            setattr(current, key, value)
