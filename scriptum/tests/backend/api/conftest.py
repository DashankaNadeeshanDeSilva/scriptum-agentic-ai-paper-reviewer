"""Shared fixtures for API endpoint tests.

Provides an in-memory SQLite database and an httpx AsyncClient
wired to the FastAPI app with dependency overrides.
"""

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_db
from backend.core.database import Base


@pytest.fixture
def tmp_upload_dir(monkeypatch, tmp_path):
    """Override UPLOAD_DIR to use a temp directory."""
    import backend.api.v1.files as files_mod
    import backend.api.v1.reviews as reviews_mod

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(files_mod, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(reviews_mod, "UPLOAD_DIR", upload_dir)
    return upload_dir


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database and yield a session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session, tmp_upload_dir):
    """Create an httpx AsyncClient with dependency overrides."""
    from backend.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf(tmp_upload_dir) -> Path:
    """Create a sample PDF file on disk and return its path."""
    pdf_content = b"%PDF-1.4 sample content for testing"
    pdf_path = tmp_upload_dir / "sample.pdf"
    pdf_path.write_bytes(pdf_content)
    return pdf_path
