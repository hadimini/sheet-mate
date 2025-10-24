import os
from typing import AsyncGenerator

from sqlalchemy import QueuePool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    poolclass=QueuePool,
    max_overflow=20,
)
AsyncSessionLocal = async_sessionmaker(eengine=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides async database session"""
    with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            session.close()
