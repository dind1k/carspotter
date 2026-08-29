````python
import json
import base64
import httpx

from app.config import settings
from app.schemas import RecognizeResult


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# =========================================================
# FREE VISION MODELS
# =========================================================

MODELS = [
    "qwen/qwen2.5-vl-72b-instruct:free",
    "qwen/qwen3-vl-235b-a22b-thinking:free",
    "google/gemma-3-27b-it:free",
]


# =========================================================
# PROMPT
# =========================================================

PROMPT = """
Ты эксперт по автомобилям.

На фотографии изображён автомобиль.

Определи:

1. марку;
2. модель;
3. примерный год выпуска.

Будь максимально внимателен к:
- форме кузова;
- фарам;
- решётке радиатора;
- эмблеме;
- дискам;
- фонарям;
- характерным элементам конкретной модели.

Если точную модель определить невозможно, укажи наиболее вероятную.

Если видишь только марку, model можешь оставить null.

Если на фотографии вообще нет автомобиля:
brand = "unknown"
model = null
year = null
confidence = 0

Ответь СТРОГО валидным JSON.

Формат:

{
  "brand": "BMW",
  "model": "M3",
  "year": "2018-2020",
  "confidence": 0.87
}

confidence — число от 0 до 1.

Никакого Markdown.
Никаких пояснений.
Только JSON.
"""


# =========================================================
# JSON CLEANER
# =========================================================

def clean_json(text: str) -> str:
    """
    Удаляет возможные ```json ... ``` вокруг ответа.
    """

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


# =========================================================
# RECOGNITION
# =========================================================

async def recognize_car(
    image_bytes: bytes,
    mime_type: str = "image/jpeg"
) -> RecognizeResult:

    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY не настроен"
        )

    if not image_bytes:
        raise RuntimeError(
            "Получено пустое изображение"
        )

    image_b64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    image_url = (
        f"data:{mime_type};base64,{image_b64}"
    )

    headers = {
        "Authorization":
            f"Bearer {settings.OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://happy-respect-production-5227.up.railway.app",

        "X-Title":
            "CarSpotter",
    }


    last_error = None


    # =====================================================
    # TRY MODELS ONE BY ONE
    # =====================================================

    async with httpx.AsyncClient(
        timeout=60
    ) as client:

        for model in MODELS:

            print("=" * 60)
            print("AI RECOGNITION")
            print("MODEL:", model)
            print("IMAGE SIZE:", len(image_bytes))
            print("MIME TYPE:", mime_type)
            print("=" * 60)


            payload = {

                "model": model,

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

                "max_tokens": 300,
            }


            try:

                response = await client.post(
                    OPENROUTER_URL,
                    json=payload,
                    headers=headers
                )


                print(
                    "OPENROUTER STATUS:",
                    response.status_code
                )


                # =========================================
                # MODEL UNAVAILABLE
                # =========================================

                if response.status_code in (
                    404,
                    429,
                    500,
                    502,
                    503,
                    504
                ):

                    print(
                        "MODEL UNAVAILABLE:",
                        model
                    )

                    print(
                        response.text[:1000]
                    )

                    last_error = RuntimeError(
                        f"OpenRouter {response.status_code}"
                    )

                    continue


                # =========================================
                # OTHER HTTP ERROR
                # =========================================

                response.raise_for_status()


                data = response.json()


                # =========================================
                # EXTRACT TEXT
                # =========================================

                try:

                    text = (
                        data["choices"][0]
                        ["message"]["content"]
                    )

                except (
                    KeyError,
                    IndexError,
                    TypeError
                ):

                    raise RuntimeError(
                        f"Некорректный ответ OpenRouter: {data}"
                    )


                if not isinstance(text, str):
                    raise RuntimeError(
                        "OpenRouter вернул ответ не строкой"
                    )


                print(
                    "AI RAW RESPONSE:",
                    text[:1000]
                )


                # =========================================
                # CLEAN JSON
                # =========================================

                text = clean_json(text)


                # =========================================
                # PARSE JSON
                # =========================================

                try:

                    parsed = json.loads(text)

                except json.JSONDecodeError as error:

                    print(
                        "JSON PARSE ERROR:",
                        error
                    )

                    last_error = RuntimeError(
                        "ИИ вернул некорректный JSON"
                    )

                    continue


                # =========================================
                # NORMALIZE
                # =========================================

                brand = parsed.get(
                    "brand",
                    "unknown"
                )

                model_name = parsed.get(
                    "model"
                )

                year = parsed.get(
                    "year"
                )

                confidence = parsed.get(
                    "confidence",
                    0
                )


                try:

                    confidence = float(
                        confidence
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    confidence = 0


                # Защита confidence

                confidence = max(
                    0,
                    min(
                        1,
                        confidence
                    )
                )


                # =========================================
                # SUCCESS
                # =========================================

                print("=" * 60)
                print("AI SUCCESS")
                print("BRAND:", brand)
                print("MODEL:", model_name)
                print("YEAR:", year)
                print(
                    "CONFIDENCE:",
                    confidence
                )
                print("=" * 60)


                return RecognizeResult(

                    brand=str(
                        brand or "unknown"
                    ),

                    model=(
                        str(model_name)
                        if model_name
                        else None
                    ),

                    year=(
                        str(year)
                        if year
                        else None
                    ),

                    confidence=confidence

                )


            except httpx.HTTPError as error:

                print(
                    "HTTP ERROR:",
                    repr(error)
                )

                last_error = error

                continue


            except Exception as error:

                print(
                    "RECOGNITION ERROR:",
                    repr(error)
                )

                last_error = error

                continue


    # =====================================================
    # ALL MODELS FAILED
    # =====================================================

    raise RuntimeError(
        "Все бесплатные модели OpenRouter "
        "временно недоступны. "
        f"Последняя ошибка: {last_error}"
    )
````
