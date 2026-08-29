import json
import base64
import httpx

from app.config import settings
from app.schemas import RecognizeResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "openrouter/free"


PROMPT = """
Ты эксперт по автомобилям.

На фотографии изображён автомобиль.
Определи его марку, модель и примерный год выпуска.

Ответь ТОЛЬКО валидным JSON:

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

Никакого Markdown.
Никаких пояснений.
Только JSON.
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
                            "url": f"data:{mime_type};base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 300
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://happy-respect-production-5227.up.railway.app",
        "X-Title": "CarSpotter"
    }

    async with httpx.AsyncClient(timeout=60) as client:

        response = await client.post(
            OPENROUTER_URL,
            json=payload,
            headers=headers
        )

    print("OPENROUTER STATUS:", response.status_code)
    print("OPENROUTER RESPONSE:")
    print(response.text[:3000])

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter returned {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            f"Некорректный ответ OpenRouter: {data}"
        )

    print("AI RAW RESPONSE:", text)

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"ИИ вернул некорректный JSON: {text}"
        ) from error

    brand = parsed.get("brand", "unknown")
    model = parsed.get("model")
    year = parsed.get("year")
    confidence = parsed.get("confidence", 0)

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0

    confidence = max(0, min(1, confidence))

    print("=" * 60)
    print("AI SUCCESS")
    print("BRAND:", brand)
    print("MODEL:", model)
    print("YEAR:", year)
    print("CONFIDENCE:", confidence)
    print("=" * 60)

    return RecognizeResult(
        brand=str(brand or "unknown"),
        model=str(model) if model else None,
        year=str(year) if year else None,
        confidence=confidence
    )
