from sqlalchemy import String, Integer, BigInteger, ForeignKey, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cars: Mapped[list["Car"]] = relationship(back_populates="owner")


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Telegram file_id — фото хранится на серверах Telegram, бесплатно
    photo_file_id: Mapped[str] = mapped_column(String(255))

    brand: Mapped[str] = mapped_column(String(100), index=True)
    model: Mapped[str] = mapped_column(String(150), index=True, nullable=True)
    year: Mapped[str] = mapped_column(String(10), nullable=True)

    # confidence от ИИ-распознавания (0-1), пригодится для UI "уточните?"
    ai_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    confirmed_by_user: Mapped[bool] = mapped_column(default=False)

    location: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="cars")
