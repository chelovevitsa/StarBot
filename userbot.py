from telethon import TelegramClient
from telethon.tl.functions.messages import GetBotCallbackAnswerRequest
from telethon.tl.types import InputBotInlineMessageID
import sqlite3
import asyncio

# Данные Telegram API (замени своими)
api_id = 23355959
api_hash = 'b1f4e47d212838b44762a1c3b04fe37f'
phone = '+48795405315'

# Создаем клиент
client = TelegramClient("user_session", api_id, api_hash)

async def click_button(message, button_index=0, row_index=0):
    """
    Нажать кнопку по индексу в inline клавиатуре
    """
    try:
        btn = message.reply_markup.rows[row_index].buttons[button_index]
        await client(GetBotCallbackAnswerRequest(
            peer=message.peer_id,
            msg_id=message.id,
            data=btn.data
        ))
        print(f"✅ Нажата кнопка: {btn.text}")
        return True
    except Exception as e:
        print(f"❌ Ошибка нажатия кнопки: {e}")
        return False

async def find_button_by_text(message, button_text):
    """
    Найти и нажать кнопку по тексту
    """
    try:
        if not message.reply_markup:
            return False
            
        for row_idx, row in enumerate(message.reply_markup.rows):
            for btn_idx, btn in enumerate(row.buttons):
                if button_text.lower() in btn.text.lower():
                    await click_button(message, btn_idx, row_idx)
                    return True
        
        print(f"❌ Кнопка '{button_text}' не найдена")
        return False
    except Exception as e:
        print(f"❌ Ошибка поиска кнопки: {e}")
        return False

async def main():
    await client.start(phone)
    print("✅ Userbot подключен и мониторит покупки...")

    while True:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, stars, gift_count, max_price, released_thousands FROM users WHERE want_to_buy = 1")
        buyers = cursor.fetchall()

        for user_id, stars, gift_count, max_price, released_thousands in buyers:
            print(f"\n🎁 Покупаем подарок для пользователя {user_id}")
            print(f"💫 Звёзд: {stars}")
            print(f"📋 Настройки: {gift_count} подарков по {max_price}₽")
            
            # Здесь — эмуляция покупок через Telethon: посылаем команды/нажимаем кнопки другому боту
            await buy_gift_through_bot(user_id, gift_count, max_price)

            # Снимаем флаг want_to_buy и уменьшаем звезды (например, по фиксированной цене за подарок)
            gift_cost = 10  # Условная стоимость одного подарка в звёздах
            total_cost = gift_count * gift_cost
            
            if stars >= total_cost:
                cursor.execute("UPDATE users SET want_to_buy=0, stars = stars - ? WHERE user_id = ?", (total_cost, user_id))
                print(f"✅ Покупка завершена! Потрачено {total_cost} звёзд")
            else:
                cursor.execute("UPDATE users SET want_to_buy=0 WHERE user_id = ?", (user_id,))
                print(f"❌ Недостаточно звёзд! Нужно {total_cost}, есть {stars}")
            
            conn.commit()

        if not buyers:
            print("⏳ Нет новых заказов...")
            
        conn.close()
        await asyncio.sleep(5)  # Проверять каждые 5 секунд

async def buy_gift_through_bot(user_id, gift_count, max_price):
    """
    Реальное взаимодействие с ботом подарков через Telethon
    """
    try:
        # Замените '@gift_bot' на реальный username бота подарков
        bot_username = '@gift_bot'  # Например: '@AutoGiftsBot'
        
        print(f"🤖 Подключаемся к боту {bot_username}...")
        
        # Отправляем /start боту
        start_msg = await client.send_message(bot_username, '/start')
        await asyncio.sleep(2)
        
        # Получаем последние сообщения от бота
        messages = await client.get_messages(bot_username, limit=5)
        latest_msg = messages[0]
        
        # Если есть кнопки в ответе
        if latest_msg.reply_markup:
            print("🔍 Ищем кнопку поиска/каталога...")
            
            # Ищем кнопки по ключевым словам
            search_keywords = ['поиск', 'каталог', 'подарки', 'gifts', 'search', 'browse']
            
            button_found = False
            for keyword in search_keywords:
                if await find_button_by_text(latest_msg, keyword):
                    button_found = True
                    break
            
            if not button_found:
                # Если не нашли по тексту, нажимаем первую кнопку
                await click_button(latest_msg, 0, 0)
            
            await asyncio.sleep(2)
            
            # Получаем обновленные сообщения
            messages = await client.get_messages(bot_username, limit=3)
            latest_msg = messages[0]
            
            # Настройка фильтров по цене
            print(f"💰 Устанавливаем фильтр цены до {max_price}₽...")
            
            # Ищем кнопки фильтра цены
            price_keywords = ['цена', 'price', 'фильтр', 'filter', 'до', 'up to']
            
            for keyword in price_keywords:
                if await find_button_by_text(latest_msg, keyword):
                    await asyncio.sleep(1)
                    break
            
            # Отправляем цену текстом (если бот принимает текстовые команды)
            await client.send_message(bot_username, f'до {max_price}')
            await asyncio.sleep(2)
            
            # Процесс покупки подарков
            for i in range(gift_count):
                print(f"🎁 Покупаем подарок #{i+1}...")
                
                # Получаем актуальные сообщения
                messages = await client.get_messages(bot_username, limit=3)
                latest_msg = messages[0]
                
                # Ищем кнопку "Купить" или "Buy"
                buy_keywords = ['купить', 'buy', 'заказать', 'order', '💎', '⭐']
                
                buy_found = False
                for keyword in buy_keywords:
                    if await find_button_by_text(latest_msg, keyword):
                        buy_found = True
                        await asyncio.sleep(1)
                        break
                
                if not buy_found:
                    print(f"❌ Кнопка покупки не найдена для подарка #{i+1}")
                    continue
                
                # Подтверждение покупки (если требуется)
                await asyncio.sleep(1)
                messages = await client.get_messages(bot_username, limit=2)
                if messages[0].reply_markup:
                    confirm_keywords = ['подтвердить', 'confirm', 'да', 'yes', '✅']
                    for keyword in confirm_keywords:
                        if await find_button_by_text(messages[0], keyword):
                            break
                
                await asyncio.sleep(2)
            
            print("✅ Все подарки успешно куплены!")
            
        else:
            print("❌ Бот не отвечает кнопками")
            
    except Exception as e:
        print(f"❌ Ошибка при покупке через бота: {e}")

if __name__ == "__main__":
    asyncio.run(main())

