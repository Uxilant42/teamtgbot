"""
Обработчики команд статистики.
/stats, /mystats
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import Database
from utils.formatters import format_team_stats, format_user_stats
from utils.keyboards import get_back_to_menu_keyboard

logger = logging.getLogger(__name__)


# Обработчик команды /stats — статистика команды
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ статистики текущей команды."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    # Получаем и форматируем статистику
    stats = db.get_team_stats(team["team_id"])
    msg = format_team_stats(stats, team["name"])
    await update.message.reply_text(msg, parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard())


# Обработчик команды /mystats — личная статистика
async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ личной статистики пользователя."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    # Получаем и форматируем личную статистику
    stats = db.get_user_stats(user.id, team["team_id"])
    user_name = user.first_name or user.username or str(user.id)
    msg = format_user_stats(stats, user_name)
    await update.message.reply_text(msg, parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard())
