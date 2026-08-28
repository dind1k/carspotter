from aiogram import Bot

from app.config import settings


async def download_telegram_photo(file_id: str) -> bytes:
    bot = Bot(token=settings.BOT_TOKEN)

    try:
        telegram_file = await bot.get_file(file_id)

        file = await bot.download_file(
            telegram_file.file_path
        )

        return file.read()

    finally:
        await bot.session.close()
