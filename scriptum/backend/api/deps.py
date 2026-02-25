"""Shared API dependencies for FastAPI dependency injection."""

from starlette.requests import Request

from backend.core.logging import request_id_ctx


def get_request_id(request: Request) -> str:
    """Extract the request ID from the current request state."""
    return getattr(request.state, "request_id", request_id_ctx.get(""))
