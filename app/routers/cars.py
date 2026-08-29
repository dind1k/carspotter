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

from fastapi.responses import Response

from typing import Optional
import json
import httpx

from app.database import get_db
from app.models import Car, User
from app.schemas import CarOut, RecognizeResult

from app.services.recognition import recognize_car
from app.services.telegram_auth import validate_init_data
from app.services.telegram_files import download_telegram_photo

from app.config import settings


router = APIRouter(
    prefix="/api/cars",
    tags=["cars"]
)


# =========================================================
# TELEGRAM USER AUTH
# =========================================================

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

    try:
        tg_user = json.loads(data["user"])
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram user data"
        )

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


# =========================================================
# AI RECOGNITION
# =========================================================

@router.post(
    "/recognize",
    response_model=RecognizeResult
)
async def recognize(
    photo: UploadFile = File(...)
):

    if not photo.content_type:
        raise HTTPException(
            status_code=400,
            detail="Photo content type is missing"
        )

    if not photo.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )

    image_bytes = await photo.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty image"
        )

    try:

        result = await recognize_car(
            image_bytes,
            photo.content_type
        )

        return result

    except Exception as e:

        print(
            "RECOGNITION ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=422,
            detail="Car recognition failed"
        )


# =========================================================
# SAVE CAR + REAL PHOTO
# =========================================================

@router.post(
    "",
    response_model=CarOut
)
async def create_car(
    photo: UploadFile = File(...),

    brand: str = Form(...),
    model: Optional[str] = Form(None),
    year: Optional[str] = Form(None),

    ai_confidence: Optional[float] = Form(None),

    confirmed_by_user: bool = Form(True),

    location: Optional[str] = Form(None),

    user: User = Depends(get_current_user),

    db: AsyncSession = Depends(get_db),
):

    if not photo.content_type:
        raise HTTPException(
            status_code=400,
            detail="Photo content type is missing"
        )

    if not photo.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )

    image_bytes = await photo.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty image"
        )

    # -----------------------------------------------------
    # Отправляем настоящую фотографию в Telegram
    # -----------------------------------------------------

    telegram_api_url = (
        f"https://api.telegram.org/bot"
        f"{settings.BOT_TOKEN}/sendPhoto"
    )

    try:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(
                telegram_api_url,

                data={
                    "chat_id": user.telegram_id,
                },

                files={
                    "photo": (
                        photo.filename or "car.jpg",
                        image_bytes,
                        photo.content_type,
                    )
                }
            )

        if response.status_code != 200:

            print(
                "TELEGRAM SEND PHOTO ERROR:",
                response.text
            )

            raise HTTPException(
                status_code=500,
                detail="Failed to save photo"
            )

        telegram_result = response.json()

        if not telegram_result.get("ok"):

            print(
                "TELEGRAM API ERROR:",
                telegram_result
            )

            raise HTTPException(
                status_code=500,
                detail="Telegram failed to save photo"
            )

        message = telegram_result["result"]

        photos = message.get("photo", [])

        if not photos:

            raise HTTPException(
                status_code=500,
                detail="Telegram returned no photo"
            )

        # Берём самое большое доступное изображение
        photo_file_id = photos[-1]["file_id"]

    except HTTPException:
        raise

    except Exception as e:

        print(
            "PHOTO SAVE ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to upload photo"
        )


    # -----------------------------------------------------
    # Сохраняем автомобиль
    # -----------------------------------------------------

    db_car = Car(
        owner_id=user.id,

        photo_file_id=photo_file_id,

        brand=brand.strip(),

        model=(
            model.strip()
            if model
            else None
        ),

        year=(
            year.strip()
            if year
            else None
        ),

        ai_confidence=ai_confidence,

        confirmed_by_user=confirmed_by_user,

        location=(
            location.strip()
            if location
            else None
        ),
    )

    db.add(db_car)

    await db.commit()

    await db.refresh(db_car)

    return db_car


# =========================================================
# GET USER CARS
# =========================================================

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
            Car.brand.ilike(
                f"%{brand}%"
            )
        )

    if model:

        query = query.where(
            Car.model.ilike(
                f"%{model}%"
            )
        )

    query = query.order_by(
        Car.created_at.desc()
    )

    result = await db.execute(query)

    return result.scalars().all()


# =========================================================
# GET CAR PHOTO
# =========================================================

@router.get(
    "/{car_id}/photo"
)
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

    if not car.photo_file_id:

        raise HTTPException(
            status_code=404,
            detail="Photo not found"
        )

    try:

        photo = await download_telegram_photo(
            car.photo_file_id
        )

    except Exception as e:

        print(
            "PHOTO DOWNLOAD ERROR:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to load photo"
        )

    return Response(
        content=photo,
        media_type="image/jpeg"
    )


# =========================================================
# DELETE CAR
# =========================================================

@router.delete(
    "/{car_id}"
)
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

    await db.delete(car)

    await db.commit()

    return {
        "ok": True
    }
