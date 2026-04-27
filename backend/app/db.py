"""Database primitives shared by the whole backend."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """Base SQLAlchemy model for all tables."""


engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a short-lived async database session for FastAPI dependencies."""
    async with AsyncSessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create database tables on startup.

    This project uses create_all for simplicity. If you later decide to evolve the
    schema aggressively, add Alembic migrations on top of this foundation.
    """
    from .models import Account, AppSetting, PanelUser, ScanRun, WorkspaceSnapshot  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
