"""
utils/otp.py
Управління одноразовими кодами (OTP) для автентифікації за номером телефону.
Коди зберігаються в Redis із часом спливання TTL.
"""

import logging
import random
import string

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Префікс ключа для OTP у Redis
_OTP_PREFIX = "otp:"
# Префікс ключа для лічильника спроб (захист від брутфорсу)
_ATTEMPTS_PREFIX = "otp_attempts:"

# Константи
OTP_LENGTH = 6
OTP_TTL_SECONDS = 300       # 5 хвилин
MAX_ATTEMPTS = 5             # максимум спроб введення OTP
COOLDOWN_TTL_SECONDS = 900  # 15 хвилин блокування після перевищення спроб


def _otp_key(phone: str) -> str:
    return f"{_OTP_PREFIX}{phone}"


def _attempts_key(phone: str) -> str:
    return f"{_ATTEMPTS_PREFIX}{phone}"


def generate_otp() -> str:
    """Генерує 6-значний числовий OTP."""
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


async def store_otp(redis: Redis, phone: str, otp: str) -> None:
    """Зберігає OTP у Redis із TTL."""
    await redis.setex(_otp_key(phone), OTP_TTL_SECONDS, otp)
    # Скидаємо лічильник спроб при виданні нового коду
    await redis.delete(_attempts_key(phone))
    logger.info("OTP збережено для %s (TTL=%ds)", phone, OTP_TTL_SECONDS)


async def verify_otp(redis: Redis, phone: str, otp: str) -> bool:
    """
    Перевіряє OTP.

    Returns:
        True — код вірний і видалений (одноразовий).
        False — код неправильний або протермінований.

    Raises:
        TooManyAttemptsError: якщо перевищено ліміт спроб.
    """
    attempts_key = _attempts_key(phone)
    attempts = await redis.get(attempts_key)
    if attempts and int(attempts) >= MAX_ATTEMPTS:
        raise TooManyAttemptsError(phone)

    stored = await redis.get(_otp_key(phone))
    if stored is None:
        return False  # код протермінований або не існує

    if stored.decode() == otp:
        # Код вірний — видаляємо, щоб не можна було використати повторно
        await redis.delete(_otp_key(phone))
        await redis.delete(attempts_key)
        return True

    # Невірний код — збільшуємо лічильник спроб
    new_attempts = await redis.incr(attempts_key)
    if new_attempts == 1:
        # Встановлюємо TTL для лічильника при першій невдачі
        await redis.expire(attempts_key, COOLDOWN_TTL_SECONDS)
    logger.warning("Невірний OTP для %s (спроба %d/%d)", phone, new_attempts, MAX_ATTEMPTS)
    return False


async def otp_exists(redis: Redis, phone: str) -> bool:
    """Перевіряє чи існує активний OTP для даного номера."""
    return bool(await redis.exists(_otp_key(phone)))


class TooManyAttemptsError(Exception):
    """Перевищено кількість спроб введення OTP."""

    def __init__(self, phone: str):
        self.phone = phone
        super().__init__(f"Перевищено кількість спроб для {phone}")
