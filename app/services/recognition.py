````python
import json
import base64
import httpx

from app.config import settings
from app.schemas import RecognizeResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Бесплатный роутер OpenRouter.
# Он сам выбирает доступную бесплатную vision-модель.
MODEL = "openrouter/free"


PROMPT = """
Ты эксперт по автомобилям.

На фотографии изображён автомобиль.
Определи его марку, модель и примерный год выпуска.

Ответь ТОЛЬКО валидным JSON без Markdown и пояснений:

{
  "brand": "BMW",
  "model": "M3",
  "year": "2018-2020",
  "confidence": 0.87
}

confidence — число от 0 до 1.

Если автомобиль определить невозможно:

{
  "brand": "unknown",
  "model": null,
  "year": null,
  "confidence": 0
}

ВАЖНО:
- Не пиши рассуждения.
- Не пиши Thinking Process.
- Не используй Markdown.
- Ответ должен содержать только JSON.
"""


async def recognize_car(
    image_bytes: bytes,
    mime_type: str = "image/jpeg"
) -> RecognizeResult:

    print("=" * 60)
    print("AI RECOGNITION START")
    print("MODEL:", MODEL)
    print("IMAGE SIZE:", len(image_bytes))
    print("MIME TYPE:", mime_type)
    print("API KEY EXISTS:", bool(settings.OPENROUTER_API_KEY))
    print("=" * 60)

    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY не установлен")

    if not image_bytes:
        raise RuntimeError("Получено пустое изображение")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": MODEL,

        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{mime_type};base64,"
                                f"{image_b64}"
                            )
                        }
                    }
                ]
            }
        ],

        "temperature": 0.1,

        # Немного увеличиваем лимит,
        # чтобы бесплатная модель успевала закончить JSON.
        "max_tokens": 500
    }

    headers = {
        "Authorization": (
            f"Bearer {settings.OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",

        "HTTP-Referer": (
            "https://happy-respect-production-5227.up.railway.app"
        ),

        "X-Title": "CarSpotter"
    }

    try:

        async with httpx.AsyncClient(
            timeout=90
        ) as client:

            response = await client.post(
                OPENROUTER_URL,
                json=payload,
                headers=headers
            )

    except httpx.TimeoutException as error:

        raise RuntimeError(
            "OpenRouter не ответил вовремя"
        ) from error

    except httpx.HTTPError as error:

        raise RuntimeError(
            f"Ошибка соединения с OpenRouter: {error}"
        ) from error

    print("OPENROUTER STATUS:", response.status_code)
    print("OPENROUTER RESPONSE:")
    print(response.text[:5000])

    if response.status_code != 200:

        raise RuntimeError(
            f"OpenRouter returned {response.status_code}: "
            f"{response.text}"
        )

    try:
        data = response.json()

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "OpenRouter вернул невалидный JSON"
        ) from error

    # ---------------------------------------------------------
    # Получаем message
    # ---------------------------------------------------------

    try:

        choice = data["choices"][0]
        message = choice["message"]

    except (KeyError, IndexError, TypeError) as error:

        raise RuntimeError(
            f"Некорректный ответ OpenRouter: {data}"
        ) from error

    # ---------------------------------------------------------
    # Проверяем content
    # ---------------------------------------------------------

    text = message.get("content")

    print("AI RAW RESPONSE:", text)

    # Некоторые модели могут вернуть content=null,
    # особенно если закончился лимит токенов.
    if not text:

        reasoning = message.get("reasoning")

        print(
            "AI CONTENT IS EMPTY"
        )

        print(
            "AI REASONING:",
            reasoning[:3000] if reasoning else None
        )

        finish_reason = choice.get("finish_reason")

        raise RuntimeError(
            "ИИ не вернул результат. "
            f"finish_reason={finish_reason}"
        )

    text = str(text).strip()

    # ---------------------------------------------------------
    # Удаляем Markdown, если модель его всё-таки добавила
    # ---------------------------------------------------------

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # ---------------------------------------------------------
    # Иногда модель пишет что-то вокруг JSON.
    #
    # Например:
    #
    # Вот результат:
    # {"brand":"BMW",...}
    #
    # Попробуем найти JSON внутри ответа.
    # ---------------------------------------------------------

    if not text.startswith("{"):

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:

            text = text[start:end + 1]

    print("AI CLEAN RESPONSE:", text)

    # ---------------------------------------------------------
    # Парсим JSON
    # ---------------------------------------------------------

    try:

        parsed = json.loads(text)

    except json.JSONDecodeError as error:

        raise RuntimeError(
            f"ИИ вернул некорректный JSON: {text}"
        ) from error

    if not isinstance(parsed, dict):

        raise RuntimeError(
            f"ИИ вернул JSON неправильного типа: {parsed}"
        )

    # ---------------------------------------------------------
    # Получаем поля
    # ---------------------------------------------------------

    brand = parsed.get("brand", "unknown")
    model = parsed.get("model")
    year = parsed.get("year")
    confidence = parsed.get("confidence", 0)

    # ---------------------------------------------------------
    # Нормализуем confidence
    # ---------------------------------------------------------

    try:

        confidence = float(confidence)

    except (TypeError, ValueError):

        confidence = 0

    confidence = max(
        0,
        min(1, confidence)
    )

    # ---------------------------------------------------------
    # Нормализуем brand
    # ---------------------------------------------------------

    if not brand:

        brand = "unknown"

    brand = str(brand).strip()

    # ---------------------------------------------------------
    # Финальный результат
    # ---------------------------------------------------------

    print("=" * 60)
    print("AI SUCCESS")
    print("BRAND:", brand)
    print("MODEL:", model)
    print("YEAR:", year)
    print("CONFIDENCE:", confidence)
    print("=" * 60)

    return RecognizeResult(
        brand=brand,

        model=(
            str(model).strip()
            if model
            else None
        ),

        year=(
            str(year).strip()
            if year
            else None
        ),

        confidence=confidence
    )
````
