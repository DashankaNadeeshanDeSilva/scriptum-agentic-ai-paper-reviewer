"""Settings API endpoints.

Manages application configuration: LLM providers, MCP tools, API keys,
and preferences. Supports connection testing and Ollama model discovery.
"""

from fastapi import APIRouter, Depends

from backend.api.deps import get_request_id

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(
    request_id: str = Depends(get_request_id),
) -> dict:
    """Get the current application settings.

    Returns the full configuration (LLM providers, MCP tools, APIs, preferences)
    with API keys masked for security.
    """
    # TODO: Load from ~/.scriptum/config.yaml via config module
    # TODO: Mask API keys (show last 4 chars only)
    return {
        "llm": {
            "default_provider": "anthropic",
            "providers": {
                "anthropic": {"enabled": False, "model": "claude-sonnet-4-5-20250929", "has_key": False},
                "openai": {"enabled": False, "model": "gpt-4o", "has_key": False},
                "ollama": {"enabled": False, "base_url": "http://localhost:11434", "model": "llama3.1:70b"},
            },
        },
        "mcp": {
            "perplexity": {"enabled": False, "has_key": False},
            "google_search": {"enabled": False, "has_key": False},
        },
        "apis": {
            "semantic_scholar": {"has_key": False},
            "arxiv": {"enabled": True},
            "crossref": {"enabled": True},
        },
        "agents": {
            "framework": "langgraph",
        },
    }


@router.put("")
async def update_settings(
    request_id: str = Depends(get_request_id),
) -> dict:
    """Update application settings.

    Accepts a partial settings object and merges with existing configuration.
    API keys are encrypted before storage.
    """
    # TODO: Parse settings update body
    # TODO: Encrypt any API keys via security module
    # TODO: Write updated config to ~/.scriptum/config.yaml
    return {
        "message": "Settings updated successfully.",
    }


@router.post("/test-connection")
async def test_connection(
    request_id: str = Depends(get_request_id),
) -> dict:
    """Test a connection to an LLM provider or external API.

    Accepts {provider, model, api_key} and sends a test message.
    Returns success status, latency, and model info.
    """
    # TODO: Parse test request (provider, model, api_key)
    # TODO: Send test prompt via LiteLLM
    # TODO: Measure latency and return result
    return {
        "success": False,
        "latency_ms": None,
        "model_info": None,
        "error": "Not yet implemented. Configure in Step 2.3.",
    }


@router.get("/ollama/models")
async def get_ollama_models(
    request_id: str = Depends(get_request_id),
) -> dict:
    """List available models from a running Ollama instance.

    Queries the Ollama API at the configured base_url and returns
    all locally available models.
    """
    # TODO: Query Ollama REST API at configured base_url/api/tags
    # TODO: Return list of model names and sizes
    return {
        "models": [],
        "error": "Not yet implemented. Configure in Step 2.3.",
    }
