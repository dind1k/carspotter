import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Header,
    Form,
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from fastapi.responses import FileResponse

from app.database import get_db
from app.models import Car, User
from app.schemas import CarOut, RecognizeResult
from app.services.recognition import recognize_car
from app.services.telegram_auth import validate_init_data


router = APIRouter(
    prefix="/api/cars",
    tags=["cars"]
)


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================
# Telegram user auth
# =========================

async def get_current_user(
    x_telegram_init_data: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:

    data = validate_init_data(x_telegram_init_data)

    if not data:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram init data"
        )

    import json

    tg_user = json.loads(data["user"])

    telegram_id = str(tg_user["id"])

    result = await db.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=tg_user.get("username")
        )

        db.add(user)

        await db.commit()
        await db.refresh(user)

    return user


# =========================
# AI recognize photo
# =========================

@router.post(
    "/recognize",
    response_model=RecognizeResult
)
async def recognize(
    photo: UploadFile = File(...)
):

    image_bytes = await photo.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty photo"
        )

    result = await recognize_car(
        image_bytes,
        photo.content_type or "image/jpeg"
    )

    return result


# =========================
# Save car + real photo
# =========================

@router.post(
    "",
    response_model=CarOut
)
async def create_car(
    brand: str = Form(...),
    model: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
    ai_confidence: Optional[float] = Form(None),
    confirmed_by_user: bool = Form(True),
    location: Optional[str] = Form(None),

    photo: UploadFile = File(...),

    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    image_bytes = await photo.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty photo"
        )

    # Проверяем тип файла
    content_type = photo.content_type or ""

    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )

    # Уникальное имя
    extension = ".jpg"

    if "png" in content_type:
        extension = ".png"
    elif "webp" in content_type:
        extension = ".webp"
    elif "jpeg" in content_type:
        extension = ".jpg"

    filename = f"{uuid.uuid4().hex}{extension}"

    file_path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    # Сохраняем фотографию
    with open(file_path, "wb") as f:
        f.write(image_bytes)

    # Создаём автомобиль
    db_car = Car(
        owner_id=user.id,
        photo_path=file_path,
        photo_file_id=None,

        brand=brand,
        model=model,
        year=year,

        ai_confidence=ai_confidence,
        confirmed_by_user=confirmed_by_user,
        location=location,
    )

    db.add(db_car)

    await db.commit()
    await db.refresh(db_car)

    return db_car


# =========================
# Get user cars
# =========================

@router.get(
    "",
    response_model=list[CarOut]
)
async def list_cars(
    brand: Optional[str] = None,
    model: Optional[str] = None,

    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    query = select(Car).where(
        Car.owner_id == user.id
    )

    if brand:
        query = query.where(
            Car.brand.ilike(f"%{brand}%")
        )

    if model:
        query = query.where(
            Car.model.ilike(f"%{model}%")
        )

    query = query.order_by(
        Car.created_at.desc()
    )

    result = await db.execute(query)

    return result.scalars().all()


# =========================
# Get car photo
# =========================

@router.get("/{car_id}/photo")
async def get_car_photo(
    car_id: int,

    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Car).where(
            Car.id == car_id,
            Car.owner_id == user.id
        )
    )

    car = result.scalar_one_or_none()

    if not car:
        raise HTTPException(
            status_code=404,
            detail="Car not found"
        )

    if not car.photo_path:
        raise HTTPException(
            status_code=404,
            detail="Photo not found"
        )

    if not os.path.exists(car.photo_path):
        raise HTTPException(
            status_code=404,
            detail="Photo file does not exist"
        )

    return FileResponse(
        car.photo_path
    )


# =========================
# Delete car
# =========================

@router.delete("/{car_id}")
async def delete_car(
    car_id: int,

    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Car).where(
            Car.id == car_id,
            Car.owner_id == user.id
        )
    )

    car = result.scalar_one_or_none()

    if not car:
        raise HTTPException(
            status_code=404,
            detail="Car not found"
        )

    # Удаляем фотографию
    if car.photo_path and os.path.exists(car.photo_path):
        os.remove(car.photo_path)

    await db.delete(car)

    await db.commit()

    return {
        "ok": True
    }
