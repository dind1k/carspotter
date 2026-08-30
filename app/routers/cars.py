import os
import uuid
import json
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Header,
)

from fastapi.responses import FileResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Car, User
from app.schemas import CarCreate, CarOut
from app.services.telegram_auth import validate_init_data


router = APIRouter(
    prefix="/api/cars",
    tags=["cars"],
)


# =========================
# Upload directory
# =========================

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True,
)


# =========================
# Telegram user auth
# =========================

async def get_current_user(
    x_telegram_init_data: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:

    data = validate_init_data(
        x_telegram_init_data
    )

    if not data:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram init data",
        )

    try:
        tg_user = json.loads(
            data["user"]
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid Telegram user data",
        )

    telegram_id = str(
        tg_user["id"]
    )

    result = await db.execute(
        select(User).where(
            User.telegram_id == telegram_id
        )
    )

    user = result.scalar_one_or_none()

    if not user:

        user = User(
            telegram_id=telegram_id,
            username=tg_user.get("username"),
        )

        db.add(user)

        await db.commit()

        await db.refresh(user)

    return user


# =========================
# Upload photo
# =========================

@router.post("/upload")
async def upload_photo(
    photo: UploadFile = File(...),
    user: User = Depends(get_current_user),
):

    if not photo.content_type:
        raise HTTPException(
            status_code=400,
            detail="File type is missing",
        )

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    if photo.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed",
        )

    image_bytes = await photo.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty image",
        )

    extension = allowed_types[
        photo.content_type
    ]

    filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    filepath = os.path.join(
        UPLOAD_DIR,
        filename
    )

    with open(
        filepath,
        "wb"
    ) as f:
        f.write(image_bytes)

    return {
        "photo_url": f"/api/cars/photo/{filename}"
    }

    if not photo.content_type:
        raise HTTPException(
            status_code=400,
            detail="File type is missing",
        )

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    if photo.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed",
        )

    image_bytes = await photo.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty image",
        )

    extension = allowed_types[
        photo.content_type
    ]

    filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    filepath = os.path.join(
        UPLOAD_DIR,
        filename,
    )

    with open(
        filepath,
        "wb",
    ) as f:
        f.write(
            image_bytes
        )

    return {
        "photo_url":
            f"/api/cars/photo/{filename}"
    }


# =========================
# Serve uploaded photo
# =========================

@router.get(
    "/photo/{filename}"
)
async def get_uploaded_photo(
    filename: str,
):

    filename = os.path.basename(
        filename
    )

    filepath = os.path.join(
        UPLOAD_DIR,
        filename,
    )

    if not os.path.isfile(
        filepath
    ):
        raise HTTPException(
            status_code=404,
            detail="Photo not found",
        )

    return FileResponse(
        filepath
    )


# =========================
# Save car
# =========================

@router.post(
    "",
    response_model=CarOut,
)
async def create_car(
    car: CarCreate,
    user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    db_car = Car(
        owner_id=user.id,
        **car.model_dump(),
    )

    db.add(
        db_car
    )

    await db.commit()

    await db.refresh(
        db_car
    )

    return db_car


# =========================
# Get user cars
# =========================

@router.get(
    "",
    response_model=list[CarOut],
)
async def list_cars(
    brand: Optional[str] = None,
    model: Optional[str] = None,
    user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    query = select(
        Car
    ).where(
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

    result = await db.execute(
        query
    )

    return result.scalars().all()


# =========================
# Delete car
# =========================

@router.delete(
    "/{car_id}"
)
async def delete_car(
    car_id: int,
    user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    result = await db.execute(
        select(Car).where(
            Car.id == car_id,
            Car.owner_id == user.id,
        )
    )

    car = result.scalar_one_or_none()

    if not car:
        raise HTTPException(
            status_code=404,
            detail="Car not found",
        )

    await db.delete(
        car
    )

    await db.commit()

    return {
        "ok": True
    }
