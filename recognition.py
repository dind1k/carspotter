import json
import base64
import httpx
from app.config import settings
from app.schemas import RecognizeResult

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Бесплатная модель с поддержкой изображений.
# Если эта модель станет недоступна/платной — на openrouter.ai/models
# отфильтруй по "modality: image->text" и "free", возьми любую другую.
MODEL = "qwen/qwen2.5-vl-32b-instruct:free"

PROMPT = """Ты эксперт по автомобилям. На фото изображена машина.
Определи марку, модель и примерный год выпуска (диапазон, если не уверен).
Ответь СТРОГО в формате JSON без markdown и без пояснений:
{"brand": "...", "model": "...", "year": "...", "confidence": 0.0}
confidence — число от 0 до 1, насколько ты уверен в ответе.
Если на фото не машина или марку определить невозможно — brand: "unknown", confidence: 0.
"""


async def recognize_car(image_bytes: bytes, mime_type: str = "image/jpeg") -> RecognizeResult:
    image_b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                    },
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    text = data["choices"][0]["message"]["content"]
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    parsed = json.loads(text)
    return RecognizeResult(
        brand=parsed.get("brand", "unknown"),
        model=parsed.get("model"),
        year=parsed.get("year"),
        confidence=float(parsed.get("confidence", 0)),
    )
