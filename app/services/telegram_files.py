import httpx

from app.config import settings


async def download_telegram_photo(
    file_id: str
) -> bytes:

    # Получаем информацию о файле
    get_file_url = (
        f"https://api.telegram.org/bot"
        f"{settings.BOT_TOKEN}/getFile"
    )

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.get(
            get_file_url,
            params={
                "file_id": file_id
            }
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):

            raise RuntimeError(
                f"Telegram getFile error: {data}"
            )

        file_path = data["result"]["file_path"]

        # Скачиваем файл
        download_url = (
            f"https://api.telegram.org/file/bot"
            f"{settings.BOT_TOKEN}/"
            f"{file_path}"
        )

        photo_response = await client.get(
            download_url
        )

        photo_response.raise_for_status()

        return photo_response.content
