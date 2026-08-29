import json
import base64
import httpx

from app.config import settings
from app.schemas import RecognizeResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "qwen/qwen2.5-vl-32b-instruct:free"


PROMPT = """
Ты эксперт по распознаванию автомобилей.

Посмотри на фотографию автомобиля и определи:
1. марку
2. модель
3. примерный год выпуска

Не придумывай автомобиль, если его невозможно определить.

Ответь строго одним JSON-объектом:

{
  "brand": "BMW",
  "model": "M3",
  "year": "2021-2023",
  "confidence": 0.85
}

confidence — число от 0 до 1.

Если автомобиль определить невозможно:

{
  "brand": "unknown",
  "model": null,
  "year": null,
  "confidence": 0
}

Никакого markdown.
Никаких ``` .
Только JSON.
"""


async def recognize_car(
    image_bytes: bytes,
    mime_type: str = "image/jpeg"
) -> RecognizeResult:

    if not image_bytes:
        raise ValueError("Image is empty")

    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    image_url = f"data:{mime_type};base64,{image_b64}"

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
                            "url": image_url
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
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=90.0) as client:

        response = await client.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload
        )

    print("OPENROUTER STATUS:", response.status_code)
    print("OPENROUTER RESPONSE:", response.text[:2000])

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter error {response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(
            f"Unexpected OpenRouter response: {data}"
        ) from e

    if not text:
        raise RuntimeError("OpenRouter returned empty response")

    print("AI RAW RESPONSE:", repr(text))

    text = text.strip()

    # Убираем markdown, если модель всё-таки его добавила
    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        parsed = json.loads(text)

    except json.JSONDecodeError as e:

        print("JSON PARSE ERROR:", repr(e))
        print("BAD AI RESPONSE:", repr(text))

        raise RuntimeError(
            f"AI returned invalid JSON: {text[:1000]}"
        ) from e

    brand = parsed.get("brand") or "unknown"
    model = parsed.get("model")
    year = parsed.get("year")

    try:
        confidence = float(
            parsed.get("confidence", 0)
        )
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(
        0.0,
        min(1.0, confidence)
    )

    return RecognizeResult(
        brand=str(brand),
        model=str(model) if model else None,
        year=str(year) if year else None,
        confidence=confidence
    )
