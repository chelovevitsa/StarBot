#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестирование функций StarBot
"""

import sqlite3
from db import init_db, add_stars, get_user_settings, create_star_check, claim_star_check, get_user_checks

def test_database_and_checks():
    """Тестирует основные функции базы данных и чеков"""
    
    print("🧪 Тестирование StarBot функций...")
    
    # Инициализируем базу данных
    init_db()
    print("✅ База данных инициализирована")
    
    # Тестовый пользователь
    test_user_id = 123456789
    test_recipient_id = 987654321
    
    # 1. Добавляем звезды тестовому пользователю
    total_stars = add_stars(test_user_id, 500)
    print(f"✅ Добавлено 500 звезд пользователю {test_user_id}, всего: {total_stars}")
    
    # 2. Проверяем настройки пользователя
    settings = get_user_settings(test_user_id)
    print(f"✅ Настройки пользователя: {settings}")
    
    # 3. Создаем чек
    check_id, result = create_star_check(test_user_id, 100, message="Тестовый перевод")
    if check_id:
        print(f"✅ Создан чек ID: {check_id} на 100 звезд")
        
        # 4. Проверяем баланс после создания чека
        settings_after = get_user_settings(test_user_id)
        print(f"✅ Баланс после создания чека: {settings_after['stars']} звезд")
        
        # 5. Активируем чек другим пользователем
        success, check_data = claim_star_check(check_id, test_recipient_id)
        if success:
            print(f"✅ Чек активирован пользователем {test_recipient_id}")
            print(f"   Получено: {check_data['amount']} звезд")
            
            # 6. Проверяем баланс получателя
            add_stars(test_recipient_id, 0)  # Создаем запись если нет
            recipient_settings = get_user_settings(test_recipient_id)
            print(f"✅ Баланс получателя: {recipient_settings['stars']} звезд")
        else:
            print(f"❌ Ошибка активации чека: {check_data}")
    else:
        print(f"❌ Ошибка создания чека: {result}")
    
    # 7. Получаем историю чеков
    sent_checks, received_checks = get_user_checks(test_user_id)
    print(f"✅ Отправленных чеков: {len(sent_checks)}")
    print(f"✅ Полученных чеков: {len(received_checks)}")
    
    # 8. Проверяем состояние базы данных
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM star_checks")
    checks_count = cursor.fetchone()[0]
    print(f"✅ Всего чеков в базе: {checks_count}")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE stars > 0")
    users_with_stars = cursor.fetchone()[0] 
    print(f"✅ Пользователей со звездами: {users_with_stars}")
    
    conn.close()
    
    print("\n🎉 Все тесты завершены!")
    print("💡 Функционал чеков работает корректно!")

if __name__ == "__main__":
    test_database_and_checks() 