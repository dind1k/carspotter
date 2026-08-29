from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RecognizeResult(BaseModel):
    brand: str
    model: Optional[str] = None
    year: Optional[str] = None
    confidence: float
    photo_url: Optional[str] = None


class CarCreate(BaseModel):
    photo_url: str
    brand: str
    model: Optional[str] = None
    year: Optional[str] = None
    ai_confidence: Optional[float] = None
    confirmed_by_user: bool = True
    location: Optional[str] = None


class CarOut(BaseModel):
    id: int
    photo_url: str
    brand: str
    model: Optional[str]
    year: Optional[str]
    ai_confidence: Optional[float]
    confirmed_by_user: bool
    location: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
