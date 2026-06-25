from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню пользователя"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Открыть сундук", callback_data="open_chest")
    builder.button(text="📜 История", callback_data="history")
    builder.button(text="👑 Админ-панель", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def admin_menu() -> InlineKeyboardMarkup:
    """Меню администратора"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Ожидают подтверждения", callback_data="admin_pending")
    builder.button(text="🎁 Управление призами", callback_data="admin_prizes")
    builder.button(text="🔑 Выдать ключи", callback_data="admin_give_keys")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📋 Не выданные призы", callback_data="admin_undelivered")
    builder.button(text="⚙️ Настройки", callback_data="admin_settings")
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()


def back_button() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="back")
    return builder.as_markup()


def registration_confirmation() -> InlineKeyboardMarkup:
    """Кнопки подтверждения регистрации"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="reg_confirm")
    builder.button(text="❌ Отклонить", callback_data="reg_reject")
    builder.adjust(1)
    return builder.as_markup()


def prize_management_buttons() -> InlineKeyboardMarkup:
    """Кнопки управления призами"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить приз", callback_data="prize_add")
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()


def get_users_list(users: list, prefix: str) -> InlineKeyboardMarkup:
    """Список пользователей для выбора"""
    builder = InlineKeyboardBuilder()
    for user in users:
        builder.button(
            text=f"👤 {user['name']}",
            callback_data=f"{prefix}_{user['telegram_id']}"
        )
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    return builder.as_markup()