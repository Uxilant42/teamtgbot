"""
Обработчики команд управления командами.
/createteam, /team, /invite, /join, /leave
"""

import logging
import secrets
from telegram import Update
from telegram.ext import ContextTypes

from database import Database
from utils.formatters import format_team_info
from utils.validators import check_member_limit, format_limit_message
from utils.notifications import notify_new_member

logger = logging.getLogger(__name__)


# Обработчик команды /createteam — создание новой команды
async def createteam_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создание новой команды (workspace)."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Проверяем что передано название
    if not context.args:
        await update.message.reply_text(
            "📝 Укажите название команды.\n"
            "Пример: <code>/createteam Моя команда</code>",
            parse_mode="HTML",
        )
        return

    team_name = " ".join(context.args)

    # Проверяем длину названия
    if len(team_name) > 100:
        await update.message.reply_text("❌ Название команды слишком длинное (макс. 100 символов).")
        return

    # Генерируем уникальный инвайт-код
    invite_code = secrets.token_urlsafe(8)

    # Создаём команду в БД
    team_id = db.create_team(team_name, user.id, invite_code)
    # Проверяем результат
    if not team_id:
        await update.message.reply_text("❌ Ошибка создания команды. Попробуйте позже.")
        return

    msg = (
        f"✅ <b>Команда создана!</b>\n\n"
        f"👥 Название: <b>{team_name}</b>\n"
        f"🔑 ID команды: <code>{team_id}</code>\n"
        f"🔗 Инвайт-код: <code>{invite_code}</code>\n\n"
        f"Поделитесь кодом с участниками.\n"
        f"Они могут присоединиться командой:\n"
        f"<code>/join {invite_code}</code>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    logger.info("Команда '%s' (ID=%s) создана пользователем %s", team_name, team_id, user.id)


# Обработчик команды /team — информация о команде
async def team_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ информации о текущей команде и участниках."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Получаем активную команду пользователя
    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text(
            "❌ Вы не состоите ни в одной команде.\n\n"
            "Создайте команду: /createteam [название]\n"
            "Или присоединитесь: /join [код]",
            parse_mode="HTML",
        )
        return

    # Получаем участников команды
    members = db.get_team_members(team["team_id"])
    owner = db.get_user(team["owner_id"])
    owner_name = owner["first_name"] if owner else "—"

    msg = format_team_info(dict(team), [dict(m) for m in members], owner_name)
    await update.message.reply_text(msg, parse_mode="HTML")


# Обработчик команды /invite — генерация инвайт-кода
async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ инвайт-кода для приглашения в команду."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Получаем активную команду
    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text(
            "❌ Вы не состоите в команде.", parse_mode="HTML"
        )
        return

    # Проверяем права (только owner и admin)
    role = db.get_member_role(team["team_id"], user.id)
    if role not in ("owner", "admin"):
        await update.message.reply_text("❌ Только владелец и админы могут приглашать участников.")
        return

    msg = (
        f"🔗 <b>Инвайт-код команды «{team['name']}»</b>\n\n"
        f"Код: <code>{team['invite_code']}</code>\n\n"
        f"Отправьте этот код коллегам.\n"
        f"Для присоединения: <code>/join {team['invite_code']}</code>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


# Обработчик команды /join — присоединение к команде
async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Присоединение к команде по инвайт-коду."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Проверяем что передан инвайт-код
    if not context.args:
        await update.message.reply_text(
            "📝 Укажите инвайт-код.\n"
            "Пример: <code>/join abc123</code>",
            parse_mode="HTML",
        )
        return

    invite_code = context.args[0]

    # Ищем команду по инвайт-коду
    team = db.get_team_by_invite(invite_code)
    if not team:
        await update.message.reply_text("❌ Команда с таким кодом не найдена.")
        return

    # Проверяем лимит участников
    limit_check = check_member_limit(db, team["team_id"])
    if not limit_check["allowed"]:
        await update.message.reply_text(
            format_limit_message(limit_check, "участника"), parse_mode="HTML"
        )
        return

    # Добавляем пользователя в команду
    success = db.add_team_member(team["team_id"], user.id)
    if not success:
        await update.message.reply_text("ℹ️ Вы уже состоите в этой команде.")
        return

    await update.message.reply_text(
        f"✅ Вы присоединились к команде «<b>{team['name']}</b>»!\n\n"
        f"Используйте /menu для начала работы.",
        parse_mode="HTML",
    )

    # Уведомляем остальных участников
    members = db.get_team_members(team["team_id"])
    member_ids = [m["user_id"] for m in members if m["user_id"] != user.id]
    member_name = user.first_name or user.username or str(user.id)
    await notify_new_member(context.bot, member_ids, member_name, team["name"])

    logger.info("Пользователь %s присоединился к команде %s", user.id, team["team_id"])


# Обработчик команды /leave — выход из команды
async def leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выход пользователя из текущей команды."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Получаем активную команду
    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    # Проверяем что пользователь не владелец
    if team["owner_id"] == user.id:
        await update.message.reply_text(
            "❌ Владелец не может покинуть команду.\n"
            "Передайте права или удалите команду."
        )
        return

    # Удаляем из команды
    db.remove_team_member(team["team_id"], user.id)
    await update.message.reply_text(
        f"👋 Вы покинули команду «<b>{team['name']}</b>».",
        parse_mode="HTML",
    )
    logger.info("Пользователь %s покинул команду %s", user.id, team["team_id"])
