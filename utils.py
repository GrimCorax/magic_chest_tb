import sys
import os
from datetime import datetime
from loguru import logger

from config import LOG_LEVEL


def setup_logging() -> None:
    """Настройка логирования"""
    os.makedirs('logs', exist_ok=True)
    
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Вывод в консоль
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL
    )
    
    # Вывод в файл
    logger.add(
        "logs/bot.log",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG"
    )
    
    logger.info(f"✅ Логирование настроено (уровень: {LOG_LEVEL})")


def is_admin(telegram_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    from config import ADMIN_IDS
    return telegram_id in ADMIN_IDS


def format_datetime(dt_str: str) -> str:
    """Форматирование даты"""
    try:
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%d.%m.%Y %H:%M')
    except (ValueError, TypeError):
        return dt_str


def safe_get(data: dict, key: str, default=None):
    """Безопасное получение значения из словаря"""
    return data.get(key, default)

def chest_opening_animation() -> str:
    """Анимация открытия сундука"""
    return (
        "🎁 *Открываем сундук...*\n\n"
        "🔓 Ключ подходит...\n"
        "⚙️ Механизмы активируются...\n"
        "💫 Магия оживает...\n\n"
        "✨ *Вот что внутри!*"
    )