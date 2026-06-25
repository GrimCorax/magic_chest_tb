import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


def get_env_var(name: str, default: Optional[str] = None, required: bool = True) -> str:
    """Безопасное получение переменной окружения"""
    value = os.getenv(name, default)
    if required and value is None:
        raise ValueError(f"❌ Обязательная переменная {name} не задана в .env")
    return value


# === ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ===
BOT_TOKEN: str = get_env_var('BOT_TOKEN')

# === АДМИНИСТРАТОРЫ ===
ADMIN_IDS_RAW: str = get_env_var('ADMIN_IDS', '')
ADMIN_IDS: List[int] = [int(id.strip()) for id in ADMIN_IDS_RAW.split(',') if id.strip()]
if not ADMIN_IDS:
    raise ValueError("❌ ADMIN_IDS не может быть пустым! Укажите хотя бы одного администратора.")

# === НАСТРОЙКИ БАЗЫ ДАННЫХ ===
DATABASE_PATH: str = get_env_var('DATABASE_PATH', 'data/magic_chest.db', required=False)
BACKUP_PATH: str = get_env_var('BACKUP_PATH', 'backups/', required=False)
BACKUP_INTERVAL: int = int(get_env_var('BACKUP_INTERVAL', '24', required=False))

# === ЛОГИРОВАНИЕ ===
LOG_LEVEL: str = get_env_var('LOG_LEVEL', 'INFO', required=False)

# === ОПЦИОНАЛЬНЫЕ ПЕРЕМЕННЫЕ (для совместимости) ===
ADMIN_CHAT_ID: int = int(get_env_var('ADMIN_CHAT_ID', '0', required=False))

# Проверка путей
os.makedirs(os.path.dirname(DATABASE_PATH) or '.', exist_ok=True)
os.makedirs(BACKUP_PATH, exist_ok=True)