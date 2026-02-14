"""
Точка входа Telegram-бота для управления задачами команды.
Инициализация приложения, регистрация обработчиков, запуск бота.
"""

import sys
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    DATABASE_PATH,
    STATE_TITLE,
    STATE_DESCRIPTION,
    STATE_ASSIGNEE,
    STATE_DEADLINE,
    STATE_PRIORITY,
    STATE_CONFIRM,
)
from database import Database

# Импортируем обработчики
from handlers.start import (
    start_command,
    help_command,
    menu_command,
    cancel_command,
    settings_command,
    timezone_command,
)
from handlers.team import (
    createteam_command,
    team_command,
    invite_command,
    join_command,
    leave_command,
)
from handlers.tasks import (
    newtask_command,
    task_title_received,
    task_description_received,
    task_description_skipped,
    task_assignee_selected,
    task_deadline_received,
    task_deadline_skipped,
    task_priority_selected,
    task_confirmed,
    mytasks_command,
    alltasks_command,
    today_command,
    week_command,
    task_detail_command,
)
from handlers.callbacks import callback_handler, comment_text_handler
from handlers.subscription import (
    subscribe_command,
    upgrade_command,
    billing_command,
)
from handlers.stats import stats_command, mystats_command
from handlers.calendar_handler import calendar_command
from scheduler.reminders import setup_scheduler

logger = logging.getLogger(__name__)


# Обработчик ошибок
async def error_handler(update, context) -> None:
    """Глобальный обработчик ошибок."""
    logger.error("Ошибка при обработке обновления: %s", context.error)
    # Пытаемся уведомить пользователя
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Произошла ошибка. Попробуйте позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass


# Инициализация и запуск бота
def main() -> None:
    """Основная функция запуска бота."""
    # Проверяем наличие токена
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.critical("BOT_TOKEN не установлен! Создайте .env файл.")
        print("❌ Ошибка: BOT_TOKEN не установлен.")
        print("   Скопируйте .env.example в .env и укажите токен бота.")
        sys.exit(1)

    # Инициализируем БД
    db = Database(DATABASE_PATH)

    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # Сохраняем БД в контексте бота
    app.bot_data["db"] = db

    # ─── Регистрация ConversationHandler для создания задач ──────

    task_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newtask", newtask_command)],
        states={
            STATE_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, task_title_received),
            ],
            STATE_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, task_description_received),
                CallbackQueryHandler(task_description_skipped, pattern="^skip$"),
            ],
            STATE_ASSIGNEE: [
                CallbackQueryHandler(task_assignee_selected, pattern="^assign_"),
            ],
            STATE_DEADLINE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, task_deadline_received),
                CallbackQueryHandler(task_deadline_skipped, pattern="^skip$"),
            ],
            STATE_PRIORITY: [
                CallbackQueryHandler(task_priority_selected, pattern="^priority_"),
            ],
            STATE_CONFIRM: [
                CallbackQueryHandler(task_confirmed, pattern="^confirm_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        allow_reentry=True,
    )

    # ─── Регистрация обработчиков команд ────────────────────────

    # Основные команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("timezone", timezone_command))

    # Управление командами
    app.add_handler(CommandHandler("createteam", createteam_command))
    app.add_handler(CommandHandler("team", team_command))
    app.add_handler(CommandHandler("invite", invite_command))
    app.add_handler(CommandHandler("join", join_command))
    app.add_handler(CommandHandler("leave", leave_command))

    # Создание задач (ConversationHandler)
    app.add_handler(task_conv_handler)

    # Просмотр задач
    app.add_handler(CommandHandler("mytasks", mytasks_command))
    app.add_handler(CommandHandler("alltasks", alltasks_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("task", task_detail_command))

    # Подписка
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("upgrade", upgrade_command))
    app.add_handler(CommandHandler("billing", billing_command))

    # Статистика
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("mystats", mystats_command))

    # Календарь
    app.add_handler(CommandHandler("calendar", calendar_command))

    # Обработка inline-кнопок
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Обработка текстовых сообщений (комментарии)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, comment_text_handler)
    )

    # Глобальный обработчик ошибок
    app.add_error_handler(error_handler)

    # ─── Запуск планировщика ────────────────────────────────────

    scheduler = setup_scheduler(app.bot, db)

    # ─── Запуск бота ────────────────────────────────────────────

    logger.info("🚀 Бот запускается...")
    print("🚀 Бот запущен! Нажмите Ctrl+C для остановки.")

    try:
        app.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        # Graceful shutdown
        scheduler.shutdown(wait=False)
        db.close()
        logger.info("Бот остановлен")
        print("👋 Бот остановлен.")


if __name__ == "__main__":
    main()
