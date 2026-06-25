from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any

from database import get_active_keys_count, get_user_by_telegram_id


def main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню пользователя"""
    user = get_user_by_telegram_id(user_id)
    if not user or user['status'] != 'active':
        return None
    
    keys_count = get_active_keys_count(user['id'])
    
    builder = InlineKeyboardBuilder()
    
    if keys_count > 0:
        builder.button(text=f"🗝 Открыть сундук ({keys_count})", callback_data="open_chest")
    else:
        builder.button(text="🔒 Сундук закрыт", callback_data="no_keys")
    
    builder.button(text="📜 История получения призов", callback_data="history")
    builder.adjust(1)
    
    return builder.as_markup()


def admin_menu() -> InlineKeyboardMarkup:
    """Админ-меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Подтверждение регистраций", callback_data="admin_pending")
    builder.button(text="🎁 Управление призами", callback_data="admin_prizes")
    builder.button(text="🔑 Выдать ключи", callback_data="admin_give_keys")
    builder.button(text="📊 Статистика пользователей", callback_data="admin_stats")
    builder.button(text="📋 Не выданные призы", callback_data="admin_undelivered")
    builder.button(text="⚙️ Настройки", callback_data="admin_settings")
    builder.adjust(1)
    return builder.as_markup()


def registration_confirmation() -> InlineKeyboardMarkup:
    """Кнопки подтверждения регистрации"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="reg_confirm")
    builder.button(text="❌ Отказать", callback_data="reg_reject")
    builder.adjust(2)
    return builder.as_markup()


def chest_opening_animation() -> str:
    """Текстовая анимация открытия сундука"""
    return """
🗝 Сундук открывается...
⚡️ 3...
⚡️ 2...
⚡️ 1...
✨ *Вжух!* ✨
    """


def back_button() -> InlineKeyboardMarkup:
    """Кнопка Назад"""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="back")
    return builder.as_markup()


def prize_management_buttons() -> InlineKeyboardMarkup:
    """Кнопки управления призами"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить приз", callback_data="prize_add")
    builder.button(text="✏️ Редактировать приз", callback_data="prize_edit")
    builder.button(text="🗑 Удалить приз", callback_data="prize_delete")
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()


def get_users_list(users: list, prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user in users:
        builder.button(
            text=f"👤 {user['name']}",
            callback_data=f"{prefix}_{user['telegram_id']}"  # ← Telegram ID
        )
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()


def get_prizes_list(prizes: List[Dict[str, Any]], action: str) -> InlineKeyboardMarkup:
    """Список призов для выбора"""
    builder = InlineKeyboardBuilder()
    for prize in prizes[:20]:
        status = "✅" if prize['is_active'] else "❌"
        builder.button(
            text=f"{status} {prize['name']} (вес:{prize['weight']})",
            callback_data=f"{action}_{prize['id']}"
        )
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()