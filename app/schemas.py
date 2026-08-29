from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RecognizeResult(BaseModel):
    brand: str
    model: Optional[str] = None
    year: Optional[str] = None
    confidence: float


class CarOut(BaseModel):
    id: int
    photo_file_id: str

    brand: str
    model: Optional[str] = None
    year: Optional[str] = None

    ai_confidence: Optional[float] = None

    confirmed_by_user: bool

    location: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True
