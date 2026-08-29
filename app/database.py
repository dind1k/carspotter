from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
settings.DATABASE_URL,
echo=True
)

async_session = async_sessionmaker(
engine,
expire_on_commit=False
)

class Base(DeclarativeBase):
"""Base class for all database models."""

async def get_db() -> AsyncSession:
async with async_session() as session:
yield session

async def init_db():
from app import models

```
print("LOADED TABLES:", Base.metadata.tables.keys())

async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

print("DATABASE INITIALIZED")
```
