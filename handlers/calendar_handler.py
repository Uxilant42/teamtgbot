"""
Обработчик команды /calendar — экспорт задач в .ics файл.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import Database
from utils.calendar_export import generate_ics_file

logger = logging.getLogger(__name__)


# Обработчик команды /calendar — экспорт в iCalendar
async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Генерация и отправка .ics файла с задачами команды."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    # Получаем все задачи команды
    tasks = db.get_team_tasks(team["team_id"])
    if not tasks:
        await update.message.reply_text("📅 Нет задач для экспорта.")
        return

    # Генерируем .ics файл
    try:
        ics_data = generate_ics_file([dict(t) for t in tasks], team["name"])

        # Отправляем файл пользователю
        from io import BytesIO
        file = BytesIO(ics_data)
        file.name = f"tasks_{team['name']}.ics"

        await update.message.reply_document(
            document=file,
            caption=(
                f"📅 Календарь задач команды «{team['name']}»\n\n"
                f"Импортируйте файл в Google Calendar, "
                f"Apple Calendar или Outlook."
            ),
            parse_mode="HTML",
        )
        logger.info("Календарь экспортирован для команды %s", team["team_id"])
    except Exception as e:
        logger.error("Ошибка экспорта календаря: %s", e)
        await update.message.reply_text("❌ Ошибка при генерации календаря.")
