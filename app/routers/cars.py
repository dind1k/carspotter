from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from fastapi.responses import Response

from app.services.telegram_files import download_telegram_photo
from app.database import get_db
from app.models import Car, User
from app.schemas import CarCreate, CarOut, RecognizeResult
from app.services.recognition import recognize_car
from app.services.telegram_auth import validate_init_data


router = APIRouter(
    prefix="/api/cars",
    tags=["cars"]
)


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
    telegram_id = tg_user["id"]

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


@router.post(
    "/recognize",
    response_model=RecognizeResult
)
async def recognize(
    photo: UploadFile = File(...)
):
    """
    Шаг 1:
    Пользователь отправляет фото.
    ИИ определяет машину.
    """

    image_bytes = await photo.read()

    return await recognize_car(
        image_bytes,
        photo.content_type or "image/jpeg"
    )


@router.post(
    "",
    response_model=CarOut
)
async def create_car(
    car: CarCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Шаг 2:
    Сохраняем подтвержденную машину.
    """

    db_car = Car(
        owner_id=user.id,
        **car.model_dump()
    )

    db.add(db_car)

    await db.commit()
    await db.refresh(db_car)

    return db_car


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
    """
    Получение альбома пользователя.
    """

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


@router.delete("/{car_id}")
async def delete_car(
    car_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Удаление машины из коллекции.
    """

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


@router.get("/{car_id}/photo")
async def get_car_photo(
    car_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Получение фотографии машины из Telegram.
    """

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

    photo = await download_telegram_photo(
        car.photo_file_id
    )

    return Response(
        content=photo,
        media_type="image/jpeg"
    )
@router.post("/test-save")
async def test_save_photo(
    photo_file_id: str,
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(
        select(User).limit(1)
    )

    user = user_result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id="test_user"
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)


    car = Car(
        owner_id=user.id,
        photo_file_id=photo_file_id,
        brand="BMW",
        model="M3",
        year="2020",
        ai_confidence=0.95,
        confirmed_by_user=True,
        location="Москва"
    )

    db.add(car)

    await db.commit()
    await db.refresh(car)

    return car
    @router.post("/test-save")
async def test_save_photo(
    photo_file_id: str,
    db: AsyncSession = Depends(get_db),
):

    user_result = await db.execute(
        select(User).limit(1)
    )

    user = user_result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id="test_user",
            username="test"
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

    car = Car(
        owner_id=user.id,
        photo_file_id=photo_file_id,
        brand="BMW",
        model="M3",
        year="2020",
        ai_confidence=0.95,
        confirmed_by_user=True,
        location="Москва"
    )

    db.add(car)

    await db.commit()
    await db.refresh(car)

    return car
