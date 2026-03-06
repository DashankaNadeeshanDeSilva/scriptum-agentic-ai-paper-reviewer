"""SCRIPTUM FastAPI application entry point.

Sets up the FastAPI app with CORS, structured logging, request ID middleware,
and all API routers (reviews, settings, files, websocket).
"""

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from backend.api.v1 import chat, files, metrics, reviews, settings, websocket
from backend.core.database import close_db, init_db
from backend.core.exceptions import ScriptumError
from backend.core.logging import generate_request_id, request_id_ctx, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle startup and shutdown events."""
    # Startup
    setup_logging(level="INFO", json_format=True, log_to_file=True)
    logger.info("SCRIPTUM backend starting up")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("SCRIPTUM backend shutting down")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title="SCRIPTUM API",
    description="Agentic AI Academic Paper Review System",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(ScriptumError)
async def scriptum_error_handler(request: Request, exc: ScriptumError) -> JSONResponse:
    """Map ScriptumError subtypes to consistent JSON error responses."""
    req_id = getattr(request.state, "request_id", "")
    logger.warning(
        "Application error: {} — {}",
        type(exc).__name__,
        exc.detail,
        request_id=req_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "message": exc.detail, "request_id": req_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a consistent 422 for request validation failures."""
    req_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": "Request validation failed.",
            "details": jsonable_encoder(exc.errors()),
            "request_id": req_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected errors — log and return generic 500."""
    req_id = getattr(request.state, "request_id", "")
    logger.exception("Unhandled error: {}", exc, request_id=req_id)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred.",
            "request_id": req_id,
        },
    )


# Request ID middleware for correlation
@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Attach a unique request ID to every HTTP request for log correlation."""
    req_id = request.headers.get("X-Request-ID", generate_request_id())
    request.state.request_id = req_id
    token = request_id_ctx.set(req_id)

    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    response.headers["X-Request-ID"] = req_id

    logger.info(
        "Request completed",
        method=request.method,
        path=str(request.url.path),
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
        request_id=req_id,
    )

    request_id_ctx.reset(token)
    return response


# API routers
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/ws")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(chat.ws_router, prefix="/ws")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "scriptum-backend"}
