import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Основная таблица пользователей с настройками автопокупки
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            gift_count INTEGER DEFAULT 1,
            max_price INTEGER DEFAULT 100,
            released_thousands INTEGER DEFAULT 10,
            stars INTEGER DEFAULT 0,
            want_to_buy INTEGER DEFAULT 0,
            auto_buy INTEGER DEFAULT 0,
            auto_buy_new_gifts INTEGER DEFAULT 0,
            max_stars_per_gift INTEGER DEFAULT 50,
            notification_enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица истории покупок
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            gift_name TEXT,
            gift_price INTEGER,
            stars_spent INTEGER,
            telegram_gift_id TEXT,
            recipient_username TEXT,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success',
            auto_purchase INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Обновленная таблица доступных подарков из Telegram
    c.execute('''
        CREATE TABLE IF NOT EXISTS available_gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE,
            name TEXT,
            price_stars INTEGER,
            price_rubles INTEGER,
            total_released INTEGER,
            sold_count INTEGER DEFAULT 0,
            remaining INTEGER,
            limited INTEGER DEFAULT 0,
            emoji TEXT,
            sticker_id TEXT,
            source TEXT DEFAULT 'telegram',
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Таблица для отслеживания новых подарков
    c.execute('''
        CREATE TABLE IF NOT EXISTS new_gift_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_gift_id TEXT,
            gift_name TEXT,
            stars_cost INTEGER,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified_users TEXT,
            auto_purchases_made INTEGER DEFAULT 0
        )
    ''')
    
    # Индексы для оптимизации
    c.execute('CREATE INDEX IF NOT EXISTS idx_gifts_price ON available_gifts(price_stars)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_gifts_source ON available_gifts(source)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_users_auto_buy ON users(auto_buy, auto_buy_new_gifts)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_purchase_history_user ON purchase_history(user_id)')
    
    conn.commit()
    conn.close()

def set_gift_count(user_id, gift_count):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (user_id, gift_count)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET gift_count=excluded.gift_count
    ''', (user_id, gift_count))
    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT gift_count, max_price, released_thousands, stars, auto_buy, 
               auto_buy_new_gifts, max_stars_per_gift, notification_enabled
        FROM users WHERE user_id=?
    ''', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'gift_count': row[0], 
            'max_price': row[1], 
            'released_thousands': row[2],
            'stars': row[3],
            'auto_buy': row[4],
            'auto_buy_new_gifts': row[5],
            'max_stars_per_gift': row[6],
            'notification_enabled': row[7]
        }
    else:
        return None

def add_stars(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users(user_id, stars) VALUES (?,0)', (user_id,))
    c.execute('UPDATE users SET stars = stars + ? WHERE user_id = ?', (amount, user_id))
    c.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
    total_stars = c.fetchone()[0]
    conn.commit()
    conn.close()
    return total_stars

def get_suitable_gifts(max_price_rubles, max_released):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT name, price_stars, price_rubles, total_released, emoji, telegram_id
        FROM available_gifts 
        WHERE price_rubles <= ? AND total_released <= ? AND is_active = 1
        ORDER BY price_rubles DESC
    ''', (max_price_rubles, max_released))
    gifts = c.fetchall()
    conn.close()
    return gifts

def log_purchase(user_id, gift_name, gift_price, stars_spent, recipient_username="self", status="success", telegram_gift_id=None, auto_purchase=False):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO purchase_history 
        (user_id, gift_name, gift_price, stars_spent, telegram_gift_id, recipient_username, status, auto_purchase)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, gift_name, gift_price, stars_spent, telegram_gift_id, recipient_username, status, int(auto_purchase)))
    conn.commit()
    conn.close()

def spend_stars(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET stars = stars - ? WHERE user_id = ? AND stars >= ?', (amount, user_id, amount))
    success = c.rowcount > 0
    conn.commit()
    conn.close()
    return success

def enable_auto_buy(user_id, enable_new_gifts=True, max_stars_per_gift=50):
    """Включает автопокупку для пользователя"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET auto_buy = 1, auto_buy_new_gifts = ?, max_stars_per_gift = ?
        WHERE user_id = ?
    ''', (int(enable_new_gifts), max_stars_per_gift, user_id))
    conn.commit()
    conn.close()

def disable_auto_buy(user_id):
    """Отключает автопокупку для пользователя"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET auto_buy = 0, auto_buy_new_gifts = 0
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def get_auto_buy_users():
    """Получает список пользователей с включенной автопокупкой"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT user_id, stars, max_stars_per_gift, notification_enabled
        FROM users 
        WHERE auto_buy = 1 AND auto_buy_new_gifts = 1 AND stars > 0
    ''')
    users = c.fetchall()
    conn.close()
    return users

def log_new_gift_alert(telegram_gift_id, gift_name, stars_cost):
    """Логирует обнаружение нового подарка"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT OR IGNORE INTO new_gift_alerts 
        (telegram_gift_id, gift_name, stars_cost)
        VALUES (?, ?, ?)
    ''', (telegram_gift_id, gift_name, stars_cost))
    conn.commit()
    conn.close()

def get_purchase_stats(user_id, limit=10):
    """Получает статистику покупок пользователя"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        SELECT gift_name, stars_spent, purchase_date, status, auto_purchase
        FROM purchase_history 
        WHERE user_id = ? 
        ORDER BY purchase_date DESC 
        LIMIT ?
    ''', (user_id, limit))
    history = c.fetchall()
    
    # Общая статистика
    c.execute('''
        SELECT 
            COUNT(*) as total_purchases,
            SUM(stars_spent) as total_stars_spent,
            COUNT(CASE WHEN auto_purchase = 1 THEN 1 END) as auto_purchases
        FROM purchase_history 
        WHERE user_id = ? AND status = 'success'
    ''', (user_id,))
    stats = c.fetchone()
    
    conn.close()
    return history, stats