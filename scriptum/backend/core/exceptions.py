"""SCRIPTUM exception hierarchy.

All application exceptions inherit from ``ScriptumError``, which carries
an HTTP ``status_code`` and ``detail`` message.  The global exception
handler in ``main.py`` converts these to consistent JSON responses.
"""

from __future__ import annotations


class ScriptumError(Exception):
    """Base exception for all SCRIPTUM errors."""

    status_code: int = 500

    def __init__(self, detail: str = "An unexpected error occurred.") -> None:
        self.detail = detail
        super().__init__(detail)


# --- Configuration -----------------------------------------------------------


class ConfigError(ScriptumError):
    """Invalid configuration or missing required keys."""

    status_code: int = 500


# --- Review lifecycle ---------------------------------------------------------


class ReviewError(ScriptumError):
    """Review lifecycle errors (generic)."""

    status_code: int = 400


class ReviewNotFoundError(ReviewError):
    """Requested review does not exist."""

    status_code: int = 404

    def __init__(self, review_id: object = None) -> None:
        detail = "Review not found." if review_id is None else f"Review not found: {review_id}"
        super().__init__(detail)


class ReviewStateError(ReviewError):
    """Operation invalid for the current review state."""

    status_code: int = 409


# --- Agents -------------------------------------------------------------------


class AgentError(ScriptumError):
    """Agent execution failure."""

    status_code: int = 500


class AgentTimeoutError(AgentError):
    """Agent exceeded the configured execution timeout."""

    status_code: int = 504

    def __init__(self, agent_name: str, timeout_seconds: float) -> None:
        super().__init__(f"Agent '{agent_name}' timed out after {timeout_seconds}s")


# --- Document processing ------------------------------------------------------


class DocumentProcessingError(ScriptumError):
    """Raised when document processing (parsing/conversion) fails."""

    status_code: int = 422


# --- LLM ---------------------------------------------------------------------


class LLMError(ScriptumError):
    """Raised when an LLM call fails after all retries."""

    status_code: int = 502


# --- Parsing ------------------------------------------------------------------


class ParsingError(ScriptumError):
    """Raised when parsing a document or LLM response fails."""

    status_code: int = 422
