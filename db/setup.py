"""Database setup and connection management."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from utils.config import get_settings

Base = declarative_base()
engine = None
async_session_factory = None


async def init_db():
    """Initialize database engine and session factory (when DATABASE_URL is set)."""
    global engine, async_session_factory
    settings = get_settings()
    if not settings.database_url:
        return
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db() -> AsyncSession:
    """Dependency for FastAPI - yields database session."""
    if async_session_factory is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL in .env")
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
