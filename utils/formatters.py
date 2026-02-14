"""
Модуль форматирования сообщений для Telegram-бота.
Красивый вывод задач, списков, статистики в HTML-разметке.
"""

from datetime import datetime
from typing import Any

from config import PRIORITY_EMOJI, STATUS_EMOJI, STATUS_TEXT, PRIORITY_TEXT


# Форматирование карточки задачи
def format_task_message(
    task: dict[str, Any],
    assignee_name: str = "Не назначен",
    author_name: str = "—",
) -> str:
    """
    Форматирует полную карточку задачи для отображения в чате.
    Возвращает строку в HTML-разметке.
    """
    priority = task.get("priority", "medium")
    status = task.get("status", "todo")

    # Расчёт времени до дедлайна
    deadline_str = "Не установлен"
    deadline_info = ""
    if task.get("deadline"):
        try:
            deadline_dt = datetime.fromisoformat(str(task["deadline"]))
            deadline_str = deadline_dt.strftime("%d.%m.%Y %H:%M")
            now = datetime.now()
            diff = deadline_dt - now
            # Определяем оставшееся время
            if diff.total_seconds() < 0:
                deadline_info = "⚠️ ПРОСРОЧЕНО"
            elif diff.days > 0:
                deadline_info = f"через {diff.days} дн."
            elif diff.seconds > 3600:
                deadline_info = f"через {diff.seconds // 3600} ч."
            else:
                deadline_info = f"через {diff.seconds // 60} мин."
        except (ValueError, TypeError):
            deadline_str = str(task.get("deadline", ""))

    # Собираем текст сообщения
    msg = (
        f"📌 <b>Задача #{task['task_id']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>{task['title']}</b>\n\n"
        f"👤 <b>Исполнитель:</b> {assignee_name}\n"
        f"✍️ <b>Автор:</b> {author_name}\n"
        f"📅 <b>Дедлайн:</b> {deadline_str}"
    )

    # Добавляем информацию о времени до дедлайна
    if deadline_info:
        msg += f" ({deadline_info})"

    msg += (
        f"\n{PRIORITY_EMOJI.get(priority, '⚪️')} <b>Приоритет:</b> "
        f"{PRIORITY_TEXT.get(priority, priority)}\n"
    )

    # Добавляем описание, если есть
    if task.get("description"):
        msg += f"\n📄 <b>Описание:</b>\n{task['description']}\n"

    # Добавляем теги, если есть
    if task.get("tags"):
        msg += f"\n🏷 <b>Теги:</b> {task['tags']}\n"

    # Статус
    msg += (
        f"\n📊 <b>Статус:</b> {STATUS_EMOJI.get(status, '⚪️')} "
        f"{STATUS_TEXT.get(status, status)}"
    )

    return msg


# Форматирование списка задач
def format_tasks_list(
    tasks: list[dict[str, Any]], title: str = "📋 Задачи"
) -> str:
    """
    Форматирует список задач для отображения в чате.
    Группирует по статусу.
    """
    # Проверяем пустой ли список
    if not tasks:
        return f"{title}\n\n<i>Список пуст</i> 🤷‍♂️"

    msg = f"{title} ({len(tasks)})\n\n"

    # Группируем задачи по статусу
    groups: dict[str, list] = {
        "todo": [],
        "in_progress": [],
        "done": [],
        "cancelled": [],
    }
    # Проходим по задачам и распределяем по группам
    for task in tasks:
        status = task.get("status", "todo")
        if status in groups:
            groups[status].append(task)

    # Формируем вывод по группам
    if groups["todo"]:
        msg += f"⏳ <b>К выполнению:</b>\n"
        for task in groups["todo"]:
            msg += _format_task_line(task)
        msg += "\n"

    if groups["in_progress"]:
        msg += f"🔄 <b>В работе:</b>\n"
        for task in groups["in_progress"]:
            msg += _format_task_line(task)
        msg += "\n"

    if groups["done"]:
        msg += f"✅ <b>Выполнено:</b>\n"
        # Показываем последние 5 выполненных задач
        for task in groups["done"][:5]:
            msg += _format_task_line(task)
        if len(groups["done"]) > 5:
            msg += f"   <i>...и ещё {len(groups['done']) - 5}</i>\n"
        msg += "\n"

    return msg.rstrip()


# Форматирование одной строки задачи в списке
def _format_task_line(task: dict[str, Any]) -> str:
    """Форматирует одну строку задачи для отображения в списке."""
    priority = task.get("priority", "medium")
    p_emoji = PRIORITY_EMOJI.get(priority, "⚪️")

    deadline_str = ""
    # Проверяем наличие дедлайна
    if task.get("deadline"):
        try:
            dl = datetime.fromisoformat(str(task["deadline"]))
            deadline_str = f" → {dl.strftime('%d.%m %H:%M')}"
        except (ValueError, TypeError):
            pass

    return f"  • #{task['task_id']} {p_emoji} {task['title']}{deadline_str}\n"


# Форматирование статистики команды
def format_team_stats(stats: dict[str, Any], team_name: str) -> str:
    """Форматирует статистику команды."""
    msg = (
        f"📈 <b>Статистика команды «{team_name}»</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Всего задач: <b>{stats['total']}</b>\n"
        f"🔄 Активных: <b>{stats['active']}</b>\n"
        f"✅ Выполнено за неделю: <b>{stats['done_week']}</b>\n"
        f"✅ Выполнено за месяц: <b>{stats['done_month']}</b>\n"
        f"⚠️ Просрочено: <b>{stats['overdue']}</b>\n"
    )

    # Добавляем топ участников, если есть
    if stats.get("top_members"):
        msg += "\n🏆 <b>Топ участников (за неделю):</b>\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, member in enumerate(stats["top_members"]):
            name = member["first_name"] or member["username"] or "—"
            medal = medals[i] if i < len(medals) else f"{i + 1}."
            msg += f"  {medal} {name} — {member['cnt']} задач\n"

    return msg


# Форматирование личной статистики
def format_user_stats(stats: dict[str, Any], user_name: str) -> str:
    """Форматирует личную статистику пользователя."""
    msg = (
        f"📈 <b>Статистика — {user_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Выполнено: <b>{stats['done']}</b>\n"
        f"🔄 В работе: <b>{stats['in_progress']}</b>\n"
        f"⏳ Ожидают: <b>{stats['todo']}</b>\n"
        f"✅ За неделю: <b>{stats['done_week']}</b>\n"
        f"⚠️ Просрочено: <b>{stats['overdue']}</b>\n"
        f"🎯 В срок: <b>{stats['on_time_pct']}%</b>\n"
    )
    return msg


# Форматирование информации о команде
def format_team_info(
    team: dict[str, Any],
    members: list[dict[str, Any]],
    owner_name: str,
) -> str:
    """Форматирует информацию о команде и её участниках."""
    msg = (
        f"👥 <b>Команда «{team['name']}»</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 <b>Владелец:</b> {owner_name}\n"
        f"📅 <b>Создана:</b> {team['created_at'][:10]}\n"
        f"💎 <b>План:</b> {team['subscription_type'].upper()}\n"
        f"👤 <b>Участников:</b> {len(members)}\n\n"
        f"<b>Участники:</b>\n"
    )

    role_emoji = {"owner": "👑", "admin": "⭐", "member": "👤"}
    # Проходим по участникам и добавляем в список
    for m in members:
        name = m.get("first_name") or m.get("username") or str(m["user_id"])
        r_emoji = role_emoji.get(m.get("role", "member"), "👤")
        msg += f"  {r_emoji} {name}\n"

    return msg


# Форматирование справочного сообщения
def format_help_message() -> str:
    """Форматирует сообщение справки по всем командам."""
    return (
        "ℹ️ <b>Справка по командам</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>🚀 Основные:</b>\n"
        "/start — Начало работы\n"
        "/menu — Главное меню\n"
        "/help — Эта справка\n\n"
        "<b>👥 Команда:</b>\n"
        "/createteam — Создать команду\n"
        "/team — Моя команда\n"
        "/invite — Инвайт-код\n"
        "/join — Присоединиться\n"
        "/leave — Покинуть команду\n\n"
        "<b>📝 Задачи:</b>\n"
        "/newtask — Новая задача\n"
        "/mytasks — Мои задачи\n"
        "/alltasks — Все задачи\n"
        "/today — На сегодня\n"
        "/week — На неделю\n"
        "/task [ID] — Детали задачи\n\n"
        "<b>📈 Аналитика:</b>\n"
        "/stats — Статистика команды\n"
        "/mystats — Моя статистика\n"
        "/calendar — Экспорт в .ics\n\n"
        "<b>💎 Подписка:</b>\n"
        "/subscribe — Тарифы\n\n"
        "<b>⚙️ Прочее:</b>\n"
        "/cancel — Отменить действие\n"
    )
