"""
Database configuration and session management.

Uses SQLite with aiosqlite for zero-infrastructure local storage.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


logger = logging.getLogger(__name__)

# Database URL - from environment or default SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./geo_chat.db",
)

logger.info(f"Using database: {DATABASE_URL}")

# SQLite async engine (no connection pool needed — aiosqlite is in-process)
# Configure SQLite-specific settings for concurrent access
kwargs = {"echo": False}  # Set to True for SQL logging
if DATABASE_URL.startswith("sqlite"):
    kwargs["connect_args"] = {"timeout": 30}

engine = create_async_engine(DATABASE_URL, **kwargs)

# Enable WAL mode for SQLite to allow concurrent reads/writes
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s in ms (belt+suspenders with connect_args timeout)
        cursor.close()

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Verify database connection on startup. Schema is managed by Alembic."""
    await check_db_connection()
    logger.info("Database connection verified")


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")


async def check_db_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_db_session() as session:
        yield session
