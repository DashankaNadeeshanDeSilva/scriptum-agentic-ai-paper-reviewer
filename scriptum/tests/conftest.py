"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_config() -> dict[str, str]:
    """Provide a sample configuration for testing."""
    return {
        "llm_provider": "anthropic",
        "llm_model": "claude-opus-4-6",
    }
