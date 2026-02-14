"""
Обработчики команд /start, /help, /menu и /cancel.
Регистрация пользователей и основная навигация.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from utils.keyboards import get_main_menu_keyboard, get_back_to_menu_keyboard
from utils.formatters import format_help_message

logger = logging.getLogger(__name__)


# Обработчик команды /start — регистрация пользователя
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Регистрация пользователя и приветственное сообщение."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Сохраняем / обновляем данные пользователя
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code or "ru",
    )

    # Проверяем, есть ли у пользователя команда
    team = db.get_user_active_team(user.id)

    welcome = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"Я — бот для управления задачами вашей команды.\n\n"
    )

    # Подсказываем что делать дальше
    if team:
        welcome += (
            f"✅ Вы состоите в команде «<b>{team['name']}</b>»\n\n"
            f"Используйте /menu для доступа ко всем функциям."
        )
    else:
        welcome += (
            "🚀 <b>Начните работу:</b>\n"
            "• /createteam — создать новую команду\n"
            "• /join [код] — присоединиться к существующей\n\n"
            "Используйте /help для просмотра всех команд."
        )

    await update.message.reply_text(
        welcome, parse_mode="HTML", reply_markup=get_main_menu_keyboard()
    )
    logger.info("Пользователь %s (%s) зарегистрирован", user.id, user.username)


# Обработчик команды /help — справка
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка справки по всем командам."""
    await update.message.reply_text(
        format_help_message(), parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard(),
    )


# Обработчик команды /menu — главное меню
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка главного меню с inline-кнопками."""
    await update.message.reply_text(
        "📋 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )


# Обработчик команды /cancel — отмена текущего действия
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего диалога (ConversationHandler)."""
    # Очищаем данные диалога
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Действие отменено.\n\nИспользуйте /menu для продолжения.",
        parse_mode="HTML",
    )
    return ConversationHandler.END


# Обработчик команды /settings — настройки
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка информации о настройках."""
    user = update.effective_user
    db: Database = context.bot_data["db"]
    user_data = db.get_user(user.id)

    tz = user_data["timezone"] if user_data else "Europe/Moscow"
    msg = (
        "⚙️ <b>Настройки</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🕐 Часовой пояс: <b>{tz}</b>\n\n"
        "Команды настроек:\n"
        "/timezone [зона] — сменить часовой пояс\n"
        "Пример: /timezone Europe/Moscow"
    )
    await update.message.reply_text(msg, parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard())


# Обработчик команды /timezone — смена часового пояса
async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Установка часового пояса пользователя."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Проверяем аргументы
    if not context.args:
        await update.message.reply_text(
            "⚙️ Укажите часовой пояс.\n"
            "Пример: /timezone Europe/Moscow\n\n"
            "Популярные зоны:\n"
            "• Europe/Moscow\n"
            "• Europe/Kiev\n"
            "• Asia/Almaty\n"
            "• UTC",
            parse_mode="HTML",
        )
        return

    tz = context.args[0]
    # Пробуем установить часовой пояс
    try:
        import pytz
        pytz.timezone(tz)
        db.set_user_timezone(user.id, tz)
        await update.message.reply_text(
            f"✅ Часовой пояс установлен: <b>{tz}</b>", parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text(
            f"❌ Неизвестный часовой пояс: {tz}\n"
            "Используйте формат: Europe/Moscow, UTC и т.д.",
            parse_mode="HTML",
        )
