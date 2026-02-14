"""
Модуль планировщика напоминаний.
Использует APScheduler для периодических задач:
- Проверка дедлайнов каждые 30 минут
- Ежедневная сводка задач в 9:00
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from database import Database

logger = logging.getLogger(__name__)


# Настройка и запуск планировщика
def setup_scheduler(bot: Bot, db: Database) -> AsyncIOScheduler:
    """
    Создаёт и настраивает планировщик задач.
    Возвращает экземпляр AsyncIOScheduler.
    """
    scheduler = AsyncIOScheduler()

    # Проверка дедлайнов каждые 30 минут
    scheduler.add_job(
        check_upcoming_deadlines,
        "interval",
        minutes=30,
        args=[bot, db],
        id="check_deadlines",
        name="Проверка дедлайнов",
    )

    # Ежедневная сводка задач в 9:00
    scheduler.add_job(
        send_daily_summary,
        "cron",
        hour=9,
        minute=0,
        args=[bot, db],
        id="daily_summary",
        name="Ежедневная сводка",
    )

    scheduler.start()
    logger.info("Планировщик запущен: проверка дедлайнов + ежедневная сводка")
    return scheduler


# Проверка приближающихся дедлайнов
async def check_upcoming_deadlines(bot: Bot, db: Database) -> None:
    """
    Ищет задачи с приближающимся дедлайном и отправляет напоминания.
    Временные окна: 24 часа, 3 часа, момент дедлайна.
    """
    now = datetime.now()

    # Определяем временные окна для напоминаний
    windows = {
        "24h": (
            now + timedelta(hours=23, minutes=30),
            now + timedelta(hours=24, minutes=30),
        ),
        "3h": (
            now + timedelta(hours=2, minutes=30),
            now + timedelta(hours=3, minutes=30),
        ),
        "now": (
            now - timedelta(minutes=15),
            now + timedelta(minutes=15),
        ),
    }

    # Проходим по каждому временному окну
    for reminder_type, (start, end) in windows.items():
        tasks = db.get_upcoming_tasks(start.isoformat(), end.isoformat())

        # Проходим по найденным задачам
        for task in tasks:
            # Пропускаем если напоминание уже отправлено
            if db.is_reminder_sent(task["task_id"], reminder_type):
                continue

            # Проверяем есть ли исполнитель
            if not task["assignee_id"]:
                continue

            # Формируем текст напоминания
            message = _format_reminder(task, reminder_type)

            try:
                await bot.send_message(
                    chat_id=task["assignee_id"],
                    text=message,
                    parse_mode="HTML",
                )
                # Помечаем что напоминание отправлено
                db.mark_reminder_sent(task["task_id"], reminder_type)
                logger.info(
                    "Напоминание '%s' отправлено для задачи #%s",
                    reminder_type,
                    task["task_id"],
                )
            except Exception as e:
                logger.error(
                    "Ошибка отправки напоминания задачи #%s: %s",
                    task["task_id"],
                    e,
                )


# Форматирование текста напоминания
def _format_reminder(task: dict, reminder_type: str) -> str:
    """Формирует текст напоминания в зависимости от типа."""
    deadline_str = ""
    try:
        dl = datetime.fromisoformat(str(task["deadline"]))
        deadline_str = dl.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        pass

    # Определяем текст и эмодзи по типу напоминания
    if reminder_type == "24h":
        header = "⏰ <b>Напоминание!</b>"
        time_info = "должна быть выполнена <b>завтра</b>"
    elif reminder_type == "3h":
        header = "⚠️ <b>Срочно!</b>"
        time_info = "должна быть выполнена <b>через 3 часа</b>"
    else:
        header = "🔥 <b>ДЕДЛАЙН СЕЙЧАС!</b>"
        time_info = "должна быть выполнена <b>прямо сейчас</b>"

    return (
        f"{header}\n\n"
        f"📝 Задача <b>#{task['task_id']}</b> — {task['title']}\n"
        f"📅 Дедлайн: {deadline_str}\n\n"
        f"Задача {time_info}!\n\n"
        f"Открыть: /task {task['task_id']}"
    )


# Ежедневная сводка задач
async def send_daily_summary(bot: Bot, db: Database) -> None:
    """
    Отправляет ежедневную сводку задач каждому пользователю в 9:00.
    Включает задачи на сегодня и просроченные.
    """
    # Получаем всех пользователей через все команды
    try:
        all_members = db.conn.execute(
            """SELECT DISTINCT tm.user_id, tm.team_id, t.name as team_name
               FROM team_members tm
               JOIN teams t ON tm.team_id = t.team_id"""
        ).fetchall()
    except Exception as e:
        logger.error("Ошибка получения пользователей для сводки: %s", e)
        return

    # Группируем по пользователю
    user_teams: dict = {}
    for row in all_members:
        uid = row["user_id"]
        if uid not in user_teams:
            user_teams[uid] = []
        user_teams[uid].append({"team_id": row["team_id"], "team_name": row["team_name"]})

    # Отправляем сводку каждому пользователю
    for user_id, teams in user_teams.items():
        msg = "☀️ <b>Доброе утро! Ваша сводка на сегодня:</b>\n\n"
        has_tasks = False

        # Проходим по командам пользователя
        for team_info in teams:
            today_tasks = db.get_tasks_today(team_info["team_id"])
            user_today = [t for t in today_tasks if t["assignee_id"] == user_id]

            # Проверяем есть ли задачи на сегодня
            if user_today:
                has_tasks = True
                msg += f"👥 <b>{team_info['team_name']}</b>\n"
                for task in user_today:
                    from config import PRIORITY_EMOJI
                    p = PRIORITY_EMOJI.get(task["priority"], "⚪️")
                    dl = ""
                    if task["deadline"]:
                        try:
                            dl_dt = datetime.fromisoformat(str(task["deadline"]))
                            dl = f" → {dl_dt.strftime('%H:%M')}"
                        except (ValueError, TypeError):
                            pass
                    msg += f"  • #{task['task_id']} {p} {task['title']}{dl}\n"
                msg += "\n"

        # Проверяем просроченные задачи
        overdue = db.get_overdue_tasks()
        user_overdue = [t for t in overdue if t["assignee_id"] == user_id]
        if user_overdue:
            has_tasks = True
            msg += "⚠️ <b>Просроченные задачи:</b>\n"
            for task in user_overdue[:5]:
                msg += f"  • #{task['task_id']} {task['title']}\n"
            msg += "\n"

        # Отправляем только если есть задачи
        if has_tasks:
            msg += "Хорошего дня! 🚀"
            try:
                await bot.send_message(chat_id=user_id, text=msg, parse_mode="HTML")
            except Exception as e:
                logger.error("Ошибка отправки сводки пользователю %s: %s", user_id, e)
