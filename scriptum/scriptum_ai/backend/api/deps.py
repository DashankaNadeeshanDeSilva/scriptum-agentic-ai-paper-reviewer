"""Shared API dependencies for FastAPI dependency injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from scriptum_ai.backend.core.database import async_session_factory
from scriptum_ai.backend.core.logging import request_id_ctx


def get_request_id(request: Request) -> str:
    """Extract the request ID from the current request state."""
    return getattr(request.state, "request_id", request_id_ctx.get(""))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use in API endpoints.

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
