"""
Модуль генерации inline-клавиатур для Telegram-бота.
Все клавиатуры собраны в одном месте для удобства.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# Кнопка "Назад в главное меню"
def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой 'Назад в меню'."""
    keyboard = [
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Генерация главного меню
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню."""
    keyboard = [
        [InlineKeyboardButton("📝 Новая задача", callback_data="menu_newtask")],
        [
            InlineKeyboardButton("📋 Мои задачи", callback_data="menu_mytasks"),
            InlineKeyboardButton("📊 Все задачи", callback_data="menu_alltasks"),
        ],
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="menu_today"),
            InlineKeyboardButton("📆 Неделя", callback_data="menu_week"),
        ],
        [
            InlineKeyboardButton("👥 Команда", callback_data="menu_team"),
            InlineKeyboardButton("📈 Статистика", callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton("📅 Календарь", callback_data="menu_calendar"),
            InlineKeyboardButton("💎 Подписка", callback_data="menu_subscribe"),
        ],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Генерация клавиатуры задачи с кнопками статусов
def get_task_keyboard(
    task_id: int, current_status: str, user_role: str | None = None,
    add_back_button: bool = True,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления задачей.
    Кнопки зависят от текущего статуса и роли пользователя.
    """
    keyboard = []

    # Кнопки смены статуса в зависимости от текущего
    if current_status == "todo":
        keyboard.append(
            [InlineKeyboardButton("▶️ В работу", callback_data=f"status_{task_id}_in_progress")]
        )
    elif current_status == "in_progress":
        keyboard.append([
            InlineKeyboardButton("✅ Выполнено", callback_data=f"status_{task_id}_done"),
            InlineKeyboardButton("⏸ Вернуть", callback_data=f"status_{task_id}_todo"),
        ])
    elif current_status == "done":
        keyboard.append(
            [InlineKeyboardButton("🔄 Вернуть в работу", callback_data=f"status_{task_id}_in_progress")]
        )
    elif current_status == "cancelled":
        keyboard.append(
            [InlineKeyboardButton("🔄 Возобновить", callback_data=f"status_{task_id}_todo")]
        )

    # Кнопки действий
    action_row = [
        InlineKeyboardButton("💬 Комментарий", callback_data=f"comment_{task_id}"),
    ]

    # Редактирование и удаление доступно автору и админам
    if user_role in ("owner", "admin", None):
        action_row.append(
            InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_{task_id}")
        )

    keyboard.append(action_row)

    # Кнопка удаления отдельной строкой
    if user_role in ("owner", "admin", None):
        keyboard.append([
            InlineKeyboardButton("❌ Отменить задачу", callback_data=f"cancel_{task_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{task_id}"),
        ])

    # Кнопка возврата в меню
    if add_back_button:
        keyboard.append(
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        )

    return InlineKeyboardMarkup(keyboard)


# Клавиатура выбора приоритета
def get_priority_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора приоритета задачи."""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Низкий", callback_data="priority_low"),
            InlineKeyboardButton("🟡 Средний", callback_data="priority_medium"),
            InlineKeyboardButton("🔴 Высокий", callback_data="priority_high"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Клавиатура подтверждения создания задачи
def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Создать", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Отменить", callback_data="confirm_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Клавиатура выбора участника команды
def get_members_keyboard(
    members: list, action: str = "assign"
) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком участников команды.
    Используется для назначения исполнителя.
    """
    keyboard = []
    # Проходим по участникам и создаём кнопки
    for member in members:
        name = member["first_name"] or member["username"] or str(member["user_id"])
        role_badge = ""
        if member["role"] == "owner":
            role_badge = "👑 "
        elif member["role"] == "admin":
            role_badge = "⭐ "
        keyboard.append([
            InlineKeyboardButton(
                f"{role_badge}{name}",
                callback_data=f"{action}_{member['user_id']}",
            )
        ])
    # Кнопка "Без исполнителя"
    keyboard.append([
        InlineKeyboardButton("👤 Без исполнителя", callback_data=f"{action}_none")
    ])
    return InlineKeyboardMarkup(keyboard)


# Клавиатура пропуска шага
def get_skip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить'."""
    keyboard = [[InlineKeyboardButton("⏭ Пропустить", callback_data="skip")]]
    return InlineKeyboardMarkup(keyboard)


# Клавиатура подтверждения удаления
def get_delete_confirm_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления задачи."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{task_id}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"cancel_delete_{task_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Клавиатура тарифных планов
def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с доступными тарифами."""
    keyboard = [
        [InlineKeyboardButton("💎 Pro — ₽299/мес", callback_data="sub_pro")],
        [InlineKeyboardButton("🏢 Enterprise", callback_data="sub_enterprise")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Клавиатура навигации списка задач
def get_tasks_list_keyboard(
    page: int = 0, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Клавиатура пагинации для длинных списков задач."""
    keyboard = []
    nav_row = []
    # Проверяем есть ли предыдущая страница
    if page > 0:
        nav_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page - 1}")
        )
    # Проверяем есть ли следующая страница
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton("➡️ Далее", callback_data=f"page_{page + 1}")
        )
    if nav_row:
        keyboard.append(nav_row)
    # Добавляем кнопку возврата в меню
    keyboard.append(
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
    )
    return InlineKeyboardMarkup(keyboard)


# Клавиатура выбора команды
def get_teams_keyboard(teams: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора команды из списка."""
    keyboard = []
    # Проходим по командам пользователя
    for team in teams:
        keyboard.append([
            InlineKeyboardButton(
                f"👥 {team['name']}", callback_data=f"select_team_{team['team_id']}"
            )
        ])
    return InlineKeyboardMarkup(keyboard)
