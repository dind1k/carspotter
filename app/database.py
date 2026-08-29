```python
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from sqlalchemy.orm import DeclarativeBase

from sqlalchemy import text

from app.config import settings


# =========================
# Database engine
# =========================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True
)


async_session = async_sessionmaker(
    engine,
    expire_on_commit=False
)


# =========================
# Base
# =========================

class Base(DeclarativeBase):
    pass


# =========================
# Database session
# =========================

async def get_db() -> AsyncSession:

    async with async_session() as session:

        yield session


# =========================
# Initialize database
# =========================

async def init_db():

    # Важно:
    # загружаем модели перед create_all()

    from app import models

    print(
        "LOADED TABLES:",
        Base.metadata.tables.keys()
    )


    async with engine.begin() as conn:

        # Создаём таблицы, если их ещё нет
        await conn.run_sync(
            Base.metadata.create_all
        )


        # ---------------------------------
        # Проверяем старую колонку
        # ---------------------------------

        result = await conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'cars'
                """
            )
        )


        columns = {
            row[0]
            for row in result.fetchall()
        }


        print(
            "CARS COLUMNS:",
            columns
        )


        # ---------------------------------
        # Добавляем photo_url
        # ---------------------------------

        if "photo_url" not in columns:

            print(
                "ADDING photo_url COLUMN..."
            )


            await conn.execute(
                text(
                    """
                    ALTER TABLE cars
                    ADD COLUMN photo_url VARCHAR
                    """
                )
            )


            print(
                "photo_url COLUMN ADDED"
            )


        # ---------------------------------
        # Старые записи
        # ---------------------------------
        #
        # Для старых автомобилей у нас нет
        # настоящего URL фотографии.
        #
        # Поэтому временно ставим
        # специальное значение.
        #

        await conn.execute(
            text(
                """
                UPDATE cars
                SET photo_url = '/uploads/no-photo.jpg'
                WHERE photo_url IS NULL
                """
            )
        )


        # Теперь делаем колонку обязательной
        await conn.execute(
            text(
                """
                ALTER TABLE cars
                ALTER COLUMN photo_url
                SET NOT NULL
                """
            )
        )


    print(
        "DATABASE INITIALIZED"
    )
```
