import hashlib
import hmac
from urllib.parse import parse_qsl
from app.config import settings


def validate_init_data(init_data: str) -> dict | None:
    """
    Проверяет подпись initData, которую присылает Telegram Web App.
    Возвращает распарсенные данные пользователя, если подпись верна, иначе None.
    Документация: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(
        key=b"WebAppData", msg=settings.BOT_TOKEN.encode(), digestmod=hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        key=secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    return parsed
