#!/usr/bin/env python3

from db import get_user_settings, enable_auto_buy, add_stars
import sqlite3

def check_autobuy_status():
    """Проверяет статус автопокупки"""
    
    # Проверяем настройки автопокупки для тестового пользователя
    test_user = 123456789
    settings = get_user_settings(test_user)
    print(f'🔍 Настройки пользователя {test_user}:')
    print(f'  Баланс: {settings["stars"]} звезд')
    print(f'  Автопокупка: {"🟢 ВКЛ" if settings["auto_buy"] else "🔴 ВЫКЛ"}')
    print(f'  Новые подарки: {"🟢 ВКЛ" if settings["auto_buy_new_gifts"] else "🔴 ВЫКЛ"}')
    print(f'  Макс. звезд за подарок: {settings["max_stars_per_gift"]}')

    # Включаем автопокупку для тестирования
    enable_auto_buy(test_user, enable_new_gifts=True, max_stars_per_gift=200)
    print(f'✅ Автопокупка ВКЛЮЧЕНА для пользователя {test_user}')

    # Проверяем кто есть в автопокупке
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, stars, auto_buy, auto_buy_new_gifts, max_stars_per_gift FROM users WHERE auto_buy = 1')
    auto_users = cursor.fetchall()
    conn.close()

    print(f'\n🤖 Пользователи с автопокупкой ({len(auto_users)}):')
    for user_id, stars, auto_buy, auto_new, max_stars in auto_users:
        print(f'  User {user_id}: {stars}⭐, max {max_stars}⭐ за подарок')

if __name__ == "__main__":
    check_autobuy_status() 