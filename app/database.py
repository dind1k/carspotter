import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")


if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

print("DATABASE DRIVER:", DATABASE_URL.split("://")[0])


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    from app.models import User, Car

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("LOADED TABLES:", list(Base.metadata.tables.keys()))
    print("DATABASE INITIALIZED")
