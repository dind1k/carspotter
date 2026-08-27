from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Car

router = APIRouter(
    prefix="/api/game",
    tags=["game"]
)


@router.get("/profile/{telegram_id}")
async def get_profile(
    telegram_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    cars_result = await db.execute(
        select(func.count(Car.id)).where(
            Car.owner_id == user.id
        )
    )
    cars_count = cars_result.scalar() or 0

    brands_result = await db.execute(
        select(func.count(func.distinct(Car.brand))).where(
            Car.owner_id == user.id
        )
    )
    brands_count = brands_result.scalar() or 0

    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "level": getattr(user, "level", 1),
        "xp": getattr(user, "xp", 0),
        "cars_count": cars_count,
        "brands_count": brands_count,
    }


@router.get("/collection/{telegram_id}")
async def get_collection(
    telegram_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    cars_result = await db.execute(
        select(Car)
        .where(Car.owner_id == user.id)
        .order_by(Car.created_at.desc())
    )

    cars = cars_result.scalars().all()

    return {
        "total": len(cars),
        "cars": [
            {
                "id": car.id,
                "brand": car.brand,
                "model": car.model,
                "year": car.year,
                "photo_file_id": car.photo_file_id,
                "ai_confidence": car.ai_confidence,
                "confirmed_by_user": car.confirmed_by_user,
                "location": car.location,
                "created_at": car.created_at,
            }
            for car in cars
        ]
    }
