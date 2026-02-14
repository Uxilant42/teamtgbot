"""
Обработчики callback-запросов от inline-кнопок.
Смена статусов, удаление, меню, комментарии.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from utils.keyboards import (
    get_main_menu_keyboard,
    get_task_keyboard,
    get_delete_confirm_keyboard,
    get_back_to_menu_keyboard,
)
from utils.formatters import (
    format_task_message,
    format_tasks_list,
    format_help_message,
    format_team_info,
)
from utils.notifications import notify_status_changed

logger = logging.getLogger(__name__)

# Состояние для ожидания комментария
WAITING_COMMENT = 100


# Главный обработчик callback-запросов
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Маршрутизатор callback-запросов от inline-кнопок."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Обработка кнопок меню
    if data == "back_to_menu":
        await handle_back_to_menu(update, context)
    elif data.startswith("menu_"):
        await handle_menu_callback(update, context)
    # Обработка смены статуса задачи
    elif data.startswith("status_"):
        await handle_status_callback(update, context)
    # Обработка удаления задачи
    elif data.startswith("delete_"):
        await handle_delete_callback(update, context)
    # Подтверждение удаления
    elif data.startswith("confirm_delete_"):
        await handle_confirm_delete_callback(update, context)
    # Отмена удаления
    elif data.startswith("cancel_delete_"):
        await query.edit_message_text("✅ Удаление отменено.",
            reply_markup=get_back_to_menu_keyboard())
    # Отмена задачи (статус cancelled)
    elif data.startswith("cancel_"):
        await handle_cancel_task_callback(update, context)
    # Начало добавления комментария
    elif data.startswith("comment_"):
        await handle_comment_start(update, context)
    # Просмотр задачи по нажатию
    elif data.startswith("edit_"):
        await handle_edit_callback(update, context)


# Обработка кнопки "Назад в главное меню"
async def handle_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат пользователя в главное меню."""
    query = update.callback_query
    user = update.effective_user

    try:
        await query.edit_message_text(
            f"👋 <b>{user.first_name}</b>, выберите действие:\n\n"
            "📋 <b>Главное меню</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )
    except Exception:
        # Если не удалось отредактировать — отправляем новое сообщение
        await query.message.reply_text(
            f"👋 <b>{user.first_name}</b>, выберите действие:\n\n"
            "📋 <b>Главное меню</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )


# Обработка кнопок главного меню
async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий кнопок главного меню."""
    query = update.callback_query
    data = query.data
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Проверяем активную команду
    team = db.get_user_active_team(user.id)

    if data == "menu_newtask":
        # Перенаправляем на создание задачи
        await query.edit_message_text(
            "📝 Для создания задачи используйте команду /newtask",
            parse_mode="HTML",
        )

    elif data == "menu_mytasks":
        # Проверяем наличие команды
        if not team:
            await query.edit_message_text("❌ Вы не состоите в команде.")
            return
        tasks = db.get_user_tasks(user.id, team["team_id"])
        msg = format_tasks_list([dict(t) for t in tasks], "📋 Мои задачи")
        await query.edit_message_text(msg, parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard())

    elif data == "menu_alltasks":
        if not team:
            await query.edit_message_text("❌ Вы не состоите в команде.")
            return
        tasks = db.get_team_tasks(team["team_id"])
        msg = format_tasks_list([dict(t) for t in tasks], f"📊 Все задачи «{team['name']}»")
        await query.edit_message_text(msg, parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard())

    elif data == "menu_today":
        if not team:
            await query.edit_message_text("❌ Вы не состоите в команде.")
            return
        tasks = db.get_tasks_today(team["team_id"])
        msg = format_tasks_list([dict(t) for t in tasks], "📅 Задачи на сегодня")
        await query.edit_message_text(msg, parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard())

    elif data == "menu_week":
        if not team:
            await query.edit_message_text("❌ Вы не состоите в команде.")
            return
        tasks = db.get_tasks_week(team["team_id"])
        msg = format_tasks_list([dict(t) for t in tasks], "📆 Задачи на неделю")
        await query.edit_message_text(msg, parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard())

    elif data == "menu_team":
        if not team:
            await query.edit_message_text("❌ Вы не состоите в команде.")
            return
        members = db.get_team_members(team["team_id"])
        owner = db.get_user(team["owner_id"])
        owner_name = owner["first_name"] if owner else "—"
        msg = format_team_info(dict(team), [dict(m) for m in members], owner_name)
        await query.edit_message_text(msg, parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard())

    elif data == "menu_stats":
        await query.edit_message_text(
            "📈 Статистика: /stats\n📊 Моя статистика: /mystats",
            parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard(),
        )

    elif data == "menu_calendar":
        await query.edit_message_text(
            "📅 Экспорт календаря: /calendar", parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard(),
        )

    elif data == "menu_subscribe":
        await query.edit_message_text(
            "💎 Информация о подписке: /subscribe", parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard(),
        )

    elif data == "menu_help":
        await query.edit_message_text(format_help_message(), parse_mode="HTML",
            reply_markup=get_back_to_menu_keyboard())

    elif data == "menu_back":
        await query.edit_message_text(
            "📋 <b>Главное меню</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )


# Обработка смены статуса задачи
async def handle_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатия кнопки смены статуса задачи."""
    query = update.callback_query
    user = update.effective_user
    db: Database = context.bot_data["db"]

    # Парсим callback_data: status_{task_id}_{new_status}
    parts = query.data.split("_", 2)
    if len(parts) < 3:
        return

    task_id = int(parts[1])
    new_status = parts[2]

    # Получаем задачу
    task = db.get_task(task_id)
    if not task:
        await query.edit_message_text("❌ Задача не найдена.")
        return

    # Обновляем статус
    success = db.update_task_status(task_id, new_status)
    if not success:
        await query.edit_message_text("❌ Ошибка при изменении статуса.")
        return

    # Перезагружаем задачу для обновления
    task = db.get_task(task_id)
    team = db.get_user_active_team(user.id)
    role = db.get_member_role(team["team_id"], user.id) if team else None

    # Получаем имена
    assignee_name = "Не назначен"
    if task["assignee_id"]:
        assignee = db.get_user(task["assignee_id"])
        if assignee:
            assignee_name = assignee["first_name"] or assignee["username"] or "—"

    author = db.get_user(task["author_id"])
    author_name = author["first_name"] if author else "—"

    msg = format_task_message(dict(task), assignee_name, author_name)
    keyboard = get_task_keyboard(task_id, task["status"], role)

    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=keyboard)

    # Уведомляем автора о смене статуса (если это не сам автор)
    if task["author_id"] != user.id:
        changer_name = user.first_name or user.username or str(user.id)
        await notify_status_changed(
            context.bot, task["author_id"], dict(task), new_status, changer_name
        )

    logger.info("Статус задачи #%s изменён на '%s' пользователем %s", task_id, new_status, user.id)


# Обработка запроса на удаление задачи
async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрос подтверждения удаления задачи."""
    query = update.callback_query
    task_id = int(query.data.replace("delete_", ""))

    await query.edit_message_text(
        f"⚠️ <b>Удалить задачу #{task_id}?</b>\n\n"
        "Это действие необратимо!",
        parse_mode="HTML",
        reply_markup=get_delete_confirm_keyboard(task_id),
    )


# Обработка подтверждения удаления
async def handle_confirm_delete_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Удаление задачи после подтверждения."""
    query = update.callback_query
    db: Database = context.bot_data["db"]
    task_id = int(query.data.replace("confirm_delete_", ""))

    success = db.delete_task(task_id)
    if success:
        await query.edit_message_text(f"🗑 Задача #{task_id} удалена.")
    else:
        await query.edit_message_text("❌ Ошибка при удалении задачи.")


# Обработка отмены задачи (статус cancelled)
async def handle_cancel_task_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Отмена задачи (перевод в статус cancelled)."""
    query = update.callback_query
    db: Database = context.bot_data["db"]
    task_id = int(query.data.replace("cancel_", ""))

    db.update_task_status(task_id, "cancelled")
    await query.edit_message_text(
        f"❌ Задача #{task_id} отменена.\n\n"
        f"Посмотреть: /task {task_id}",
        parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard(),
    )


# Начало добавления комментария
async def handle_comment_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Начинает процесс добавления комментария к задаче."""
    query = update.callback_query
    task_id = int(query.data.replace("comment_", ""))

    # Сохраняем ID задачи для комментария
    context.user_data["comment_task_id"] = task_id

    await query.edit_message_text(
        f"💬 Введите комментарий к задаче #{task_id}:\n\n"
        "<i>Отмена: /cancel</i>",
        parse_mode="HTML",
    )


# Обработка текста комментария (вызывается из main.py)
async def comment_text_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Получение текста комментария и сохранение в БД."""
    task_id = context.user_data.get("comment_task_id")
    # Проверяем что ожидаем комментарий
    if not task_id:
        return

    user = update.effective_user
    db: Database = context.bot_data["db"]
    text = update.message.text.strip()

    # Проверяем длину
    if len(text) > 500:
        await update.message.reply_text("❌ Комментарий слишком длинный (макс. 500 символов).")
        return

    # Сохраняем комментарий
    db.add_comment(task_id, user.id, text)
    # Очищаем состояние
    del context.user_data["comment_task_id"]

    await update.message.reply_text(
        f"✅ Комментарий добавлен к задаче #{task_id}.\n\n"
        f"Посмотреть: /task {task_id}",
        parse_mode="HTML",
    )

    # Уведомляем участников задачи
    task = db.get_task(task_id)
    if task:
        from utils.notifications import notify_comment_added
        commenter_name = user.first_name or user.username or str(user.id)
        # Собираем ID получателей (автор и исполнитель, кроме комментатора)
        notify_ids = set()
        if task["author_id"] and task["author_id"] != user.id:
            notify_ids.add(task["author_id"])
        if task["assignee_id"] and task["assignee_id"] != user.id:
            notify_ids.add(task["assignee_id"])
        if notify_ids:
            await notify_comment_added(
                context.bot, list(notify_ids), dict(task), commenter_name, text
            )


# Обработка редактирования задачи (упрощённый вариант)
async def handle_edit_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Подсказка по редактированию задачи."""
    query = update.callback_query
    task_id = int(query.data.replace("edit_", ""))

    await query.edit_message_text(
        f"✏️ <b>Редактирование задачи #{task_id}</b>\n\n"
        "Отправьте текст в формате:\n"
        f"<code>/edit {task_id} название: Новое название</code>\n"
        f"<code>/edit {task_id} описание: Новое описание</code>\n"
        f"<code>/edit {task_id} дедлайн: ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
        f"Посмотреть: /task {task_id}",
        parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard(),
    )
