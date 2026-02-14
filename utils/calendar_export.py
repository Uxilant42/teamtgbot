"""
Модуль экспорта задач в формат iCalendar (.ics).
Совместим с Google Calendar, Apple Calendar, Outlook.
"""

import logging
from datetime import timedelta, datetime
from icalendar import Calendar, Event

logger = logging.getLogger(__name__)


# Генерация .ics файла со всеми задачами команды
def generate_ics_file(tasks: list, team_name: str = "Задачи") -> bytes:
    """
    Генерирует .ics файл из списка задач.

    Args:
        tasks: список задач (dict-like объекты с полями task_id, title, description, deadline, priority, status)
        team_name: название команды для заголовка календаря

    Returns:
        bytes — содержимое .ics файла
    """
    # Создаём объект календаря
    cal = Calendar()
    cal.add("prodid", "-//Task Manager Bot//telegram.org//")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"Задачи — {team_name}")
    cal.add("x-wr-timezone", "UTC")

    # Проходим по задачам и создаём события
    for task in tasks:
        # Пропускаем задачи без дедлайна
        if not task.get("deadline"):
            continue

        event = Event()
        event.add("uid", f"task-{task['task_id']}@taskbot.telegram")

        status = task.get("status", "todo")
        title = task.get("title", "Без названия")
        event.add("summary", f"[{status.upper()}] {title}")

        # Описание задачи
        if task.get("description"):
            event.add("description", task["description"])

        # Конвертируем дедлайн в datetime
        try:
            deadline_dt = datetime.fromisoformat(str(task["deadline"]))
        except (ValueError, TypeError):
            continue

        event.add("dtstart", deadline_dt)
        event.add("dtend", deadline_dt + timedelta(hours=1))
        event.add("dtstamp", datetime.now())

        # Категория по приоритету
        priority = task.get("priority", "medium")
        if priority == "high":
            event.add("categories", "ВЫСОКИЙ ПРИОРИТЕТ")
            event.add("priority", 1)
        elif priority == "medium":
            event.add("categories", "СРЕДНИЙ ПРИОРИТЕТ")
            event.add("priority", 5)
        else:
            event.add("categories", "НИЗКИЙ ПРИОРИТЕТ")
            event.add("priority", 9)

        # Статус события в формате iCal
        if status == "done":
            event.add("status", "COMPLETED")
        elif status == "in_progress":
            event.add("status", "IN-PROCESS")
        else:
            event.add("status", "NEEDS-ACTION")

        cal.add_component(event)

    logger.info("Сгенерирован .ics файл: %d событий", len(tasks))
    return cal.to_ical()
