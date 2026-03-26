from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config.settings import get_settings

settings = get_settings()

# Async engine — connects to Postgres via asyncpg driver
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,   # logs SQL queries in dev
    pool_size=10,
    max_overflow=20,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields a DB session per request.
    Always closes the session after the request finishes.
    """
    async with AsyncSessionLocal() as session:
        yield session
