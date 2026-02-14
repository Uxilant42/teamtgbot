"""
Обработчики команд управления задачами.
/newtask (ConversationHandler), /mytasks, /alltasks, /today, /week, /task
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from config import STATE_TITLE, STATE_DESCRIPTION, STATE_ASSIGNEE, STATE_DEADLINE, STATE_PRIORITY, STATE_CONFIRM
from utils.keyboards import (
    get_priority_keyboard,
    get_skip_keyboard,
    get_members_keyboard,
    get_confirm_keyboard,
    get_task_keyboard,
)
from utils.formatters import format_task_message, format_tasks_list
from utils.validators import check_task_limit, format_limit_message, validate_deadline
from utils.notifications import notify_task_assigned

logger = logging.getLogger(__name__)


# ─── ConversationHandler: создание задачи ──────────────────────────

# Шаг 0: запуск создания задачи
async def newtask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания новой задачи. Просим ввести название."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Получаем команду пользователя
    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text(
            "❌ Сначала создайте или присоединитесь к команде.\n"
            "/createteam или /join",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    # Проверяем лимит задач
    limit_check = check_task_limit(db, team["team_id"])
    if not limit_check["allowed"]:
        await update.message.reply_text(
            format_limit_message(limit_check, "задачу"), parse_mode="HTML"
        )
        return ConversationHandler.END

    # Сохраняем team_id в контексте диалога
    context.user_data["new_task"] = {"team_id": team["team_id"]}

    await update.message.reply_text(
        "📝 <b>Создание задачи</b>\n\n"
        "Шаг 1/5: Введите <b>название</b> задачи:\n\n"
        "<i>Отмена: /cancel</i>",
        parse_mode="HTML",
    )
    return STATE_TITLE


# Шаг 1: название задачи
async def task_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия задачи. Просим описание."""
    title = update.message.text.strip()

    # Проверяем длину названия
    if len(title) > 200:
        await update.message.reply_text("❌ Название слишком длинное (макс. 200 символов). Попробуйте ещё раз:")
        return STATE_TITLE

    if len(title) < 2:
        await update.message.reply_text("❌ Название слишком короткое. Попробуйте ещё раз:")
        return STATE_TITLE

    context.user_data["new_task"]["title"] = title

    await update.message.reply_text(
        "📝 <b>Создание задачи</b>\n\n"
        "Шаг 2/5: Введите <b>описание</b> задачи:\n\n"
        "<i>Можно пропустить</i>",
        parse_mode="HTML",
        reply_markup=get_skip_keyboard(),
    )
    return STATE_DESCRIPTION


# Шаг 2: описание задачи
async def task_description_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение описания задачи. Просим выбрать исполнителя."""
    description = update.message.text.strip()

    # Проверяем длину описания
    if len(description) > 1000:
        await update.message.reply_text("❌ Описание слишком длинное (макс. 1000 символов). Попробуйте ещё раз:")
        return STATE_DESCRIPTION

    context.user_data["new_task"]["description"] = description

    return await _ask_assignee(update, context)


# Обработка пропуска описания через callback
async def task_description_skipped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск описания задачи. Переход к выбору исполнителя."""
    query = update.callback_query
    await query.answer()

    context.user_data["new_task"]["description"] = None
    return await _ask_assignee(update, context)


# Вспомогательная функция — показываем список участников
async def _ask_assignee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отправляет клавиатуру выбора исполнителя."""
    db: Database = context.bot_data["db"]
    team_id = context.user_data["new_task"]["team_id"]
    members = db.get_team_members(team_id)

    msg = (
        "📝 <b>Создание задачи</b>\n\n"
        "Шаг 3/5: Выберите <b>исполнителя</b>:"
    )
    keyboard = get_members_keyboard([dict(m) for m in members], action="assign")

    # Определяем как отправить — через callback или message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            msg, parse_mode="HTML", reply_markup=keyboard
        )
    return STATE_ASSIGNEE


# Шаг 3: выбор исполнителя через callback
async def task_assignee_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора исполнителя. Просим дедлайн."""
    query = update.callback_query
    await query.answer()

    data = query.data  # assign_{user_id} или assign_none
    assignee_id = data.replace("assign_", "")

    # Сохраняем исполнителя
    if assignee_id == "none":
        context.user_data["new_task"]["assignee_id"] = None
    else:
        context.user_data["new_task"]["assignee_id"] = int(assignee_id)

    await query.edit_message_text(
        "📝 <b>Создание задачи</b>\n\n"
        "Шаг 4/5: Укажите <b>дедлайн</b>:\n\n"
        "Формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
        "Пример: <code>20.02.2026 18:00</code>\n\n"
        "<i>Можно пропустить</i>",
        parse_mode="HTML",
        reply_markup=get_skip_keyboard(),
    )
    return STATE_DEADLINE


# Шаг 4: установка дедлайна
async def task_deadline_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение дедлайна. Просим выбрать приоритет."""
    text = update.message.text.strip()

    # Валидируем дату
    deadline = validate_deadline(text)
    if not deadline:
        await update.message.reply_text(
            "❌ Неверный формат даты или дата в прошлом.\n"
            "Используйте формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
            "Попробуйте ещё раз:",
            parse_mode="HTML",
            reply_markup=get_skip_keyboard(),
        )
        return STATE_DEADLINE

    context.user_data["new_task"]["deadline"] = deadline.isoformat()

    await update.message.reply_text(
        "📝 <b>Создание задачи</b>\n\n"
        "Шаг 5/5: Выберите <b>приоритет</b>:",
        parse_mode="HTML",
        reply_markup=get_priority_keyboard(),
    )
    return STATE_PRIORITY


# Обработка пропуска дедлайна
async def task_deadline_skipped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск дедлайна. Переход к выбору приоритета."""
    query = update.callback_query
    await query.answer()

    context.user_data["new_task"]["deadline"] = None

    await query.edit_message_text(
        "📝 <b>Создание задачи</b>\n\n"
        "Шаг 5/5: Выберите <b>приоритет</b>:",
        parse_mode="HTML",
        reply_markup=get_priority_keyboard(),
    )
    return STATE_PRIORITY


# Шаг 5: выбор приоритета
async def task_priority_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора приоритета. Показ подтверждения."""
    query = update.callback_query
    await query.answer()

    priority = query.data.replace("priority_", "")  # low / medium / high
    context.user_data["new_task"]["priority"] = priority

    # Формируем превью задачи
    task_data = context.user_data["new_task"]
    db: Database = context.bot_data["db"]

    # Получаем имя исполнителя
    assignee_name = "Не назначен"
    if task_data.get("assignee_id"):
        assignee = db.get_user(task_data["assignee_id"])
        if assignee:
            assignee_name = assignee["first_name"] or assignee["username"] or "—"

    from config import PRIORITY_EMOJI
    p_emoji = PRIORITY_EMOJI.get(priority, "⚪️")

    preview = (
        "📋 <b>Подтвердите создание задачи:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>{task_data['title']}</b>\n"
    )
    if task_data.get("description"):
        preview += f"📄 {task_data['description']}\n"
    preview += (
        f"👤 Исполнитель: {assignee_name}\n"
        f"📅 Дедлайн: {task_data.get('deadline', 'Не установлен')}\n"
        f"{p_emoji} Приоритет: {priority}\n"
    )

    await query.edit_message_text(
        preview, parse_mode="HTML", reply_markup=get_confirm_keyboard()
    )
    return STATE_CONFIRM


# Шаг 6: подтверждение создания
async def task_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Создание задачи после подтверждения."""
    query = update.callback_query
    await query.answer()

    # Проверяем выбор пользователя
    if query.data == "confirm_no":
        context.user_data.clear()
        await query.edit_message_text("❌ Создание задачи отменено.")
        return ConversationHandler.END

    db: Database = context.bot_data["db"]
    user = update.effective_user
    task_data = context.user_data.get("new_task", {})

    # Создаём задачу в БД
    task_id = db.create_task(
        team_id=task_data["team_id"],
        title=task_data["title"],
        author_id=user.id,
        description=task_data.get("description"),
        assignee_id=task_data.get("assignee_id"),
        deadline=task_data.get("deadline"),
        priority=task_data.get("priority", "medium"),
    )

    # Проверяем результат
    if not task_id:
        await query.edit_message_text("❌ Ошибка при создании задачи.")
        context.user_data.clear()
        return ConversationHandler.END

    await query.edit_message_text(
        f"✅ <b>Задача #{task_id} создана!</b>\n\n"
        f"📝 {task_data['title']}\n\n"
        f"Посмотреть: /task {task_id}",
        parse_mode="HTML",
    )

    # Уведомляем исполнителя, если назначен и это не автор
    if task_data.get("assignee_id") and task_data["assignee_id"] != user.id:
        task = db.get_task(task_id)
        author_name = user.first_name or user.username or str(user.id)
        await notify_task_assigned(
            context.bot, task_data["assignee_id"], dict(task), author_name
        )

    context.user_data.clear()
    logger.info("Задача #%s создана пользователем %s", task_id, user.id)
    return ConversationHandler.END


# ─── Просмотр задач ────────────────────────────────────────────────

# Обработчик команды /mytasks — мои задачи
async def mytasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Список задач, назначенных на текущего пользователя."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    tasks = db.get_user_tasks(user.id, team["team_id"])
    msg = format_tasks_list([dict(t) for t in tasks], f"📋 Мои задачи")
    await update.message.reply_text(msg, parse_mode="HTML")


# Обработчик команды /alltasks — все задачи команды
async def alltasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ всех задач текущей команды."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    tasks = db.get_team_tasks(team["team_id"])
    msg = format_tasks_list(
        [dict(t) for t in tasks], f"📊 Все задачи «{team['name']}»"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


# Обработчик команды /today — задачи на сегодня
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ задач с дедлайном на сегодня."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    tasks = db.get_tasks_today(team["team_id"])
    msg = format_tasks_list([dict(t) for t in tasks], "📅 Задачи на сегодня")
    await update.message.reply_text(msg, parse_mode="HTML")


# Обработчик команды /week — задачи на неделю
async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ задач на текущую неделю."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    tasks = db.get_tasks_week(team["team_id"])
    msg = format_tasks_list([dict(t) for t in tasks], "📆 Задачи на неделю")
    await update.message.reply_text(msg, parse_mode="HTML")


# Обработчик команды /task [ID] — детали задачи
async def task_detail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ детальной информации о задаче."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Проверяем что передан ID задачи
    if not context.args:
        await update.message.reply_text(
            "📝 Укажите ID задачи.\nПример: <code>/task 42</code>",
            parse_mode="HTML",
        )
        return

    # Парсим ID задачи
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID задачи должен быть числом.")
        return

    task = db.get_task(task_id)
    if not task:
        await update.message.reply_text("❌ Задача не найдена.")
        return

    # Проверяем что пользователь состоит в той же команде
    team = db.get_user_active_team(user.id)
    if not team or task["team_id"] != team["team_id"]:
        await update.message.reply_text("❌ У вас нет доступа к этой задаче.")
        return

    # Получаем имена исполнителя и автора
    assignee_name = "Не назначен"
    if task["assignee_id"]:
        assignee = db.get_user(task["assignee_id"])
        if assignee:
            name = assignee["first_name"] or ""
            uname = f"@{assignee['username']}" if assignee["username"] else ""
            assignee_name = f"{name} {uname}".strip() or str(task["assignee_id"])

    author = db.get_user(task["author_id"])
    author_name = "—"
    if author:
        name = author["first_name"] or ""
        uname = f"@{author['username']}" if author["username"] else ""
        author_name = f"{name} {uname}".strip() or str(task["author_id"])

    # Определяем роль пользователя
    role = db.get_member_role(team["team_id"], user.id)

    msg = format_task_message(dict(task), assignee_name, author_name)

    # Добавляем комментарии
    comments = db.get_task_comments(task_id)
    if comments:
        msg += "\n\n💬 <b>Комментарии:</b>\n"
        for c in comments[-5:]:  # Показываем последние 5
            c_name = c["first_name"] or c["username"] or "—"
            msg += f"  • <b>{c_name}:</b> {c['text']}\n"

    keyboard = get_task_keyboard(task_id, task["status"], role)
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)
