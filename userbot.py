from telethon import TelegramClient
from telethon.tl.functions.messages import SendMediaRequest, GetAvailableGiftsRequest
from telethon.tl.functions.payments import SendStarsFormRequest, GetStarsGiftsRequest
from telethon.tl.types import InputMediaGift, MessageMediaGift
import sqlite3
import asyncio
import json
import time
from db import log_purchase, spend_stars

# Данные Telegram API
api_id = 23355959
api_hash = 'b1f4e47d212838b44762a1c3b04fe37f'
phone = '+48795405315'

client = TelegramClient("user_session", api_id, api_hash)

class TelegramGiftMonitor:
    def __init__(self):
        self.known_gifts = set()
        self.last_check = 0
        
    async def get_available_gifts(self):
        """Получает актуальный каталог подарков от Telegram"""
        try:
            # Используем Telegram API для получения доступных подарков
            result = await client(GetStarsGiftsRequest())
            
            gifts = []
            for gift in result.gifts:
                gift_info = {
                    'id': gift.id,
                    'name': gift.title,
                    'stars_cost': gift.stars,
                    'total_count': gift.total_count,
                    'sold_count': gift.sold_count,
                    'first_sale_date': gift.first_sale_date,
                    'last_sale_date': gift.last_sale_date,
                    'sticker': gift.sticker,
                    'limited': gift.limited,
                    'remaining': gift.total_count - gift.sold_count if gift.limited else None
                }
                gifts.append(gift_info)
                
            return gifts
            
        except Exception as e:
            print(f"❌ Ошибка получения каталога подарков: {e}")
            return []
    
    async def check_for_new_gifts(self):
        """Проверяет появление новых подарков"""
        try:
            current_gifts = await self.get_available_gifts()
            new_gifts = []
            
            for gift in current_gifts:
                gift_id = gift['id']
                
                # Проверяем, новый ли это подарок
                if gift_id not in self.known_gifts:
                    # Проверяем, что подарок действительно новый (появился недавно)
                    if gift['first_sale_date'] and time.time() - gift['first_sale_date'] < 3600:  # В течение часа
                        new_gifts.append(gift)
                    
                    self.known_gifts.add(gift_id)
            
            return new_gifts
            
        except Exception as e:
            print(f"❌ Ошибка проверки новых подарков: {e}")
            return []
    
    async def update_gift_catalog(self):
        """Обновляет каталог подарков в базе данных"""
        try:
            gifts = await self.get_available_gifts()
            
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            
            # Очищаем старый каталог
            c.execute('DELETE FROM available_gifts WHERE source = "telegram"')
            
            # Добавляем актуальные подарки
            for gift in gifts:
                c.execute('''
                    INSERT INTO available_gifts 
                    (telegram_id, name, price_stars, total_released, sold_count, 
                     remaining, limited, sticker_id, source, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, "telegram", 1)
                ''', (
                    gift['id'], gift['name'], gift['stars_cost'], 
                    gift['total_count'], gift['sold_count'], gift['remaining'],
                    gift['limited'], str(gift['sticker']), 
                ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Обновлен каталог: {len(gifts)} подарков")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обновления каталога: {e}")
            return False

async def send_real_telegram_gift(recipient_user_id, gift_id, stars_cost):
    """Отправляет настоящий Telegram подарок"""
    try:
        # Создаем медиа для подарка
        gift_media = InputMediaGift(
            gift_id=gift_id,
            stars=stars_cost
        )
        
        # Отправляем подарок
        result = await client(SendMediaRequest(
            peer=recipient_user_id,
            media=gift_media,
            message="🎁 Автоматически куплен для вас!",
            random_id=int(time.time())
        ))
        
        print(f"✅ Telegram подарок ID:{gift_id} отправлен пользователю {recipient_user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки Telegram подарка: {e}")
        return False

async def auto_buy_new_gifts(new_gifts):
    """Автоматически покупает новые подарки для пользователей с автопокупкой"""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Получаем пользователей с включенной автопокупкой
        c.execute('''
            SELECT user_id, stars, gift_count, max_price, auto_buy_new_gifts, max_stars_per_gift 
            FROM users 
            WHERE auto_buy = 1 AND stars > 0 AND auto_buy_new_gifts = 1
        ''')
        auto_buyers = c.fetchall()
        
        for gift in new_gifts:
            gift_id = gift['id']
            gift_name = gift['name']
            stars_cost = gift['stars_cost']
            
            print(f"🎁 НОВЫЙ ПОДАРОК: {gift_name} за {stars_cost}⭐")
            
            for user_id, user_stars, gift_count, max_price, auto_new, max_stars in auto_buyers:
                # Проверяем, подходит ли подарок под критерии пользователя
                if stars_cost <= max_stars and user_stars >= stars_cost:
                    
                    print(f"🚀 Автопокупка для пользователя {user_id}: {gift_name}")
                    
                    # Покупаем подарок
                    success = await send_real_telegram_gift(user_id, gift_id, stars_cost)
                    
                    if success:
                        # Списываем звезды
                        if spend_stars(user_id, stars_cost):
                            # Логируем покупку
                            log_purchase(user_id, gift_name, 0, stars_cost, "self", "success")
                            
                            # Уведомляем пользователя
                            await client.send_message(user_id, 
                                f"🎉 АВТОПОКУПКА!\n\n"
                                f"🎁 Новый подарок: {gift_name}\n"
                                f"💫 Потрачено: {stars_cost} звезд\n"
                                f"⚡ Куплен автоматически при появлении!"
                            )
                            
                            print(f"✅ Автопокупка успешна для {user_id}")
                        else:
                            print(f"❌ Не удалось списать звезды у {user_id}")
                    else:
                        print(f"❌ Не удалось купить подарок для {user_id}")
                        
                    # Задержка между покупками
                    await asyncio.sleep(2)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка автопокупки новых подарков: {e}")

async def process_manual_orders():
    """Обрабатывает ручные заказы пользователей"""
    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, stars, gift_count, max_price, released_thousands 
            FROM users 
            WHERE want_to_buy = 1 AND stars > 0
        """)
        manual_orders = cursor.fetchall()

        for user_id, stars, gift_count, max_price, released_thousands in manual_orders:
            print(f"\n🎁 Обрабатываем ручной заказ пользователя {user_id}")
            
            # Получаем подходящие подарки из Telegram каталога
            cursor.execute('''
                SELECT telegram_id, name, price_stars, sticker_id 
                FROM available_gifts 
                WHERE price_stars <= ? AND source = "telegram" AND is_active = 1
                ORDER BY price_stars DESC
                LIMIT 10
            ''', (max_price,))
            suitable_gifts = cursor.fetchall()
            
            if not suitable_gifts:
                await client.send_message(user_id, "❌ Нет подходящих подарков в каталоге")
                cursor.execute("UPDATE users SET want_to_buy = 0 WHERE user_id = ?", (user_id,))
                continue
            
            successful_purchases = 0
            total_stars_spent = 0
            
            for i in range(min(gift_count, len(suitable_gifts))):
                gift_id, gift_name, stars_cost, sticker_id = suitable_gifts[i % len(suitable_gifts)]
                
                if stars >= stars_cost:
                    # Покупаем настоящий Telegram подарок
                    success = await send_real_telegram_gift(user_id, gift_id, stars_cost)
                    
                    if success:
                        spend_stars(user_id, stars_cost)
                        log_purchase(user_id, gift_name, 0, stars_cost, "self", "success")
                        
                        successful_purchases += 1
                        total_stars_spent += stars_cost
                        stars -= stars_cost
                        
                        print(f"✅ Подарок #{i+1} '{gift_name}' куплен")
                        await asyncio.sleep(2)
                    else:
                        print(f"❌ Ошибка покупки подарка '{gift_name}'")
            
            # Уведомляем о результатах
            if successful_purchases > 0:
                await client.send_message(user_id,
                    f"🎉 Покупки завершены!\n\n"
                    f"🎁 Куплено: {successful_purchases} подарков\n"
                    f"💫 Потрачено: {total_stars_spent} звезд\n"
                    f"✨ Все подарки отправлены!"
                )
            
            # Снимаем флаг заказа
            cursor.execute("UPDATE users SET want_to_buy = 0 WHERE user_id = ?", (user_id,))
            conn.commit()

        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка обработки ручных заказов: {e}")

async def main():
    await client.start(phone)
    print("✅ UserBot подключен для работы с настоящими Telegram подарками!")
    
    gift_monitor = TelegramGiftMonitor()
    
    # Инициализация: обновляем каталог при запуске
    await gift_monitor.update_gift_catalog()

    while True:
        try:
            # 1. Проверяем новые подарки каждые 30 секунд
            new_gifts = await gift_monitor.check_for_new_gifts()
            
            if new_gifts:
                print(f"🆕 Найдено {len(new_gifts)} новых подарков!")
                
                # Обновляем каталог в базе
                await gift_monitor.update_gift_catalog()
                
                # Автоматически покупаем для пользователей с автопокупкой
                await auto_buy_new_gifts(new_gifts)
            
            # 2. Обрабатываем ручные заказы
            await process_manual_orders()
            
            if not new_gifts:
                print("⏳ Мониторим новые подарки...")
                
        except Exception as e:
            print(f"❌ Ошибка в главном цикле: {e}")
            
        await asyncio.sleep(30)  # Проверка каждые 30 секунд

if __name__ == "__main__":
    asyncio.run(main())

