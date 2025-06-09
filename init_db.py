import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    setting1 TEXT,
    setting2 TEXT
)
""")

# Добавим тестового пользователя (можно убрать потом)
cursor.execute("""
INSERT OR REPLACE INTO users (user_id, setting1, setting2)
VALUES (123456789, '🎁 Подарок A', '💬 Сообщение B')
""")

conn.commit()
conn.close()

print("✅ Таблица создана и пользователь добавлен.")
