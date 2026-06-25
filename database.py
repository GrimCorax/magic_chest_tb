import sqlite3
import json
import shutil
import glob
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from contextlib import contextmanager
from loguru import logger

from config import DATABASE_PATH, BACKUP_PATH


@contextmanager
def get_db() -> sqlite3.Connection:
    """Контекстный менеджер для работы с БД"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Ошибка БД: {e}")
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Инициализация базы данных"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица призов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                weight INTEGER DEFAULT 1,
                monthly_limit INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Таблица ключей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                admin_id INTEGER NOT NULL,
                admin_name TEXT,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used BOOLEAN DEFAULT 0,
                used_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица истории призов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prize_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                prize_id INTEGER NOT NULL,
                prize_name TEXT,
                key_id INTEGER,
                admin_id INTEGER,
                admin_name TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered BOOLEAN DEFAULT 0,
                delivered_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (prize_id) REFERENCES prizes (id),
                FOREIGN KEY (key_id) REFERENCES keys (id)
            )
        ''')
        
        # Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_keys_user ON keys(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_keys_used ON keys(used)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_user ON prize_history(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_date ON prize_history(received_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_delivered ON prize_history(delivered)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_user_delivered ON prize_history(user_id, delivered)')
        
        logger.info("✅ База данных инициализирована")


# === РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ===

def add_user(telegram_id: int, name: str) -> bool:
    """Добавление нового пользователя"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (telegram_id, name) VALUES (?, ?)',
                (telegram_id, name.strip())
            )
            return True
    except sqlite3.IntegrityError as e:
        logger.warning(f"⚠️ Пользователь {name} уже существует: {e}")
        return False


def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получить пользователя по Telegram ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить пользователя по ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Получить пользователя по имени"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_users(status: str = 'active') -> List[Dict[str, Any]]:
    """Получить всех пользователей с указанным статусом"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE status = ? ORDER BY name', (status,))
        return [dict(row) for row in cursor.fetchall()]


def get_pending_users() -> List[Dict[str, Any]]:
    """Получить пользователей, ожидающих подтверждения"""
    return get_all_users('pending')


def update_user_status(telegram_id: int, status: str) -> None:
    """Обновить статус пользователя"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET status = ? WHERE telegram_id = ?',
            (status, telegram_id)
        )


def is_name_available(name: str) -> bool:
    """Проверить, свободно ли имя"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE name = ?', (name,))
        return cursor.fetchone() is None


# === РАБОТА С ПРИЗАМИ ===

def add_prize(name: str, weight: int, monthly_limit: int) -> bool:
    """Добавить новый приз"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO prizes (name, weight, monthly_limit) VALUES (?, ?, ?)',
                (name.strip(), weight, monthly_limit)
            )
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"⚠️ Приз {name} уже существует")
        return False


def get_all_prizes(active_only: bool = True) -> List[Dict[str, Any]]:
    """Получить все призы"""
    with get_db() as conn:
        cursor = conn.cursor()
        if active_only:
            cursor.execute('SELECT * FROM prizes WHERE is_active = 1 ORDER BY name')
        else:
            cursor.execute('SELECT * FROM prizes ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]


def get_prize_by_id(prize_id: int) -> Optional[Dict[str, Any]]:
    """Получить приз по ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM prizes WHERE id = ?', (prize_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_prize_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Получить приз по названию"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM prizes WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_prize(prize_id: int, weight: int, monthly_limit: int) -> None:
    """Обновить приз"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE prizes SET weight = ?, monthly_limit = ? WHERE id = ?',
            (weight, monthly_limit, prize_id)
        )


def delete_prize(prize_id: int) -> None:
    """Мягкое удаление приза"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE prizes SET is_active = 0 WHERE id = ?', (prize_id,))


# === РАБОТА С КЛЮЧАМИ ===

def add_keys(user_id: int, admin_id: int, admin_name: str, count: int) -> int:
    """Добавить ключи для пользователя"""
    with get_db() as conn:
        cursor = conn.cursor()
        added = 0
        for _ in range(count):
            cursor.execute(
                'INSERT INTO keys (user_id, admin_id, admin_name) VALUES (?, ?, ?)',
                (user_id, admin_id, admin_name)
            )
            added += 1
        return added


def get_active_keys_count(user_id: int) -> int:
    """Количество активных ключей у пользователя"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM keys WHERE user_id = ? AND used = 0',
            (user_id,)
        )
        return cursor.fetchone()[0]


def use_key(user_id: int) -> Optional[int]:
    """Использовать один ключ"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM keys WHERE user_id = ? AND used = 0 LIMIT 1',
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            key_id = row[0]
            cursor.execute(
                'UPDATE keys SET used = 1, used_at = CURRENT_TIMESTAMP WHERE id = ?',
                (key_id,)
            )
            return key_id
        return None


# === РАБОТА С ИСТОРИЕЙ ===

def add_prize_history(
    user_id: int,
    user_name: str,
    prize_id: int,
    prize_name: str,
    key_id: int,
    admin_id: int,
    admin_name: str
) -> None:
    """Добавить запись в историю"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO prize_history 
            (user_id, user_name, prize_id, prize_name, key_id, admin_id, admin_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, prize_id, prize_name, key_id, admin_id, admin_name))


def get_user_history(user_id: int) -> List[Dict[str, Any]]:
    """Получить историю пользователя"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT prize_name, received_at, delivered 
            FROM prize_history 
            WHERE user_id = ? 
            ORDER BY received_at DESC
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_user_history_by_month(user_id: int) -> Dict[str, Dict[str, Any]]:
    """Получить историю пользователя с группировкой по месяцам"""
    history = get_user_history(user_id)
    result = {}
    for item in history:
        try:
            date = datetime.strptime(item['received_at'], '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            continue
        month_key = date.strftime('%B %Y')
        prize_name = item['prize_name']
        
        if month_key not in result:
            result[month_key] = {}
        if prize_name not in result[month_key]:
            result[month_key][prize_name] = {'count': 0, 'delivered': 0}
        
        result[month_key][prize_name]['count'] += 1
        if item['delivered']:
            result[month_key][prize_name]['delivered'] += 1
    
    return result


def get_undelivered_prizes() -> Dict[str, Dict[str, int]]:
    """Получить невыданные призы по пользователям"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_name, prize_name, COUNT(*) as count
            FROM prize_history
            WHERE delivered = 0
            GROUP BY user_name, prize_name
            ORDER BY user_name
        ''')
        rows = cursor.fetchall()
        
        result = {}
        for row in rows:
            user = row['user_name']
            prize = row['prize_name']
            count = row['count']
            if user not in result:
                result[user] = {}
            result[user][prize] = count
        return result


def mark_as_delivered(user_name: str, prize_name: str, count: Optional[int] = None) -> int:
    """Отметить призы как выданные"""
    with get_db() as conn:
        cursor = conn.cursor()
        if count is None:
            cursor.execute('''
                UPDATE prize_history 
                SET delivered = 1, delivered_at = CURRENT_TIMESTAMP
                WHERE user_name = ? AND prize_name = ? AND delivered = 0
            ''', (user_name, prize_name))
        else:
            cursor.execute('''
                UPDATE prize_history 
                SET delivered = 1, delivered_at = CURRENT_TIMESTAMP
                WHERE user_name = ? AND prize_name = ? AND delivered = 0
                LIMIT ?
            ''', (user_name, prize_name, count))
        return cursor.rowcount


def get_user_monthly_count(user_id: int, prize_id: int, month: datetime) -> int:
    """Получить количество получений приза за месяц"""
    start_of_month = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (start_of_month + timedelta(days=32)).replace(day=1)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM prize_history
            WHERE user_id = ? AND prize_id = ? 
            AND received_at >= ? AND received_at < ?
        ''', (user_id, prize_id, start_of_month, next_month))
        return cursor.fetchone()[0]


def get_user_total_stats(user_id: int) -> Dict[str, Any]:
    """Получить полную статистику пользователя"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        active_keys = get_active_keys_count(user_id)
        
        cursor.execute(
            'SELECT COUNT(*) FROM prize_history WHERE user_id = ? AND delivered = 0',
            (user_id,)
        )
        undelivered = cursor.fetchone()[0]
        
        cursor.execute(
            'SELECT COUNT(*) FROM prize_history WHERE user_id = ?',
            (user_id,)
        )
        total_prizes = cursor.fetchone()[0]
        
        return {
            'active_keys': active_keys,
            'undelivered': undelivered,
            'total_prizes': total_prizes
        }


def get_prize_by_weight(user_id: int) -> Optional[Dict[str, Any]]:
    """Выбрать приз на основе весов с учетом лимита"""
    import random
    
    prizes = get_all_prizes(active_only=True)
    if not prizes:
        return None
    
    now = datetime.now()
    available_prizes = []
    for prize in prizes:
        monthly_count = get_user_monthly_count(user_id, prize['id'], now)
        if monthly_count < prize['monthly_limit']:
            available_prizes.append(prize)
    
    if not available_prizes:
        return None
    
    total_weight = sum(p['weight'] for p in available_prizes)
    rand = random.randint(1, total_weight)
    
    current = 0
    for prize in available_prizes:
        current += prize['weight']
        if rand <= current:
            return prize
    
    return available_prizes[-1]


def backup_database() -> None:
    """Создание резервной копии БД"""
    try:
        os.makedirs(BACKUP_PATH, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_PATH, f'magic_chest_{timestamp}.db')
        
        shutil.copy2(DATABASE_PATH, backup_file)
        logger.info(f"✅ Бэкап создан: {backup_file}")
        
        # Удаляем старые бэкапы (старше 30 дней)
        for file in glob.glob(os.path.join(BACKUP_PATH, 'magic_chest_*.db')):
            if os.path.getmtime(file) < (datetime.now().timestamp() - 30 * 24 * 3600):
                os.remove(file)
                logger.debug(f"🗑 Удален старый бэкап: {file}")
    except Exception as e:
        logger.error(f"❌ Ошибка создания бэкапа: {e}")


# Инициализация при загрузке модуля
init_db()