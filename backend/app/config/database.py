"""
Database configuration and session management.

Uses PostgreSQL with asyncpg for production, with SQLite fallback for development.
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.models.database import Base

logger = logging.getLogger(__name__)

# Database configuration
# Priority: DATABASE_URL env var > PostgreSQL default > SQLite fallback
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_database_url() -> str:
    """
    Get database URL with smart defaults.

    Priority:
    1. DATABASE_URL environment variable
    2. PostgreSQL default (for Docker setup)
    3. SQLite fallback (for quick development)
    """
    # Check for explicit DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        logger.info(f"Using database from DATABASE_URL: {url.split('@')[-1] if '@' in url else url}")
        return url

    # Check if PostgreSQL is likely available (Docker container)
    postgres_url = "postgresql+asyncpg://geo_user:geo_password@localhost:5432/geo_chat"

    # For now, default to PostgreSQL - user should run /postgres install
    # If PostgreSQL is not available, it will fail at connection time
    # with a clear error message
    use_postgres = os.getenv("USE_POSTGRES", "true").lower() == "true"

    if use_postgres:
        logger.info("Using PostgreSQL database (set USE_POSTGRES=false for SQLite)")
        return postgres_url

    # SQLite fallback
    DATA_DIR.mkdir(exist_ok=True)
    sqlite_url = f"sqlite+aiosqlite:///{DATA_DIR / 'chat.db'}"
    logger.info(f"Using SQLite database: {DATA_DIR / 'chat.db'}")
    return sqlite_url


DATABASE_URL = get_database_url()

# Determine if using PostgreSQL or SQLite
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

# Engine configuration based on database type
if IS_POSTGRES:
    # PostgreSQL with connection pooling
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL logging
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,  # Recycle connections after 5 minutes
    )
else:
    # SQLite - no connection pooling needed
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # SQLite doesn't need pooling
    )

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize the database, creating all tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        db_type = "PostgreSQL" if IS_POSTGRES else "SQLite"
        logger.info(f"Database initialized successfully ({db_type})")
    except Exception as e:
        if IS_POSTGRES and "Connection refused" in str(e):
            logger.error(
                "PostgreSQL connection failed. "
                "Run '/postgres install' to set up the database, "
                "or set USE_POSTGRES=false in .env for SQLite."
            )
        raise


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
            await conn.execute("SELECT 1")
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
