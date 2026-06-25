#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import signal
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config import BOT_TOKEN, ADMIN_IDS, BACKUP_INTERVAL
from database import backup_database
from handlers import router
from utils import setup_logging

# Настройка логирования
setup_logging()

# Проверка наличия токена
if not BOT_TOKEN:
    logger.critical("❌ BOT_TOKEN не задан в .env файле!")
    sys.exit(1)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация обработчиков
dp.include_router(router)

# Глобальная ссылка на планировщик для graceful shutdown
scheduler: Optional[AsyncIOScheduler] = None


async def setup_commands() -> None:
    """Настройка команд бота"""
    commands = [
        BotCommand(command="/start", description="Начать работу"),
        BotCommand(command="/admin", description="Админ-панель"),
        BotCommand(command="/help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)


async def scheduled_backup() -> None:
    """Плановое резервное копирование"""
    try:
        backup_database()
        logger.debug("✅ Плановый бэкап выполнен")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании бэкапа: {e}")


async def shutdown() -> None:
    """Graceful shutdown"""
    logger.info("🛑 Завершение работы бота...")
    if scheduler:
        scheduler.shutdown()
    await bot.session.close()
    logger.info("✅ Бот остановлен")


def handle_shutdown(signum, frame) -> None:
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"Получен сигнал {signum}")
    asyncio.create_task(shutdown())


async def main() -> None:
    """Главная функция"""
    global scheduler
    
    logger.info("🚀 Запуск бота Magic Chest...")
    logger.info(f"📅 Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🆔 Администраторы: {ADMIN_IDS}")
    
    # Настройка команд
    await setup_commands()
    
    # Настройка планировщика для бэкапов
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_backup,
        trigger=IntervalTrigger(hours=BACKUP_INTERVAL),
        id="backup_job",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"⏰ Планировщик бэкапов запущен (каждые {BACKUP_INTERVAL} ч.)")
    
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    logger.info("✅ Бот запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"❌ Необработанная ошибка: {e}")
        sys.exit(1)