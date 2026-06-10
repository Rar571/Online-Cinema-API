import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base


POSTGRESQL_DATABASE_URL = (f"postgresql+asyncpg://{os.getenv("POSTGRES_USERNAME")}:"
                         f"{os.getenv("POSTGRES_PASSWORD")}@{os.getenv("POSTGRES_HOST")}:"
                         f"{os.getenv("POSTGRES_DB_PORT")}/{os.getenv("POSTGRES_DB")}")

postgresql_engine = create_async_engine(POSTGRESQL_DATABASE_URL, echo=False)

AsyncPostgresqlSessionLocal = async_sessionmaker(
    bind=postgresql_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

Base = declarative_base()

async def get_postgresql_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncPostgresqlSessionLocal() as session:
        yield session
