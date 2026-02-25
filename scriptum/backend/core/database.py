"""Database connection and async session management.

Supports SQLite for development and PostgreSQL for production.
The database URL is resolved from the DATABASE_URL environment variable,
falling back to a local SQLite file at ~/.scriptum/scriptum.db.
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Resolve database URL
_DEFAULT_DB_DIR = Path.home() / ".scriptum"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "scriptum.db"
_DEFAULT_DB_URL = f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"

DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)

# Convert postgres:// to postgresql+asyncpg:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

_is_sqlite = DATABASE_URL.startswith("sqlite")

# Engine configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    # SQLite needs connect_args for check_same_thread
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Connection pool settings for PostgreSQL
    **({} if _is_sqlite else {"pool_size": 10, "max_overflow": 20}),
)

# Enable WAL mode and foreign keys for SQLite via pool connect event
if _is_sqlite:

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage in endpoints:
        async def my_endpoint(db: AsyncSession = Depends(get_async_session)):
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Used for development and first-run setup.

    In production, use Alembic migrations instead.
    """
    _DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the database engine connections."""
    await engine.dispose()
