# CarSpotter — Telegram Mini App

Фотографируешь машину на улице → ИИ определяет марку/модель → она добавляется
в твой личный альбом с фильтрацией по маркам и моделям.

## Стек (полностью бесплатный для старта)

- **Backend**: FastAPI (Python)
- **Бот**: aiogram 3
- **БД**: Postgres (Supabase / Neon — бесплатный тариф)
- **Распознавание фото**: Google Gemini API (бесплатный лимит)
- **Хранение фото**: file_id из Telegram (фото не скачиваются, хранятся у Telegram)
- **Хостинг backend**: Railway / Render / Fly.io (бесплатный тариф)
- **Фронт мини-эппа**: отдельно (Vercel/Netlify) — см. ниже

## Структура проекта

```
carspotter/
├── app/
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # переменные окружения
│   ├── database.py          # подключение к БД
│   ├── models.py            # таблицы User, Car
│   ├── schemas.py           # Pydantic-схемы
│   ├── routers/
│   │   └── cars.py          # /api/cars — recognize, create, list, delete
│   └── services/
│       ├── recognition.py   # вызов Gemini API
│       └── telegram_auth.py # проверка подписи initData
├── bot/
│   └── bot.py                # Telegram-бот с кнопкой WebApp
├── requirements.txt
└── .env.example
```

## Как запустить локально

1. Установи зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Скопируй `.env.example` в `.env` и заполни:
   - `BOT_TOKEN` — получи у [@BotFather](https://t.me/BotFather)
   - `DATABASE_URL` — создай бесплатную БД на [Supabase](https://supabase.com) или [Neon](https://neon.tech)
   - `GEMINI_API_KEY` — получи на [Google AI Studio](https://aistudio.google.com/apikey)
   - `WEBAPP_URL` — заполнишь после деплоя фронта

3. Запусти backend:
   ```bash
   uvicorn app.main:app --reload
   ```

4. В отдельном терминале запусти бота:
   ```bash
   python -m bot.bot
   ```

5. В [@BotFather](https://t.me/BotFather) настрой кнопку меню (Menu Button) на URL
   твоего задеплоенного фронта — это и будет открывать мини-эпп.

## Как это работает (поток данных)

1. Юзер фоткает машину и шлёт боту, **или** сразу открывает мини-эпп и
   загружает фото через камеру/галерею (Telegram WebApp API даёт доступ к камере)
2. Фронт шлёт фото на `POST /api/cars/recognize` → получает предположение
   ИИ (марка, модель, год, confidence)
3. Фронт показывает юзеру результат с возможностью поправить вручную
4. Юзер подтверждает → фронт шлёт `POST /api/cars` с финальными данными
   и `photo_file_id` → машина сохраняется в альбом
5. `GET /api/cars?brand=...&model=...` — получить альбом с фильтром

## Что дальше (фронт мини-эппа)

Backend и бот готовы. Следующий шаг — фронтенд (React или чистый HTML/JS)
с интерфейсом альбома, загрузкой фото через Telegram WebApp SDK и вызовами
этих эндпоинтов. Могу сделать отдельным шагом.

## Ограничения бесплатного стека

- Gemini free tier: лимит запросов в день (обычно достаточно для личного проекта/MVP)
- Railway/Render free tier: сервис может "засыпать" при простое — первый запрос
  после паузы будет медленным
- Supabase free tier: 500MB — с учётом того, что фото не хранятся в БД (только
  file_id), места хватит очень надолго
