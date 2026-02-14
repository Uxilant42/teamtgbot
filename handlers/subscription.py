"""
Обработчики команд подписки.
/subscribe, /upgrade, /billing
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import Database
from config import SUBSCRIPTION_LIMITS, SUBSCRIPTION_PRICES
from utils.keyboards import get_subscription_keyboard

logger = logging.getLogger(__name__)


# Обработчик команды /subscribe — информация о тарифах
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ информации о тарифных планах."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    current_plan = team["subscription_type"] if team else "free"

    free = SUBSCRIPTION_LIMITS["free"]
    pro = SUBSCRIPTION_LIMITS["pro"]

    msg = (
        "💎 <b>Тарифные планы</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{'✅' if current_plan == 'free' else '⚪️'} <b>FREE (Бесплатно)</b>\n"
        f"  • До {free['max_members']} участников\n"
        f"  • До {free['max_tasks']} активных задач\n"
        f"  • Базовые напоминания\n"
        f"  • Стандартная поддержка\n\n"
        f"{'✅' if current_plan == 'pro' else '⚪️'} <b>PRO ({SUBSCRIPTION_PRICES['pro']})</b>\n"
        f"  • До {pro['max_members']} участников\n"
        f"  • Неограниченные задачи\n"
        f"  • Все типы напоминаний\n"
        f"  • Экспорт в календарь\n"
        f"  • Полная аналитика\n"
        f"  • Приоритетная поддержка\n\n"
        f"🏢 <b>ENTERPRISE ({SUBSCRIPTION_PRICES['enterprise']})</b>\n"
        f"  • Неограниченные участники\n"
        f"  • Неограниченные задачи\n"
        f"  • API для интеграций\n"
        f"  • Персональный менеджер\n\n"
        f"📌 Ваш текущий план: <b>{current_plan.upper()}</b>"
    )

    await update.message.reply_text(
        msg, parse_mode="HTML", reply_markup=get_subscription_keyboard()
    )


# Обработчик команды /upgrade — обновление плана
async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Информация об обновлении плана."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    # Проверяем что пользователь — владелец
    if team["owner_id"] != user.id:
        await update.message.reply_text("❌ Только владелец команды может менять подписку.")
        return

    current = team["subscription_type"]
    if current == "pro":
        await update.message.reply_text("✅ У вас уже Pro-план!")
        return

    msg = (
        "💎 <b>Обновление до Pro</b>\n\n"
        f"Цена: <b>{SUBSCRIPTION_PRICES['pro']}</b>\n\n"
        "Что вы получите:\n"
        "  ✅ До 15 участников\n"
        "  ✅ Неограниченные задачи\n"
        "  ✅ Все напоминания\n"
        "  ✅ Экспорт календаря\n"
        "  ✅ Полная аналитика\n\n"
        "📩 Для оплаты свяжитесь: @admin\n"
        "<i>(Интеграция платежей в разработке)</i>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


# Обработчик команды /billing — текущая подписка
async def billing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Информация о текущей подписке команды."""
    user = update.effective_user
    db: Database = context.bot_data["db"]

    team = db.get_user_active_team(user.id)
    if not team:
        await update.message.reply_text("❌ Вы не состоите в команде.")
        return

    plan = team["subscription_type"]
    limits = SUBSCRIPTION_LIMITS.get(plan, SUBSCRIPTION_LIMITS["free"])
    active_tasks = db.get_active_tasks_count(team["team_id"])
    member_count = db.get_team_member_count(team["team_id"])

    msg = (
        "💳 <b>Текущая подписка</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Команда: <b>{team['name']}</b>\n"
        f"💎 План: <b>{plan.upper()}</b>\n\n"
        f"<b>Использование:</b>\n"
        f"  👤 Участники: {member_count}/{limits['max_members']}\n"
        f"  📝 Активные задачи: {active_tasks}/{limits['max_tasks']}\n"
    )

    # Показываем срок действия для платных планов
    if team.get("subscription_expires"):
        msg += f"\n📅 Действует до: {team['subscription_expires'][:10]}\n"

    await update.message.reply_text(msg, parse_mode="HTML")
