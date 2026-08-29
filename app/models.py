from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    cars = relationship(
        "Car",
        back_populates="owner",
        cascade="all, delete-orphan"
    )


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    # Старое поле оставляем для совместимости
    photo_file_id = Column(
        String,
        nullable=True
    )

    # Новый путь к реальной фотографии
    photo_path = Column(
        String,
        nullable=True
    )

    brand = Column(
        String,
        nullable=False
    )

    model = Column(
        String,
        nullable=True
    )

    year = Column(
        String,
        nullable=True
    )

    ai_confidence = Column(
        Float,
        nullable=True
    )

    confirmed_by_user = Column(
        Boolean,
        default=True,
        nullable=False
    )

    location = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    owner = relationship(
        "User",
        back_populates="cars"
    )
