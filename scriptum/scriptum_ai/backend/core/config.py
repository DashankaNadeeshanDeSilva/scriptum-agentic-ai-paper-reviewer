"""Application configuration and settings management.

Configuration is resolved in the following priority (highest first):

1. Environment variables (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``, …)
2. ``~/.scriptum/config.yaml``
3. Built-in defaults

On first run the default ``config.yaml`` is written to ``~/.scriptum/``.
API keys stored in the YAML file are encrypted via :mod:`backend.core.security`.
"""

from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import BaseModel, Field

from scriptum_ai.backend.core.security import get_secret_manager, mask_secret

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CONFIG_DIR = Path.home() / ".scriptum"
_CONFIG_PATH = _CONFIG_DIR / "config.yaml"

# ---------------------------------------------------------------------------
# Pydantic models that mirror the YAML structure
# ---------------------------------------------------------------------------


class LLMProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    api_key: str = ""
    default_model: str = ""
    enabled: bool = False
    base_url: str | None = None  # only used by Ollama


class LLMConfig(BaseModel):
    """Top-level ``llm`` section."""

    default_provider: str = "anthropic"
    providers: dict[str, LLMProviderConfig] = Field(
        default_factory=lambda: {
            "anthropic": LLMProviderConfig(
                default_model="claude-opus-4-6",
                enabled=True,
            ),
            "openai": LLMProviderConfig(
                default_model="gpt-4-turbo",
            ),
            "ollama": LLMProviderConfig(
                base_url="http://localhost:11434",
                default_model="llama2",
            ),
        }
    )


class MCPToolConfig(BaseModel):
    """Configuration for a single MCP tool."""

    api_key: str = ""
    enabled: bool = False
    cx: str = ""  # Google custom search engine ID


class MCPConfig(BaseModel):
    """Top-level ``mcp`` section."""

    perplexity: MCPToolConfig = Field(default_factory=MCPToolConfig)
    google_search: MCPToolConfig = Field(default_factory=MCPToolConfig)


class SemanticScholarConfig(BaseModel):
    api_key: str = ""


class ToggleConfig(BaseModel):
    enabled: bool = True


class APIsConfig(BaseModel):
    """Top-level ``apis`` section."""

    semantic_scholar: SemanticScholarConfig = Field(default_factory=SemanticScholarConfig)
    arxiv: ToggleConfig = Field(default_factory=ToggleConfig)
    crossref: ToggleConfig = Field(default_factory=ToggleConfig)


class AgentsConfig(BaseModel):
    """Top-level ``agents`` section."""

    framework: str = "langgraph"
    max_parallel: int = 3
    timeout: int = 300


class DocumentConfig(BaseModel):
    """Top-level ``document`` section for Docling settings."""

    device: str = "auto"
    ocr_enabled: bool = True
    table_mode: str = "accurate"
    thread_count: int = 4
    max_file_size_mb: int = 100


class AppSettings(BaseModel):
    """Full application settings tree."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    apis: APIsConfig = Field(default_factory=APIsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    document: DocumentConfig = Field(default_factory=DocumentConfig)


# ---------------------------------------------------------------------------
# Environment variable mapping → YAML key path
# ---------------------------------------------------------------------------

_ENV_OVERRIDES: dict[str, list[str]] = {
    "ANTHROPIC_API_KEY": ["llm", "providers", "anthropic", "api_key"],
    "OPENAI_API_KEY": ["llm", "providers", "openai", "api_key"],
    "OLLAMA_BASE_URL": ["llm", "providers", "ollama", "base_url"],
    "PERPLEXITY_API_KEY": ["mcp", "perplexity", "api_key"],
    "GOOGLE_SEARCH_API_KEY": ["mcp", "google_search", "api_key"],
    "GOOGLE_SEARCH_CX": ["mcp", "google_search", "cx"],
    "SEMANTIC_SCHOLAR_API_KEY": ["apis", "semantic_scholar", "api_key"],
    "DOCLING_DEVICE": ["document", "device"],
    "DOCLING_THREADS": ["document", "thread_count"],
}

# Keys in the YAML that hold secrets and should be encrypted on disk
_SECRET_KEYS: set[str] = {"api_key"}

# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def _deep_get(data: dict, keys: list[str]) -> Any:
    """Traverse nested dicts by key path, returning ``None`` on miss."""
    for k in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(k)  # type: ignore[assignment]
    return data


def _deep_set(data: dict, keys: list[str], value: Any) -> None:
    """Set a value in a nested dict, creating intermediate dicts as needed."""
    for k in keys[:-1]:
        data = data.setdefault(k, {})
    data[keys[-1]] = value


def _decrypt_secrets(data: dict) -> dict:
    """Recursively decrypt any ``enc:``-prefixed values in *data*."""
    sm = get_secret_manager()
    out: dict = {}
    for k, v in data.items():
        if isinstance(v, dict):
            out[k] = _decrypt_secrets(v)
        elif isinstance(v, str) and sm.is_encrypted(v):
            out[k] = sm.decrypt(v)
        else:
            out[k] = v
    return out


def _encrypt_secrets(data: dict) -> dict:
    """Recursively encrypt values whose key is in ``_SECRET_KEYS``."""
    sm = get_secret_manager()
    out: dict = {}
    for k, v in data.items():
        if isinstance(v, dict):
            out[k] = _encrypt_secrets(v)
        elif k in _SECRET_KEYS and isinstance(v, str) and v and not sm.is_encrypted(v):
            out[k] = sm.encrypt(v)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------


def _load_yaml() -> dict:
    """Read and parse ``~/.scriptum/config.yaml``.

    If the file does not exist, write the default config and return it.
    """
    if not _CONFIG_PATH.exists():
        defaults = AppSettings().model_dump()
        save_config_dict(defaults)
        logger.info("Created default config at {}", _CONFIG_PATH)
        return defaults

    with _CONFIG_PATH.open("r") as fh:
        raw: dict = yaml.safe_load(fh) or {}

    return _decrypt_secrets(raw)


def _apply_env_overrides(data: dict) -> dict:
    """Overlay environment variables onto the config dict."""
    import os

    for env_var, path in _ENV_OVERRIDES.items():
        value = os.getenv(env_var)
        if value is not None:
            _deep_set(data, path, value)
    return data


def load_settings() -> AppSettings:
    """Load the full settings with YAML + env var resolution.

    Priority: env vars > YAML > defaults.
    """
    data = _load_yaml()
    data = _apply_env_overrides(data)
    return AppSettings.model_validate(data)


def save_config_dict(data: dict) -> None:
    """Persist *data* to ``~/.scriptum/config.yaml`` with secrets encrypted."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    encrypted = _encrypt_secrets(copy.deepcopy(data))
    with _CONFIG_PATH.open("w") as fh:
        yaml.safe_dump(encrypted, fh, default_flow_style=False, sort_keys=False)
    logger.debug("Config written to {}", _CONFIG_PATH)


def save_settings(settings: AppSettings) -> None:
    """Persist an ``AppSettings`` instance to disk."""
    save_config_dict(settings.model_dump())


# ---------------------------------------------------------------------------
# Masked output for the API
# ---------------------------------------------------------------------------


def settings_to_api_response(settings: AppSettings) -> dict:
    """Convert settings to a dict safe for API responses (keys masked)."""
    data = settings.model_dump()

    # LLM providers
    providers_out: dict[str, dict] = {}
    for name, prov in settings.llm.providers.items():
        entry: dict[str, Any] = {
            "enabled": prov.enabled,
            "model": prov.default_model,
            "has_key": bool(prov.api_key),
        }
        if prov.base_url:
            entry["base_url"] = prov.base_url
        if prov.api_key:
            entry["masked_key"] = mask_secret(prov.api_key)
        providers_out[name] = entry

    # MCP tools
    mcp_out: dict[str, dict] = {}
    for name in ("perplexity", "google_search"):
        tool: MCPToolConfig = getattr(settings.mcp, name)
        entry = {"enabled": tool.enabled, "has_key": bool(tool.api_key)}
        if tool.api_key:
            entry["masked_key"] = mask_secret(tool.api_key)
        if name == "google_search" and tool.cx:
            entry["cx"] = tool.cx
        mcp_out[name] = entry

    # APIs
    apis_out: dict[str, dict] = {
        "semantic_scholar": {
            "has_key": bool(settings.apis.semantic_scholar.api_key),
        },
        "arxiv": {"enabled": settings.apis.arxiv.enabled},
        "crossref": {"enabled": settings.apis.crossref.enabled},
    }
    if settings.apis.semantic_scholar.api_key:
        apis_out["semantic_scholar"]["masked_key"] = mask_secret(
            settings.apis.semantic_scholar.api_key
        )

    return {
        "llm": {
            "default_provider": settings.llm.default_provider,
            "providers": providers_out,
        },
        "mcp": mcp_out,
        "apis": apis_out,
        "agents": data["agents"],
    }


# ---------------------------------------------------------------------------
# Convenience accessor (cached singleton per process)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return the application settings singleton.

    Call ``get_settings.cache_clear()`` after writes to force a reload.
    """
    return load_settings()
