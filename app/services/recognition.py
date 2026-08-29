import json
import base64
import httpx

from app.config import settings
from app.schemas import RecognizeResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "qwen/qwen2.5-vl-32b-instruct:free"


PROMPT = """Ты эксперт по автомобилям.

На фотографии изображён автомобиль.
Определи:
1. марку;
2. модель;
3. примерный год выпуска.

Если точно определить год невозможно, укажи примерный диапазон.

Ответь СТРОГО валидным JSON без markdown, без ``` и без пояснений:

{
  "brand": "...",
  "model": "...",
  "year": "...",
  "confidence": 0.0
}

confidence — число от 0 до 1.

Если на фотографии нет автомобиля или определить его невозможно:

{
  "brand": "unknown",
  "model": null,
  "year": null,
  "confidence": 0
}
"""


async def recognize_car(
    image_bytes: bytes,
    mime_type: str = "image/jpeg"
) -> RecognizeResult:

    print("========================================")
    print("AI RECOGNITION START")
    print("MODEL:", MODEL)
    print("IMAGE SIZE:", len(image_bytes))
    print("MIME TYPE:", mime_type)
    print("API KEY EXISTS:", bool(settings.OPENROUTER_API_KEY))
    print("========================================")


    if not image_bytes:
        raise ValueError("Image is empty")


    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured"
        )


    image_b64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")


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
                                f"data:{mime_type};"
                                f"base64,{image_b64}"
                            )
                        }
                    }
                ]
            }
        ]
    }


    headers = {
        "Authorization":
            f"Bearer {settings.OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://happy-respect-production-5227.up.railway.app",

        "X-Title":
            "CarSpotter"
    }


    try:

        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:

            response = await client.post(
                OPENROUTER_URL,
                json=payload,
                headers=headers
            )


    except Exception as e:

        print("========================================")
        print("OPENROUTER CONNECTION ERROR")
        print(repr(e))
        print("========================================")

        raise


    print("========================================")
    print("OPENROUTER STATUS:", response.status_code)
    print("OPENROUTER RESPONSE:")
    print(response.text)
    print("========================================")


    if response.status_code != 200:

        raise RuntimeError(
            f"OpenRouter returned "
            f"{response.status_code}: "
            f"{response.text}"
        )


    try:

        data = response.json()

    except Exception as e:

        print(
            "FAILED TO PARSE OPENROUTER JSON:",
            repr(e)
        )

        raise RuntimeError(
            "OpenRouter returned invalid JSON"
        )


    try:

        text = data["choices"][0]["message"]["content"]

    except Exception:

        print(
            "UNEXPECTED OPENROUTER STRUCTURE:",
            data
        )

        raise RuntimeError(
            "Unexpected OpenRouter response"
        )


    print("AI RAW TEXT:")
    print(text)


    if isinstance(text, list):

        parts = []

        for item in text:

            if isinstance(item, dict):

                if item.get("type") == "text":

                    parts.append(
                        item.get("text", "")
                    )

        text = "".join(parts)


    text = str(text).strip()


    if text.startswith("```json"):

        text = text[7:]

    elif text.startswith("```"):

        text = text[3:]


    if text.endswith("```"):

        text = text[:-3]


    text = text.strip()


    print("AI CLEAN JSON:")
    print(text)


    try:

        parsed = json.loads(text)

    except Exception as e:

        print("JSON PARSE ERROR:", repr(e))

        raise RuntimeError(
            f"AI returned invalid JSON: {text}"
        )


    return RecognizeResult(

        brand=parsed.get(
            "brand",
            "unknown"
        ),

        model=parsed.get(
            "model"
        ),

        year=parsed.get(
            "year"
        ),

        confidence=float(
            parsed.get(
                "confidence",
                0
            )
        )
    )
