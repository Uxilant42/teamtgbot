"""
Модуль отправки уведомлений пользователям.
Уведомления о назначении/смене статуса/комментариях.
"""

import logging
from telegram import Bot
from config import STATUS_EMOJI, STATUS_TEXT, PRIORITY_EMOJI

logger = logging.getLogger(__name__)


# Уведомление о назначении задачи
async def notify_task_assigned(
    bot: Bot,
    assignee_id: int,
    task: dict,
    author_name: str,
) -> None:
    """Отправляет уведомление исполнителю о назначенной задаче."""
    try:
        p_emoji = PRIORITY_EMOJI.get(task.get("priority", "medium"), "⚪️")
        msg = (
            f"📬 <b>Вам назначена задача!</b>\n\n"
            f"📝 <b>#{task['task_id']}</b> — {task['title']}\n"
            f"{p_emoji} Приоритет: {task.get('priority', 'medium')}\n"
            f"✍️ Автор: {author_name}\n"
        )
        # Добавляем дедлайн, если установлен
        if task.get("deadline"):
            msg += f"📅 Дедлайн: {task['deadline']}\n"
        msg += "\nОткройте задачу: /task " + str(task["task_id"])
        await bot.send_message(chat_id=assignee_id, text=msg, parse_mode="HTML")
        logger.info("Уведомление отправлено пользователю %s", assignee_id)
    except Exception as e:
        logger.error("Ошибка отправки уведомления (назначение): %s", e)


# Уведомление автору о смене статуса задачи
async def notify_status_changed(
    bot: Bot,
    author_id: int,
    task: dict,
    new_status: str,
    changed_by: str,
) -> None:
    """Отправляет уведомление автору при смене статуса задачи."""
    try:
        s_emoji = STATUS_EMOJI.get(new_status, "⚪️")
        s_text = STATUS_TEXT.get(new_status, new_status)
        msg = (
            f"🔔 <b>Статус задачи изменён!</b>\n\n"
            f"📝 <b>#{task['task_id']}</b> — {task['title']}\n"
            f"📊 Новый статус: {s_emoji} {s_text}\n"
            f"👤 Изменил: {changed_by}\n"
        )
        await bot.send_message(chat_id=author_id, text=msg, parse_mode="HTML")
        logger.info("Уведомление о смене статуса отправлено пользователю %s", author_id)
    except Exception as e:
        logger.error("Ошибка отправки уведомления (статус): %s", e)


# Уведомление о новом комментарии
async def notify_comment_added(
    bot: Bot,
    notify_user_ids: list[int],
    task: dict,
    commenter_name: str,
    comment_text: str,
) -> None:
    """Отправляет уведомления участникам о новом комментарии."""
    msg = (
        f"💬 <b>Новый комментарий</b>\n\n"
        f"📝 Задача <b>#{task['task_id']}</b> — {task['title']}\n"
        f"👤 {commenter_name}:\n"
        f"<i>{comment_text[:200]}</i>\n"
    )
    # Проходим по получателям и отправляем каждому
    for uid in notify_user_ids:
        try:
            await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
        except Exception as e:
            logger.error("Ошибка отправки уведомления (комментарий) для %s: %s", uid, e)


# Уведомление всей команде о новом участнике
async def notify_new_member(
    bot: Bot,
    team_member_ids: list[int],
    new_member_name: str,
    team_name: str,
) -> None:
    """Уведомляет команду о новом участнике."""
    msg = (
        f"👋 <b>Новый участник!</b>\n\n"
        f"<b>{new_member_name}</b> присоединился к команде «{team_name}»"
    )
    # Проходим по участникам и отправляем каждому
    for uid in team_member_ids:
        try:
            await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
        except Exception as e:
            logger.error("Ошибка отправки уведомления (новый участник) для %s: %s", uid, e)
