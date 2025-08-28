"""
Database connection management for Generation Service
"""

import logging
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from generation_service.config_loader import settings

logger = logging.getLogger(__name__)  # type: ignore[assignment]

# Database engines
engine = None
sync_engine = None
async_session_maker = None
sync_session_maker = None

# Base class for SQLAlchemy models
Base = declarative_base()

# Metadata for database operations
metadata = MetaData()


async def init_database():
    """Initialize database connection and create tables"""
    global engine, sync_engine, async_session_maker, sync_session_maker

    try:
        # Create async engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_recycle=300,
        )

        # Create sync engine (for RAG pipeline)
        sync_db_url = settings.DATABASE_URL.replace("aiosqlite://", "sqlite://")
        sync_engine = create_engine(
            sync_db_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_recycle=300,
        )

        # Create session makers
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        sync_session_maker = sessionmaker(
            sync_engine, class_=Session, expire_on_commit=False
        )

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def init_db():
    """Synchronous database initialization for RAG pipeline"""
    global sync_engine, sync_session_maker

    if sync_engine is None:
        try:
            sync_db_url = settings.DATABASE_URL.replace("aiosqlite://", "sqlite://")
            sync_engine = create_engine(
                sync_db_url,
                echo=settings.DEBUG,
                pool_pre_ping=True,
                pool_recycle=300,
            )

            sync_session_maker = sessionmaker(
                sync_engine, class_=Session, expire_on_commit=False
            )

            # Create tables
            Base.metadata.create_all(sync_engine)
            logger.info("Sync database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize sync database: {e}")
            raise


async def close_database():
    """Close database connections"""
    global engine

    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    async with get_session() as session:
        yield session


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Get synchronous database session"""
    if not sync_session_maker:
        init_db()  # Auto-initialize if needed

    session = sync_session_maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for synchronous database session"""
    with get_sync_session() as session:
        yield session


async def health_check() -> bool:
    """Check database connectivity"""
    try:
        async with get_session() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
