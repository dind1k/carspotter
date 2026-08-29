from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


DATABASE_URL = settings.DATABASE_URL

print("DATABASE DRIVER:", DATABASE_URL.split("://")[0])


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)


async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    from app import models

    print(
        "LOADED TABLES:",
        list(Base.metadata.tables.keys()),
    )

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    print("DATABASE INITIALIZED")
