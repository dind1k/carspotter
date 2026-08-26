import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

from app.config import settings

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📸 Открыть альбом машин",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "Привет! Это CarSpotter 🚗\n\n"
        "Фотографируй интересные машины на улице — они будут собираться "
        "в твоём личном альбоме, отсортированные по маркам и моделям.\n\n"
        "Нажми кнопку ниже, чтобы открыть альбом:",
        reply_markup=keyboard,
    )


@dp.message(F.photo)
async def handle_photo(message: Message):
    # Фото просто остаётся на серверах Telegram — берём file_id,
    # а само распознавание и сохранение в БД делает фронт мини-эппа
    # через эндпоинт /api/cars/recognize, вызывая Telegram WebApp API.
    file_id = message.photo[-1].file_id
    await message.answer(
        f"Фото получено! Открой мини-приложение, чтобы добавить машину в альбом.\n"
        f"(file_id: {file_id})"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
