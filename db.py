import sqlite3

def init_db():
    conn = sqlite3.connect('starbot.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            gift_count TEXT,
            balance INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def set_gift_count(user_id, gift_count):
    conn = sqlite3.connect('starbot.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO user_settings (user_id, gift_count)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET gift_count=excluded.gift_count
    ''', (user_id, gift_count))
    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = sqlite3.connect('starbot.db')
    c = conn.cursor()
    c.execute('SELECT gift_count, balance FROM user_settings WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'gift_count': row[0], 'balance': row[1]}
    else:
        return None
