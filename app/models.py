from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)

    # Game progress
    xp = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)

    cars = relationship(
        "Car",
        back_populates="owner",
        cascade="all, delete-orphan"
    )


class Car(Base):
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    year = Column(Integer, nullable=True)

    # Game data
    rarity = Column(String, default="common", nullable=False)
    image_url = Column(String, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    owner = relationship(
        "User",
        back_populates="cars"
    )
