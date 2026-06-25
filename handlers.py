import re
from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from config import ADMIN_IDS
from database import *
from keyboards import *
from utils import *

router = Router()

# === КОНСТАНТЫ ===
MAX_KEYS_PER_ISSUE = 100
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 50


# === СОСТОЯНИЯ ===

class RegistrationStates(StatesGroup):
    waiting_for_name = State()


class PrizeAddStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_weight = State()
    waiting_for_limit = State()


class PrizeEditStates(StatesGroup):
    waiting_for_prize_id = State()
    waiting_for_weight = State()
    waiting_for_limit = State()


class GiveKeysStates(StatesGroup):
    waiting_for_user = State()
    waiting_for_count = State()


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def is_admin(telegram_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return telegram_id in ADMIN_IDS


async def safe_edit_message(callback: CallbackQuery, text: str, **kwargs) -> None:
    """Безопасное редактирование сообщения"""
    try:
        await callback.message.edit_text(text, **kwargs)
    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")
        await callback.answer("⚠️ Обновите страницу")


async def show_main_menu(message: Message, user: Dict[str, Any]) -> None:
    """Показать главное меню пользователя"""
    keyboard = main_menu(message.from_user.id)
    if not keyboard:
        await message.answer("❌ Ошибка загрузки меню")
        return
    
    keys_count = get_active_keys_count(user['id'])
    
    await message.answer(
        f"🏠 *Главное меню*\n\n"
        f"💡 У вас активных ключей: *{keys_count}*\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_admin_panel(callback: CallbackQuery) -> None:
    """Показать админ-панель"""
    pending_users = get_pending_users()
    pending_count = len(pending_users)
    
    await callback.message.edit_text(
        f"👑 *Админ-панель*\n\n"
        f"📝 Ожидают подтверждения: *{pending_count}*\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )


# === ОБРАБОТЧИКИ КОМАНД ===

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start"""
    user = get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer(
            "🎉 *Добро пожаловать в Magic Chest!*\n\n"
            "Для начала работы пройдите регистрацию.\n"
            f"Пожалуйста, введите ваше *уникальное имя* (от {MIN_NAME_LENGTH} до {MAX_NAME_LENGTH} символов):",
            parse_mode="Markdown"
        )
        await state.set_state(RegistrationStates.waiting_for_name)
        return
    
    if user['status'] == 'pending':
        await message.answer(
            "⏳ Ваша заявка на регистрацию ожидает подтверждения администратором.\n"
            "Пожалуйста, подождите."
        )
        return
    
    if user['status'] == 'blocked':
        await message.answer(
            "🚫 Ваш аккаунт заблокирован. Обратитесь к администратору."
        )
        return
    
    await show_main_menu(message, user)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """Обработчик команды /admin"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    pending_users = get_pending_users()
    pending_count = len(pending_users)
    
    await message.answer(
        f"👑 *Админ-панель*\n\n"
        f"📝 Ожидают подтверждения: *{pending_count}*\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )


# === РЕГИСТРАЦИЯ ===

@router.message(RegistrationStates.waiting_for_name)
async def process_registration_name(message: Message, state: FSMContext) -> None:
    """Обработка ввода имени при регистрации"""
    name = message.text.strip()
    
    if not name or len(name) < MIN_NAME_LENGTH:
        await message.answer(f"❌ Имя должно содержать минимум {MIN_NAME_LENGTH} символа. Попробуйте еще раз:")
        return
    
    if len(name) > MAX_NAME_LENGTH:
        await message.answer(f"❌ Имя не должно превышать {MAX_NAME_LENGTH} символов. Попробуйте еще раз:")
        return
    
    if not re.match(r'^[a-zA-Zа-яА-Я0-9_\s]+$', name):
        await message.answer("❌ Имя содержит недопустимые символы. Используйте буквы, цифры и пробелы.")
        return
    
    if not is_name_available(name):
        await message.answer(f"❌ Имя *{name}* уже занято. Пожалуйста, выберите другое имя:", parse_mode="Markdown")
        return
    
    if add_user(message.from_user.id, name):
        admin_message = (
            f"📝 *Новая заявка на регистрацию!*\n\n"
            f"👤 Имя: *{name}*\n"
            f"🆔 Telegram ID: `{message.from_user.id}`\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    admin_message,
                    parse_mode="Markdown",
                    reply_markup=registration_confirmation()
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        
        await message.answer(
            "✅ Вы успешно зарегистрированы!\n\n"
            "⏳ Ваша заявка отправлена на подтверждение администратору.\n"
            "Пожалуйста, ожидайте подтверждения."
        )
        await state.clear()
    else:
        await message.answer("❌ Произошла ошибка при регистрации. Попробуйте позже.")


# === ОБРАБОТЧИКИ КНОПОК ОСНОВНОГО МЕНЮ ===

@router.callback_query(F.data == "open_chest")
async def callback_open_chest(callback: CallbackQuery) -> None:
    """Открыть сундук"""
    try:
        user = get_user_by_telegram_id(callback.from_user.id)
        if not user or user['status'] != 'active':
            await callback.answer("❌ Ошибка доступа")
            return
        
        keys_count = get_active_keys_count(user['id'])
        if keys_count == 0:
            await callback.answer("❌ У вас нет активных ключей!", show_alert=True)
            return
        
        await callback.message.edit_text(
            chest_opening_animation(),
            parse_mode="Markdown"
        )
        
        prize = get_prize_by_weight(user['id'])
        if not prize:
            await callback.message.answer(
                "😔 В этом месяце вы уже получили все доступные призы.\n"
                "Попробуйте в следующем месяце!",
                reply_markup=main_menu(callback.from_user.id)
            )
            return
        
        key_id = use_key(user['id'])
        if not key_id:
            await callback.message.answer("❌ Ошибка: ключ не найден")
            return
        
        add_prize_history(
            user['id'], user['name'],
            prize['id'], prize['name'],
            key_id, 0, "Система"
        )
        
        await callback.message.answer(
            f"🎉 *Поздравляем!*\n\n"
            f"В сундуке вы нашли *{prize['name']}*! 🎁",
            parse_mode="Markdown"
        )
        
        admin_notify = (
            f"📦 *Нужно выдать приз!*\n\n"
            f"👤 Пользователь: *{user['name']}*\n"
            f"🎁 Приз: *{prize['name']}*\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await callback.bot.send_message(admin_id, admin_notify, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Не удалось уведомить админа {admin_id}: {e}")
        
        await callback.message.answer(
            "🏠 *Главное меню*",
            parse_mode="Markdown",
            reply_markup=main_menu(callback.from_user.id)
        )
    except Exception as e:
        logger.error(f"Ошибка при открытии сундука: {e}")
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data == "history")
async def callback_history(callback: CallbackQuery) -> None:
    """Показать историю призов пользователя"""
    user = get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Ошибка доступа")
        return
    
    history = get_user_history_by_month(user['id'])
    
    if not history:
        await callback.message.edit_text(
            "📜 *История получения призов*\n\n"
            "😔 Вы еще не получали призов.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        return
    
    text = "📜 *Ваша история получения призов:*\n\n"
    for month, prizes in history.items():
        text += f"📅 *{month}*\n"
        for prize_name, data in prizes.items():
            delivered_status = "✅ получен" if data['delivered'] == data['count'] else f"❌ не получен ({data['delivered']}/{data['count']})"
            text += f"🎁 {prize_name} — {data['count']} раз ({delivered_status})\n"
        text += "\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_button()
    )


@router.callback_query(F.data == "back")
async def callback_back(callback: CallbackQuery) -> None:
    """Назад"""
    try:
        if is_admin(callback.from_user.id):
            await show_admin_panel(callback)
            return
        
        user = get_user_by_telegram_id(callback.from_user.id)
        if not user or user['status'] != 'active':
            await callback.answer("❌ Ошибка доступа")
            return
        
        await callback.message.edit_text(
            "🏠 *Главное меню*",
            parse_mode="Markdown",
            reply_markup=main_menu(callback.from_user.id)
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате: {e}")
        await callback.answer("❌ Произошла ошибка")


# === ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ ===

@router.callback_query(F.data.startswith("reg_"))
async def callback_confirm_registration(callback: CallbackQuery) -> None:
    """Подтверждение или отклонение регистрации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    try:
        action = callback.data.split("_")[1]
        
        text = callback.message.text
        match = re.search(r'🆔 Telegram ID: `(\d+)`', text)
        if not match:
            await callback.answer("❌ Не удалось определить пользователя")
            return
        
        telegram_id = int(match.group(1))
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        if action == "confirm":
            update_user_status(telegram_id, 'active')
            await callback.message.edit_text(
                f"✅ Подтверждено!\n\n"
                f"Пользователь *{user['name']}* успешно зарегистрирован.",
                parse_mode="Markdown"
            )
            
            try:
                await callback.bot.send_message(
                    telegram_id,
                    "🎉 *Поздравляем!*\n\n"
                    "Ваша регистрация в Magic Chest подтверждена!\n"
                    "Теперь вы можете участвовать и получать призы!",
                    parse_mode="Markdown",
                    reply_markup=main_menu(telegram_id)
                )
            except Exception as e:
                logger.error(f"Не удалось уведомить пользователя {telegram_id}: {e}")
        else:
            update_user_status(telegram_id, 'blocked')
            await callback.message.edit_text(
                f"❌ Отклонено!\n\n"
                f"Пользователь *{user['name']}* отклонен.",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Ошибка при подтверждении регистрации: {e}")
        await callback.answer("❌ Произошла ошибка")


# === АДМИН-ПАНЕЛЬ ===

@router.callback_query(F.data == "admin_pending")
async def callback_admin_pending(callback: CallbackQuery) -> None:
    """Показать ожидающие регистрации"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    pending_users = get_pending_users()
    
    if not pending_users:
        await callback.message.edit_text(
            "📝 *Ожидающие подтверждения*\n\n"
            "✅ Нет заявок на подтверждение.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        return
    
    builder = InlineKeyboardBuilder()
    for user in pending_users:
        builder.button(
            text=f"👤 {user['name']}",
            callback_data=f"confirm_user_{user['telegram_id']}"
        )
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📝 *Ожидающие подтверждения:*\n\n"
        "Нажмите на пользователя для подтверждения:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("confirm_user_"))
async def callback_confirm_user(callback: CallbackQuery) -> None:
    """Подтвердить пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    telegram_id = int(callback.data.split("_")[2])
    user = get_user_by_telegram_id(telegram_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    if user['status'] == 'active':
        await callback.answer("✅ Пользователь уже подтвержден")
        return
    
    update_user_status(telegram_id, 'active')
    
    await callback.message.edit_text(
        f"✅ *Пользователь подтвержден!*\n\n"
        f"👤 Имя: *{user['name']}*\n"
        f"🆔 ID: {user['telegram_id']}\n"
        f"📅 Дата: {user['registered_at']}",
        parse_mode="Markdown",
        reply_markup=back_button()
    )
    
    try:
        await callback.bot.send_message(
            telegram_id,
            "🎉 *Поздравляем!*\n\n"
            "Ваша регистрация в Magic Chest подтверждена!\n"
            "Теперь вы можете участвовать и получать призы!",
            parse_mode="Markdown",
            reply_markup=main_menu(telegram_id)
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {telegram_id}: {e}")


# === УПРАВЛЕНИЕ ПРИЗАМИ ===

@router.callback_query(F.data == "admin_prizes")
async def callback_admin_prizes(callback: CallbackQuery) -> None:
    """Управление призами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    prizes = get_all_prizes(active_only=False)
    
    text = "🎁 *Управление призами*\n\n"
    if prizes:
        for prize in prizes:
            status = "✅ активен" if prize['is_active'] else "❌ неактивен"
            text += f"• {prize['name']} (вес: {prize['weight']}, лимит: {prize['monthly_limit']}/мес) - {status}\n"
    else:
        text += "😔 Призов пока нет.\n"
    
    text += "\nВыберите действие:"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=prize_management_buttons()
    )


@router.callback_query(F.data == "prize_add")
async def callback_prize_add(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало добавления приза"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "➕ *Добавление нового приза*\n\n"
        "Введите *название* приза:",
        parse_mode="Markdown",
        reply_markup=back_button()
    )
    await state.set_state(PrizeAddStates.waiting_for_name)


@router.message(PrizeAddStates.waiting_for_name)
async def process_prize_name(message: Message, state: FSMContext) -> None:
    """Обработка названия приза"""
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым. Попробуйте снова:")
        return
    
    if len(name) > 100:
        await message.answer("❌ Название слишком длинное (максимум 100 символов):")
        return
    
    if get_prize_by_name(name):
        await message.answer(f"❌ Приз с названием *{name}* уже существует. Введите другое название:", parse_mode="Markdown")
        return
    
    await state.update_data(prize_name=name)
    await message.answer(
        f"✅ Название: *{name}*\n\n"
        "Теперь введите *вес* (шанс выпадения, целое число, чем больше, тем выше шанс):",
        parse_mode="Markdown"
    )
    await state.set_state(PrizeAddStates.waiting_for_weight)


@router.message(PrizeAddStates.waiting_for_weight)
async def process_prize_weight(message: Message, state: FSMContext) -> None:
    """Обработка веса приза"""
    try:
        weight = int(message.text.strip())
        if weight <= 0:
            await message.answer("❌ Вес должен быть положительным числом. Попробуйте снова:")
            return
        if weight > 10000:
            await message.answer("❌ Вес не может превышать 10000:")
            return
    except ValueError:
        await message.answer("❌ Введите целое число (например, 10):")
        return
    
    await state.update_data(prize_weight=weight)
    await message.answer(
        f"✅ Вес: *{weight}*\n\n"
        "Теперь введите *максимальное количество* в месяц для одного пользователя:",
        parse_mode="Markdown"
    )
    await state.set_state(PrizeAddStates.waiting_for_limit)


@router.message(PrizeAddStates.waiting_for_limit)
async def process_prize_limit(message: Message, state: FSMContext) -> None:
    """Обработка лимита приза"""
    try:
        limit = int(message.text.strip())
        if limit < 0:
            await message.answer("❌ Лимит не может быть отрицательным. Попробуйте снова:")
            return
        if limit > 999999:
            await message.answer("❌ Лимит не может превышать 999999:")
            return
    except ValueError:
        await message.answer("❌ Введите целое число (например, 5):")
        return
    
    data = await state.get_data()
    name = data.get('prize_name')
    weight = data.get('prize_weight')
    
    success = add_prize(name, weight, limit)
    if success:
        await message.answer(
            f"✅ *Приз успешно добавлен!*\n\n"
            f"📌 Название: *{name}*\n"
            f"⚖️ Вес: *{weight}*\n"
            f"📅 Лимит в месяц: *{limit}*\n",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
    else:
        await message.answer("❌ Ошибка при добавлении приза.", reply_markup=back_button())
    
    await state.clear()


# === ВЫДАЧА КЛЮЧЕЙ ===

@router.callback_query(F.data == "admin_give_keys")
async def callback_admin_give_keys(callback: CallbackQuery, state: FSMContext) -> None:
    """Выдача ключей — выбор пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    users = get_all_users('active')
    if not users:
        await callback.message.edit_text(
            "🔑 *Выдача ключей*\n\n"
            "😔 Нет активных пользователей.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        return
    
    await callback.message.edit_text(
        "🔑 *Выдача ключей*\n\n"
        "Выберите пользователя:",
        parse_mode="Markdown",
        reply_markup=get_users_list(users, "give_keys")
    )


@router.callback_query(F.data.startswith("give_keys_"))
async def callback_give_keys_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор пользователя для выдачи ключей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    telegram_id = int(callback.data.split("_")[2])
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    await state.update_data(give_user_id=user['id'], give_user_name=user['name'])
    
    await callback.message.edit_text(
        f"🔑 *Выдача ключей*\n\n"
        f"👤 Пользователь: *{user['name']}*\n\n"
        f"Введите количество ключей для выдачи (1-{MAX_KEYS_PER_ISSUE}):",
        parse_mode="Markdown",
        reply_markup=back_button()
    )
    await state.set_state(GiveKeysStates.waiting_for_count)


@router.message(GiveKeysStates.waiting_for_count)
async def process_give_keys_count(message: Message, state: FSMContext) -> None:
    """Обработка количества ключей"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен")
        return
    
    try:
        count = int(message.text.strip())
        if count <= 0:
            await message.answer("❌ Количество должно быть больше 0")
            return
        if count > MAX_KEYS_PER_ISSUE:
            await message.answer(f"❌ Слишком много ключей (максимум {MAX_KEYS_PER_ISSUE})")
            return
    except ValueError:
        await message.answer("❌ Введите число")
        return
    
    data = await state.get_data()
    user_id = data.get('give_user_id')
    user_name = data.get('give_user_name')
    
    if not user_id:
        await message.answer("❌ Ошибка: пользователь не выбран")
        await state.clear()
        return
    
    admin_name = message.from_user.first_name or "Админ"
    added = add_keys(user_id, message.from_user.id, admin_name, count)
    
    user = get_user_by_id(user_id)
    if user:
        try:
            active_keys = get_active_keys_count(user_id)
            await message.bot.send_message(
                user['telegram_id'],
                f"🔑 *Вам выдан ключ от Магического сундука!*\n\n"
                f"👤 Администратор: {admin_name}\n"
                f"📦 Количество ключей: {count}\n"
                f"🔑 Всего активных ключей: {active_keys}\n\n"
                f"Откройте сундук в главном меню! 🎁",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")
    
    await message.answer(
        f"✅ *Ключи выданы!*\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"📦 Количество: {count}\n"
        f"✅ Всего добавлено: {added} ключей",
        parse_mode="Markdown",
        reply_markup=back_button()
    )
    await state.clear()


# === СТАТИСТИКА ===

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery) -> None:
    """Статистика — выбор пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    users = get_all_users('active')
    if not users:
        await callback.message.edit_text(
            "📊 *Статистика пользователей*\n\n"
            "😔 Нет активных пользователей.",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        return
    
    await callback.message.edit_text(
        "📊 *Статистика пользователей*\n\n"
        "Выберите пользователя:",
        parse_mode="Markdown",
        reply_markup=get_users_list(users, "stats")
    )


@router.callback_query(F.data.startswith("stats_"))
async def callback_stats_user(callback: CallbackQuery) -> None:
    """Показать статистику пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    telegram_id = int(callback.data.split("_")[1])
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    history = get_user_history_by_month(user['id'])
    stats = get_user_total_stats(user['id'])
    
    text = f"📊 *Статистика пользователя*\n\n"
    text += f"👤 *{user['name']}*\n"
    text += f"🔑 Активных ключей: {stats['active_keys']}\n"
    text += f"📦 Невыданных призов: {stats['undelivered']}\n"
    text += f"🎁 Всего получено: {stats['total_prizes']}\n\n"
    
    if history:
        for month, prizes in history.items():
            text += f"📅 *{month}*\n"
            for prize_name, data in prizes.items():
                delivered_status = "✅ получен" if data['delivered'] == data['count'] else f"❌ не получен ({data['delivered']}/{data['count']})"
                text += f"🎁 {prize_name} — {data['count']} раз ({delivered_status})\n"
            text += "\n"
    else:
        text += "😔 Пользователь еще не получал призов."
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_button()
    )


# === НЕ ВЫДАННЫЕ ПРИЗЫ ===

@router.callback_query(F.data == "admin_undelivered")
async def callback_admin_undelivered(callback: CallbackQuery) -> None:
    """Список пользователей с невыданными призами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    undelivered = get_undelivered_prizes()

    if not undelivered:
        await callback.message.edit_text(
            "📋 *Не выданные призы*\n\n"
            "✅ Все призы выданы!",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        return

    # Получаем соответствие имя → ID пользователя
    from database import get_all_users
    all_users = get_all_users('active')
    users_map = {user['name']: user['id'] for user in all_users}

    builder = InlineKeyboardBuilder()
    for user_name, prizes in undelivered.items():
        total = sum(prizes.values())
        user_id = users_map.get(user_name)
        if user_id is None:
            # Если пользователь не найден, пропускаем
            continue
        builder.button(
            text=f"👤 {user_name} ({total} шт)",
            callback_data=f"undelivered_user_{user_id}"
        )
    builder.button(text="◀️ Назад", callback_data="back")
    builder.adjust(1)

    await callback.message.edit_text(
        "📋 *Не выданные призы*\n\n"
        "Выберите пользователя:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("undelivered_user_"))
async def callback_undelivered_user_prizes(callback: CallbackQuery) -> None:
    """Список невыданных призов пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return

    # Получаем ID пользователя из callback_data
    user_id = int(callback.data.replace("undelivered_user_", ""))

    # Находим пользователя по ID
    from database import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return

    user_name = user['name']
    undelivered = get_undelivered_prizes()

    if user_name not in undelivered or not undelivered[user_name]:
        await callback.message.edit_text(
            f"📋 *Не выданные призы*\n\n"
            f"👤 {user_name}\n"
            f"✅ Все призы выданы!",
            parse_mode="Markdown",
            reply_markup=back_button()
        )
        return

    builder = InlineKeyboardBuilder()
    for prize_name, count in undelivered[user_name].items():
        builder.button(
            text=f"🎁 {prize_name} — {count} шт",
            callback_data=f"mark_delivered_{user_name}_{prize_name}"
        )
    builder.button(text="◀️ Назад", callback_data="admin_undelivered")
    builder.adjust(1)

    await callback.message.edit_text(
        f"📋 *Не выданные призы*\n\n"
        f"👤 *{user_name}*\n\n"
        f"Выберите приз, чтобы отметить как выданный:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("mark_delivered_"))
async def callback_mark_delivered(callback: CallbackQuery) -> None:
    """Отметить приз как выданный"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    parts = callback.data.split("_")
    user_name = parts[2]
    prize_name = "_".join(parts[3:])
    
    updated = mark_as_delivered(user_name, prize_name)
    
    if updated > 0:
        await callback.answer(f"✅ Отмечено {updated} шт как выданные!")
        undelivered = get_undelivered_prizes()
        
        if user_name in undelivered and undelivered[user_name]:
            builder = InlineKeyboardBuilder()
            for p_name, count in undelivered[user_name].items():
                builder.button(
                    text=f"🎁 {p_name} — {count} шт",
                    callback_data=f"mark_delivered_{user_name}_{p_name}"
                )
            builder.button(text="◀️ Назад", callback_data="admin_undelivered")
            builder.adjust(1)
            
            await callback.message.edit_text(
                f"📋 *Не выданные призы*\n\n"
                f"👤 *{user_name}*\n\n"
                f"✅ Отмечено как выданное: *{prize_name}* ({updated} шт)\n\n"
                f"Остались:",
                parse_mode="Markdown",
                reply_markup=builder.as_markup()
            )
        else:
            await callback.message.edit_text(
                f"📋 *Не выданные призы*\n\n"
                f"👤 *{user_name}*\n"
                f"✅ Все призы выданы! 🎉",
                parse_mode="Markdown",
                reply_markup=back_button()
            )
    else:
        await callback.answer("❌ Ничего не найдено для отметки")


# === НАСТРОЙКИ ===

@router.callback_query(F.data == "admin_settings")
async def callback_admin_settings(callback: CallbackQuery) -> None:
    """Настройки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен")
        return
    
    text = (
        "⚙️ *Настройки*\n\n"
        f"👑 Администраторы: {ADMIN_IDS}\n"
        f"📅 Текущее время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        "🔄 *Доступные действия:*\n"
        "• Добавление/редактирование призов\n"
        "• Выдача ключей пользователям\n"
        "• Просмотр статистики\n"
        "• Управление невыданными призами"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_button()
    )


@router.callback_query(F.data == "no_keys")
async def callback_no_keys(callback: CallbackQuery) -> None:
    """Нет ключей"""
    await callback.answer("🔒 У вас нет активных ключей!", show_alert=True)


logger.info("✅ Handlers initialized")