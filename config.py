"""
Конфигурация Telegram-бота для управления задачами.
Загрузка переменных окружения и константы приложения.
"""

import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Путь к базе данных SQLite
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "taskbot.db")

# Часовой пояс по умолчанию
DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")

# Уровень логирования
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Режим отладки
DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ─── Лимиты подписок ───────────────────────────────────────────────

SUBSCRIPTION_LIMITS: dict = {
    "free": {
        "max_members": int(os.getenv("FREE_MEMBER_LIMIT", "3")),
        "max_tasks": int(os.getenv("FREE_TASK_LIMIT", "20")),
        "reminders": False,
        "calendar_export": False,
        "analytics": False,
    },
    "pro": {
        "max_members": int(os.getenv("PRO_MEMBER_LIMIT", "15")),
        "max_tasks": 999999,
        "reminders": True,
        "calendar_export": True,
        "analytics": True,
    },
    "enterprise": {
        "max_members": 999999,
        "max_tasks": 999999,
        "reminders": True,
        "calendar_export": True,
        "analytics": True,
    },
}

# ─── Цены подписок ─────────────────────────────────────────────────

SUBSCRIPTION_PRICES: dict = {
    "pro": "₽299/мес за команду",
    "enterprise": "По запросу",
}

# ─── Эмодзи-маппинги ──────────────────────────────────────────────

PRIORITY_EMOJI: dict[str, str] = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🔴",
}

STATUS_EMOJI: dict[str, str] = {
    "todo": "⏳",
    "in_progress": "🔄",
    "done": "✅",
    "cancelled": "❌",
}

STATUS_TEXT: dict[str, str] = {
    "todo": "К выполнению",
    "in_progress": "В процессе",
    "done": "Выполнено",
    "cancelled": "Отменено",
}

PRIORITY_TEXT: dict[str, str] = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
}

# ─── Состояния ConversationHandler ─────────────────────────────────

(
    STATE_TITLE,
    STATE_DESCRIPTION,
    STATE_ASSIGNEE,
    STATE_DEADLINE,
    STATE_PRIORITY,
    STATE_CONFIRM,
) = range(6)

# ─── Настройка логирования ─────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)
logger = logging.getLogger(__name__)
