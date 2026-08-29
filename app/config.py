import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        ""
    )

    OPENROUTER_API_KEY: str = os.getenv(
        "OPENROUTER_API_KEY",
        ""
    )

    WEBAPP_URL: str = os.getenv(
        "WEBAPP_URL",
        "https://your-frontend.vercel.app"
    )


settings = Settings()
