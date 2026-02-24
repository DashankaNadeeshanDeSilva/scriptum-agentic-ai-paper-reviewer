"""SCRIPTUM FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle startup and shutdown events."""
    # Startup
    # TODO: Initialize database connection
    # TODO: Initialize LLM clients
    # TODO: Initialize agent manager
    yield
    # Shutdown
    # TODO: Close database connections
    # TODO: Cleanup background tasks


app = FastAPI(
    title="SCRIPTUM API",
    description="Agentic AI Academic Paper Review System",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Include routers after they're implemented
# app.include_router(reviews.router, prefix="/api/v1")
# app.include_router(settings.router, prefix="/api/v1")
# app.include_router(files.router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "scriptum-backend"}
