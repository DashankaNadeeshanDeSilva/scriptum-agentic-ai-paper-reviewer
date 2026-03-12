"""Tests for the SCRIPTUM exception hierarchy."""

import pytest

from scriptum_ai.backend.core.exceptions import (
    AgentError,
    AgentTimeoutError,
    ConfigError,
    DocumentProcessingError,
    LLMError,
    ParsingError,
    ReviewError,
    ReviewNotFoundError,
    ReviewStateError,
    ScriptumError,
)


class TestScriptumErrorHierarchy:
    """All custom exceptions inherit from ScriptumError."""

    def test_base_error_defaults(self):
        exc = ScriptumError()
        assert exc.status_code == 500
        assert exc.detail == "An unexpected error occurred."
        assert str(exc) == "An unexpected error occurred."

    def test_base_error_custom_detail(self):
        exc = ScriptumError("custom message")
        assert exc.detail == "custom message"

    @pytest.mark.parametrize(
        "exc_class,expected_code",
        [
            (ConfigError, 500),
            (ReviewError, 400),
            (ReviewNotFoundError, 404),
            (ReviewStateError, 409),
            (AgentError, 500),
            (AgentTimeoutError, 504),
            (DocumentProcessingError, 422),
            (LLMError, 502),
            (ParsingError, 422),
        ],
    )
    def test_status_codes(self, exc_class, expected_code):
        if exc_class is AgentTimeoutError:
            exc = exc_class("test_agent", 300.0)
        elif exc_class is ReviewNotFoundError:
            exc = exc_class("some-id")
        else:
            exc = exc_class("test")
        assert exc.status_code == expected_code

    def test_all_are_scriptum_errors(self):
        classes = [
            ConfigError,
            ReviewError,
            ReviewNotFoundError,
            ReviewStateError,
            AgentError,
            AgentTimeoutError,
            DocumentProcessingError,
            LLMError,
            ParsingError,
        ]
        for cls in classes:
            assert issubclass(cls, ScriptumError)

    def test_review_not_found_with_id(self):
        exc = ReviewNotFoundError("abc-123")
        assert "abc-123" in exc.detail
        assert exc.status_code == 404

    def test_review_not_found_without_id(self):
        exc = ReviewNotFoundError()
        assert exc.detail == "Review not found."

    def test_agent_timeout_message(self):
        exc = AgentTimeoutError("core_expert", 300.0)
        assert "core_expert" in exc.detail
        assert "300.0s" in exc.detail
        assert exc.status_code == 504

    def test_review_state_error(self):
        exc = ReviewStateError("Cannot submit feedback for pending review.")
        assert exc.status_code == 409
        assert "pending" in exc.detail
