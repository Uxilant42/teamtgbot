"""
Модуль валидации данных и проверки лимитов подписки.
"""

import logging
from datetime import datetime
from typing import Any

from config import SUBSCRIPTION_LIMITS

logger = logging.getLogger(__name__)


# Проверка лимита задач для команды
def check_task_limit(db, team_id: int) -> dict[str, Any]:
    """
    Проверяет, можно ли создать ещё одну задачу в команде.
    Возвращает словарь с результатом проверки.
    """
    team = db.get_team(team_id)
    # Проверяем что команда существует
    if not team:
        return {"allowed": False, "error": "Команда не найдена"}

    plan = team["subscription_type"]
    limits = SUBSCRIPTION_LIMITS.get(plan, SUBSCRIPTION_LIMITS["free"])
    current = db.get_active_tasks_count(team_id)

    return {
        "allowed": current < limits["max_tasks"],
        "current": current,
        "limit": limits["max_tasks"],
        "plan": plan,
    }


# Проверка лимита участников для команды
def check_member_limit(db, team_id: int) -> dict[str, Any]:
    """
    Проверяет, можно ли добавить ещё одного участника в команду.
    Возвращает словарь с результатом проверки.
    """
    team = db.get_team(team_id)
    # Проверяем что команда существует
    if not team:
        return {"allowed": False, "error": "Команда не найдена"}

    plan = team["subscription_type"]
    limits = SUBSCRIPTION_LIMITS.get(plan, SUBSCRIPTION_LIMITS["free"])
    current = db.get_team_member_count(team_id)

    return {
        "allowed": current < limits["max_members"],
        "current": current,
        "limit": limits["max_members"],
        "plan": plan,
    }


# Проверка доступа к функции по подписке
def check_feature_access(db, team_id: int, feature: str) -> bool:
    """
    Проверяет, доступна ли функция для текущей подписки.
    Доступные фичи: reminders, calendar_export, analytics.
    """
    team = db.get_team(team_id)
    # Проверяем что команда существует
    if not team:
        return False
    plan = team["subscription_type"]
    limits = SUBSCRIPTION_LIMITS.get(plan, SUBSCRIPTION_LIMITS["free"])
    return limits.get(feature, False)


# Валидация формата даты
def validate_deadline(text: str) -> datetime | None:
    """
    Парсит дедлайн из текста пользователя.
    Поддерживаемые форматы: ДД.ММ.ГГГГ ЧЧ:ММ или ДД.ММ.ГГГГ
    Возвращает datetime или None при ошибке парсинга.
    """
    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]
    # Пробуем разные форматы дат
    for fmt in formats:
        try:
            dt = datetime.strptime(text.strip(), fmt)
            # Проверяем что дата не в прошлом
            if dt < datetime.now():
                logger.warning("Дата в прошлом: %s", text)
                return None
            return dt
        except ValueError:
            continue
    return None


# Валидация длины текста
def validate_text_length(text: str, max_length: int) -> bool:
    """Проверяет, не превышает ли текст максимальную длину."""
    return len(text.strip()) <= max_length


# Проверка роли пользователя
def check_user_permission(
    db, team_id: int, user_id: int, required_roles: list[str]
) -> bool:
    """
    Проверяет, имеет ли пользователь нужную роль в команде.
    required_roles — список допустимых ролей.
    """
    role = db.get_member_role(team_id, user_id)
    # Проверяем что роль есть и она подходит
    if not role:
        return False
    return role in required_roles


# Форматирование сообщения об ограничениях
def format_limit_message(check_result: dict[str, Any], item: str = "задачу") -> str:
    """Формирует сообщение о превышении лимита."""
    return (
        f"⚠️ <b>Лимит достигнут!</b>\n\n"
        f"Текущий план: <b>{check_result['plan'].upper()}</b>\n"
        f"Использовано: {check_result['current']}/{check_result['limit']}\n\n"
        f"Невозможно добавить {item}.\n"
        f"Обновите подписку командой /subscribe"
    )
