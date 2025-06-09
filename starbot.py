from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    CallbackQueryHandler, filters
)
import sqlite3
from db import init_db, add_stars, get_user_settings, get_suitable_gifts, enable_auto_buy, disable_auto_buy, get_purchase_stats, create_star_check, claim_star_check, get_user_checks

TOKEN = "8183658865:AAHQjtIJWA8d_yk7cPceKFZ2f8x1riijxH0"

# Словарь для хранения состояний пользователей
user_states = {}

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем есть ли параметры (например, для активации чека)
    if context.args:
        arg = context.args[0]
        if arg.startswith('check_'):
            check_id = arg.replace('check_', '')
            user_id = update.message.from_user.id
            
            # Активируем чек
            success, result = claim_star_check(check_id, user_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ **Чек активирован успешно!**\n\n"
                    f"💫 Получено: {result['amount']} звезд\n"
                    f"🆔 ID чека: `{check_id}`\n\n"
                    f"🎉 Звезды добавлены на ваш баланс!\n\n"
                    f"Используйте главное меню для управления:",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"❌ **Ошибка активации чека:**\n{result}\n\n"
                    f"Используйте главное меню:",
                    parse_mode="Markdown"
                )
    
    await show_main_menu(update)

async def show_main_menu(update: Update, edit_message=False):
    keyboard = [
        [InlineKeyboardButton("🎁 Настроить подарки", callback_data='setup_gifts')],
        [InlineKeyboardButton("💫 Мой баланс", callback_data='check_balance')],
        [InlineKeyboardButton("🛒 Купить существующий подарок", callback_data='buy_existing_gift')],
        [InlineKeyboardButton("🤖 Автопокупка", callback_data='auto_buy_settings')],
        [InlineKeyboardButton("📊 История покупок", callback_data='purchase_history')],
        [InlineKeyboardButton("🧾 Чеки", callback_data='check_receipts')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "👋 Привет! Я ваш личный бот для автопокупки Telegram подарков!\n\n"
        "🎁 Настройте параметры подарков\n"
        "💫 Пополните баланс звезд\n"
        "🛒 Купите случайный подарок прямо сейчас\n" 
        "🤖 Включите автопокупку новых подарков\n"
        "🚀 Запустите покупки\n\n"
        "➡️ Доступные команды:\n"
        "/menu - главное меню\n"
        "/addstars <число> - добавить звезды\n"
        "/sendstars @user <число> - отправить звезды\n"
        "/buygift - купить подарки сейчас\n"
        "/autobuy - включить автопокупку\n"
        "/stopautobuy - выключить автопокупку\n"
        "/balance - проверить баланс\n"
        "/stats - статистика покупок"
    )
    
    if edit_message and hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def buy_random_gift(query):
    """Покупка случайного подарка на основе настроек пользователя"""
    import random
    
    user_id = query.from_user.id
    settings = get_user_settings(user_id)
    
    if not settings:
        await query.edit_message_text(
            "❌ **Настройки не найдены**\n\n"
            "Сначала настройте параметры подарков!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎁 Настроить подарки", callback_data='setup_gifts')]]),
            parse_mode="Markdown"
        )
        return
    
    if settings['stars'] <= 0:
        await query.edit_message_text(
            "❌ **Недостаточно звезд**\n\n"
            "Пополните баланс для покупки подарков!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💫 Пополнить баланс", callback_data='check_balance')]]),
            parse_mode="Markdown"
        )
        return
    
    # Получаем лимиты пользователя
    min_price = settings.get('min_price', 15)
    max_price = settings.get('max_price', 100)
    max_supply = settings.get('released_thousands', 50)
    
    # Ищем подходящие подарки
    suitable_gifts = get_suitable_gifts(user_id)
    
    if not suitable_gifts:
        await query.edit_message_text(
            f"❌ **Подходящих подарков не найдено**\n\n"
            f"📋 Ваши лимиты:\n"
            f"⭐ Цена: {min_price}-{max_price} звезд\n"
            f"📦 Сапплай: до {max_supply}k\n\n"
            f"Попробуйте изменить настройки или добавить подарки в базу данных.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Изменить настройки", callback_data='setup_gifts')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]),
            parse_mode="Markdown"
        )
        return
    
    # Выбираем случайный подарок
    gift = random.choice(suitable_gifts)
    gift_name, gift_price, gift_supply, gift_emoji = gift
    
    # Проверяем хватает ли звезд
    if settings['stars'] < gift_price:
        await query.edit_message_text(
            f"❌ **Недостаточно звезд для покупки**\n\n"
            f"{gift_emoji} **{gift_name}**\n"
            f"💰 Цена: {gift_price} звезд\n"
            f"💫 У вас: {settings['stars']} звезд\n"
            f"❌ Не хватает: {gift_price - settings['stars']} звезд",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💫 Пополнить баланс", callback_data='check_balance')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]),
            parse_mode="Markdown"
        )
        return
    
    # Покупаем подарок (списываем звезды и записываем в историю)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Списываем звезды
    new_balance = settings['stars'] - gift_price
    cursor.execute("UPDATE users SET stars = ? WHERE user_id = ?", (new_balance, user_id))
    
    # Записываем покупку в историю
    cursor.execute("""
        INSERT INTO purchase_history (user_id, gift_name, stars_spent, status, is_auto)
        VALUES (?, ?, ?, 'success', 0)
    """, (user_id, gift_name, gift_price))
    
    conn.commit()
    conn.close()
    
    # Показываем результат покупки
    await query.edit_message_text(
        f"✅ **Подарок куплен успешно!**\n\n"
        f"{gift_emoji} **{gift_name}**\n"
        f"💰 Потрачено: {gift_price} звезд\n"
        f"📦 Тираж: {gift_supply}k\n"
        f"💫 Остаток: {new_balance} звезд\n\n"
        f"🎁 Подарок добавлен в вашу коллекцию!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Купить еще", callback_data='buy_existing_gift')],
            [InlineKeyboardButton("📊 История покупок", callback_data='purchase_history')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'main_menu':
        # Сбрасываем состояние пользователя при возврате в главное меню
        if user_id in user_states:
            del user_states[user_id]
        await show_main_menu(update, edit_message=True)
        return

    elif query.data == 'setup_gifts':
        # Сбрасываем состояние пользователя при входе в настройки
        if user_id in user_states:
            del user_states[user_id]
            
        settings = get_user_settings(user_id)
        
        if settings:
            settings_text = f"🎁 **Текущие настройки подарков:**\n\n"
            settings_text += f"🔄 Количество подарков: {settings.get('auto_buy_cycles', 1)}\n"
            min_price = settings.get('min_price', 15)
            max_price = settings.get('max_price', 100)
            settings_text += f"⭐ Лимит цены: {min_price}-{max_price} звезд\n"
            settings_text += f"📦 Лимит сапплая: {settings['released_thousands']}k\n"
            settings_text += f"💫 Звезд на балансе: {settings['stars']}\n\n"
            settings_text += f"Что хотите изменить?"
        else:
            settings_text = f"🎁 **Настройка подарков**\n\n"
            settings_text += f"Выберите что настроить:"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Количество подарков", callback_data='set_cycles')],
            [InlineKeyboardButton("⭐ Лимит цены ОТ", callback_data='set_min_price')],
            [InlineKeyboardButton("⭐ Лимит цены ДО", callback_data='set_max_price')],
            [InlineKeyboardButton("📦 Лимит сапплая", callback_data='change_supply_limit')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif query.data == 'check_balance':
        settings = get_user_settings(user_id)
        if settings:
            balance_text = f"💫 **Ваш баланс: {settings['stars']} звезд**\n\n"
            balance_text += f"⚙️ Настройки:\n"
            balance_text += f"🔄 Количество подарков: {settings.get('auto_buy_cycles', 1)}\n"
            min_price = settings.get('min_price', 15)
            max_price = settings.get('max_price', 100)
            balance_text += f"⭐ Лимит цены: {min_price}-{max_price} звезд\n"
            balance_text += f"📦 Лимит сапплая: {settings['released_thousands']}k\n"
            balance_text += f"🤖 Автопокупка: {'🟢 ВКЛ' if settings['auto_buy'] else '🔴 ВЫКЛ'}\n"
            balance_text += f"⚡ Новые подарки: {'🟢 ВКЛ' if settings['auto_buy_new_gifts'] else '🔴 ВЫКЛ'}"
        else:
            balance_text = "💫 **Ваш баланс: 0 звезд**\n\n❌ Сначала настройте параметры подарков!"
        
        # Добавляем кнопки для пополнения баланса
        keyboard = [
            [InlineKeyboardButton("⭐ Купить звезды дёшево", callback_data='buy_stars_cheap')],
            [InlineKeyboardButton("⭐ Оплатить через Telegram", callback_data='buy_stars_telegram')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(balance_text, reply_markup=reply_markup, parse_mode="Markdown")
        
    elif query.data == 'buy_existing_gift':
        await buy_random_gift(query)
        
    elif query.data == 'auto_buy_settings':
        settings = get_user_settings(user_id)
        auto_status = "🟢 ВКЛЮЧЕНА" if settings and settings['auto_buy'] else "🔴 ВЫКЛЮЧЕНА"
        new_gifts_status = "🟢 ВКЛ" if settings and settings['auto_buy_new_gifts'] else "🔴 ВЫКЛ"
        
        # Показываем текущие настройки
        settings_text = f"🤖 **Настройки автопокупки**\n\n"
        settings_text += f"Статус: {auto_status}\n"
        settings_text += f"Новые подарки: {new_gifts_status}\n\n"
        
        if settings:
            settings_text += f"⚙️ **Текущие лимиты:**\n"
            settings_text += f"🔄 Количество подарков: {settings.get('auto_buy_cycles', 1)}\n"
            min_price = settings.get('min_price', 15)
            max_price = settings.get('max_price', 100)
            settings_text += f"⭐ Лимит цены: {min_price}-{max_price} звезд\n"
            settings_text += f"📦 Лимит сапплая: {settings['released_thousands']}k\n\n"
            settings_text += f"💡 Для изменения параметров используйте:\n"
            settings_text += f"🎁 Настроить подарки\n\n"
        
        settings_text += f"💡 **Как работает:**\n"
        settings_text += f"• Мониторит новые подарки в Telegram\n"
        settings_text += f"• Покупает по вашим лимитам\n"
        settings_text += f"• Отправляет уведомления о покупках"
        
        keyboard = [
            [InlineKeyboardButton("🟢 Включить автопокупку", callback_data='enable_auto')],
            [InlineKeyboardButton("🔴 Выключить автопокупку", callback_data='disable_auto')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode="Markdown")
        
    elif query.data == 'enable_auto':
        # Получаем реальные настройки пользователя
        settings = get_user_settings(user_id)
        
        if not settings:
            # Если настроек нет, создаем дефолтные и включаем автопокупку
            enable_auto_buy(user_id, enable_new_gifts=True, max_stars_per_gift=50)
            settings_text = (
                "🟢 **Автопокупка ВКЛЮЧЕНА!**\n\n"
                "⚡ Автопокупка новых подарков: ВКЛ\n"
                "⭐ Лимит цены: 50-100 звезд (по умолчанию)\n"
                "📦 Лимит сапплая: 10k (по умолчанию)\n"
                "🔄 Подарков за раз: 1 (по умолчанию)\n\n"
                "❗ Настройте параметры в '🎁 Настроить подарки'\n\n"
                "🤖 Бот будет автоматически покупать новые подарки!"
            )
        else:
            # Включаем автопокупку с текущими настройками пользователя
            max_price = settings.get('max_price', 100)
            enable_auto_buy(user_id, enable_new_gifts=True, max_stars_per_gift=max_price)
            
            min_price = settings.get('min_price', 15)
            supply_limit = settings.get('released_thousands', 10)
            cycles = settings.get('auto_buy_cycles', 1)
            
            settings_text = (
                "🟢 **Автопокупка ВКЛЮЧЕНА!**\n\n"
                "⚡ Автопокупка новых подарков: ВКЛ\n\n"
                "📋 **Ваши лимиты:**\n"
                f"⭐ Цена: {min_price}-{max_price} звезд\n"
                f"📦 Сапплай: до {supply_limit}k\n"
                f"🔄 Подарков за раз: {cycles}\n"
                f"💫 Баланс: {settings['stars']} звезд\n\n"
                "🤖 Бот будет автоматически покупать новые подарки при их появлении в Telegram!"
            )
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode="Markdown")
        
    elif query.data == 'disable_auto':
        disable_auto_buy(user_id)
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔴 **Автопокупка ВЫКЛЮЧЕНА**\n\n"
            "Бот больше не будет автоматически покупать подарки.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    elif query.data == 'purchase_history':
        history, stats = get_purchase_stats(user_id, limit=10)
        
        if history:
            history_text = f"📊 **Статистика покупок:**\n"
            history_text += f"🎁 Всего куплено: {stats[0]} подарков\n"
            history_text += f"💫 Потрачено звезд: {stats[1]}\n"
            history_text += f"🤖 Автопокупок: {stats[2]}\n\n"
            history_text += f"**Последние покупки:**\n"
            
            for gift_name, stars_spent, date, status, auto in history[:5]:
                status_emoji = "✅" if status == "success" else "❌"
                auto_emoji = "🤖" if auto else "👤"
                history_text += f"{status_emoji}{auto_emoji} {gift_name} - {stars_spent}⭐\n"
        else:
            history_text = "📊 История покупок пуста"
            
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)    
        await query.edit_message_text(history_text, reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == 'check_receipts':
        # Главное меню чеков
        sent_checks, received_checks = get_user_checks(user_id, limit=5)
        
        checks_text = "🧾 **Ваши чеки:**\n\n"
        
        if sent_checks:
            checks_text += "📤 **Отправленные:**\n"
            for check_id, amount, to_username, status, created_at, claimed_at, message in sent_checks[:3]:
                status_emoji = "✅" if status == "claimed" else "⏳"
                recipient = f"@{to_username}" if to_username else "Любой"
                checks_text += f"{status_emoji} {check_id} - {amount}⭐ → {recipient}\n"
            checks_text += "\n"
        
        if received_checks:
            checks_text += "📥 **Полученные:**\n"
            for check_id, amount, status, created_at, claimed_at, message in received_checks[:3]:
                checks_text += f"✅ {check_id} - {amount}⭐\n"
            checks_text += "\n"
        
        if not sent_checks and not received_checks:
            checks_text += "📭 У вас пока нет чеков\n\n"
        
        checks_text += "💡 **Возможности:**\n"
        checks_text += "• Создать чек для вывода звезд\n"
        checks_text += "• Отправить звезды другому пользователю\n"
        checks_text += "• Активировать полученный чек"
        
        keyboard = [
            [InlineKeyboardButton("📤 Создать чек", callback_data='create_check')],
            [InlineKeyboardButton("📥 Активировать чек", callback_data='activate_check')],
            [InlineKeyboardButton("📋 Все мои чеки", callback_data='my_checks')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(checks_text, reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == 'create_check':
        settings = get_user_settings(user_id)
        if not settings or settings['stars'] <= 0:
            await query.edit_message_text(
                "❌ **Недостаточно звезд**\n\n"
                "Для создания чека нужны звезды на балансе!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💫 Пополнить баланс", callback_data='check_balance')]]),
                parse_mode="Markdown"
            )
            return
        
        # Устанавливаем состояние для ввода суммы чека
        user_states[user_id] = 'enter_check_amount'
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить", callback_data='cancel_input')],
            [InlineKeyboardButton("🔙 Назад к чекам", callback_data='check_receipts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📤 **Создание чека**\n\n"
            f"💫 Ваш баланс: {settings['stars']} звезд\n\n"
            f"Введите сумму для чека:\n"
            f"Пример: 100\n"
            f"Пример: 50",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    elif query.data == 'activate_check':
        # Устанавливаем состояние для ввода ID чека
        user_states[user_id] = 'enter_check_id'
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить", callback_data='cancel_input')],
            [InlineKeyboardButton("🔙 Назад к чекам", callback_data='check_receipts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📥 **Активация чека**\n\n"
            "Введите ID чека который хотите активировать:\n"
            "Пример: a1b2c3d4\n\n"
            "💡 ID чека можно найти в ссылке или сообщении с чеком",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    elif query.data == 'my_checks':
        sent_checks, received_checks = get_user_checks(user_id, limit=20)
        
        checks_text = "📋 **Все ваши чеки:**\n\n"
        
        if sent_checks:
            checks_text += "📤 **Отправленные чеки:**\n"
            for check_id, amount, to_username, status, created_at, claimed_at, message in sent_checks:
                status_emoji = "✅" if status == "claimed" else "⏳"
                recipient = f"@{to_username}" if to_username else "Любой"
                date = created_at.split(' ')[0] if created_at else ""
                checks_text += f"{status_emoji} `{check_id}` - {amount}⭐ → {recipient} ({date})\n"
            checks_text += "\n"
        
        if received_checks:
            checks_text += "📥 **Полученные чеки:**\n"
            for check_id, amount, status, created_at, claimed_at, message in received_checks:
                date = claimed_at.split(' ')[0] if claimed_at else ""
                checks_text += f"✅ `{check_id}` - {amount}⭐ ({date})\n"
            checks_text += "\n"
        
        if not sent_checks and not received_checks:
            checks_text = "📭 **У вас пока нет чеков**\n\nСоздайте первый чек для отправки звезд!"
        
        keyboard = [
            [InlineKeyboardButton("📤 Создать чек", callback_data='create_check')],
            [InlineKeyboardButton("🔙 Назад к чекам", callback_data='check_receipts')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(checks_text, reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == 'set_max_price':
        keyboard = [
            [InlineKeyboardButton("⭐ 15", callback_data='max_stars_15'), InlineKeyboardButton("⭐ 25", callback_data='max_stars_25')],
            [InlineKeyboardButton("⭐ 50", callback_data='max_stars_50'), InlineKeyboardButton("⭐ 100", callback_data='max_stars_100')],
            [InlineKeyboardButton("⭐ 200", callback_data='max_stars_200'), InlineKeyboardButton("⭐ 500", callback_data='max_stars_500')],
            [InlineKeyboardButton("⭐ 1000", callback_data='max_stars_1000'), InlineKeyboardButton("⭐ 1500", callback_data='max_stars_1500')],
            [InlineKeyboardButton("⭐ 2000", callback_data='max_stars_2000'), InlineKeyboardButton("⭐ 2500", callback_data='max_stars_2500')],
            [InlineKeyboardButton("⭐ 3000", callback_data='max_stars_3000'), InlineKeyboardButton("⭐ 5000", callback_data='max_stars_5000')],
            [InlineKeyboardButton("⭐ 7500", callback_data='max_stars_7500'), InlineKeyboardButton("⭐ 10000", callback_data='max_stars_10000')],
            [InlineKeyboardButton("⭐ 15000", callback_data='max_stars_15000'), InlineKeyboardButton("⭐ 20000", callback_data='max_stars_20000')],
            [InlineKeyboardButton("⭐ Убрать лимит", callback_data='max_stars_unlimited')],
            [InlineKeyboardButton("🔙 Назад", callback_data='setup_gifts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выбери новый максимум цены для автопокупки:\n"
            "(бот не отправит подарок дороже установленного лимита)",
            reply_markup=reply_markup
        )

    elif query.data == 'set_min_price':
        keyboard = [
            [InlineKeyboardButton("⭐ 15", callback_data='min_stars_15'), InlineKeyboardButton("⭐ 25", callback_data='min_stars_25')],
            [InlineKeyboardButton("⭐ 50", callback_data='min_stars_50'), InlineKeyboardButton("⭐ 100", callback_data='min_stars_100')],
            [InlineKeyboardButton("⭐ 200", callback_data='min_stars_200'), InlineKeyboardButton("⭐ 500", callback_data='min_stars_500')],
            [InlineKeyboardButton("⭐ 1000", callback_data='min_stars_1000'), InlineKeyboardButton("⭐ 1500", callback_data='min_stars_1500')],
            [InlineKeyboardButton("⭐ 2000", callback_data='min_stars_2000'), InlineKeyboardButton("⭐ 2500", callback_data='min_stars_2500')],
            [InlineKeyboardButton("⭐ 3000", callback_data='min_stars_3000'), InlineKeyboardButton("⭐ 5000", callback_data='min_stars_5000')],
            [InlineKeyboardButton("⭐ 10000", callback_data='min_stars_10000'), InlineKeyboardButton("⭐ 20000", callback_data='min_stars_20000')],
            [InlineKeyboardButton("⭐ Убрать лимит", callback_data='min_stars_unlimited')],
            [InlineKeyboardButton("🔙 Назад", callback_data='setup_gifts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выбери новый минимум цены для автопокупки:\n"
            "(бот не отправит подарок дешевле установленного лимита)",
            reply_markup=reply_markup
        )

    elif query.data.startswith('min_stars_'):
        # Обработка выбора минимального лимита звезд
        if query.data == 'min_stars_unlimited':
            min_stars = 0
            stars_text = "без лимита"
        else:
            min_stars = int(query.data.replace('min_stars_', ''))
            stars_text = f"{min_stars} звезд"
        
        user_id = query.from_user.id
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET min_price = ? WHERE user_id = ?", (min_stars, user_id))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO users (user_id, min_price) VALUES (?, ?)", (user_id, min_stars))
        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к настройкам", callback_data='setup_gifts')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **Минимальная цена обновлена!**\n\n"
            f"Минимум за подарок: {stars_text}\n"
            f"🤖 Автопокупка будет учитывать новый лимит",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data.startswith('max_stars_'):
        # Обработка выбора максимального лимита звезд  
        if query.data == 'max_stars_unlimited':
            max_stars = 99999
            stars_text = "без лимита"
        else:
            max_stars = int(query.data.replace('max_stars_', ''))
            stars_text = f"{max_stars} звезд"
        
        user_id = query.from_user.id
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET max_price = ? WHERE user_id = ?", (max_stars, user_id))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO users (user_id, max_price) VALUES (?, ?)", (user_id, max_stars))
        conn.commit()
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к настройкам", callback_data='setup_gifts')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **Максимальная цена обновлена!**\n\n"
            f"Максимум за подарок: {stars_text}\n"
            f"🤖 Автопокупка будет учитывать новый лимит",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data in ['set_cycles']:
        setting_type = query.data
        user_id = query.from_user.id
        
        # Устанавливаем состояние пользователя
        user_states[user_id] = setting_type
        
        instructions = {
            'set_cycles': "🔄 **Настройка количества подарков**\n\nВведите количество подарков за раз:\nПример: 5"
        }
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить", callback_data='cancel_input')],
            [InlineKeyboardButton("🔙 Назад к настройкам", callback_data='setup_gifts')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ {instructions[setting_type]}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data == 'change_supply_limit':
        keyboard = [
            [InlineKeyboardButton("500", callback_data='supply_500'), InlineKeyboardButton("1000", callback_data='supply_1000')],
            [InlineKeyboardButton("1500", callback_data='supply_1500'), InlineKeyboardButton("1999", callback_data='supply_1999')],
            [InlineKeyboardButton("2000", callback_data='supply_2000'), InlineKeyboardButton("3000", callback_data='supply_3000')],
            [InlineKeyboardButton("5000", callback_data='supply_5000'), InlineKeyboardButton("7500", callback_data='supply_7500')],
            [InlineKeyboardButton("10000", callback_data='supply_10000'), InlineKeyboardButton("15000", callback_data='supply_15000')],
            [InlineKeyboardButton("25000", callback_data='supply_25000'), InlineKeyboardButton("50000", callback_data='supply_50000')],
            [InlineKeyboardButton("100000", callback_data='supply_100000'), InlineKeyboardButton("250000", callback_data='supply_250000')],
            [InlineKeyboardButton("⭐ Убрать лимит", callback_data='supply_unlimited')],
            [InlineKeyboardButton("🔙 Назад", callback_data='setup_gifts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Выбери новый лимит сапплая для автопокупки:\n"
            "(бот не отправит подарок, если их выпущено больше установленного лимита)",
            reply_markup=reply_markup
        )

    elif query.data.startswith('supply_'):
        # Обработка выбора лимита сапплая
        if query.data == 'supply_unlimited':
            supply_limit = 999999
            supply_text = "без лимита"
        else:
            supply_limit = int(query.data.replace('supply_', ''))
            supply_text = f"{supply_limit}k"
        
        user_id = query.from_user.id
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET released_thousands = ? WHERE user_id = ?", (supply_limit, user_id))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO users (user_id, released_thousands) VALUES (?, ?)", (user_id, supply_limit))
        conn.commit()
        conn.close()

        keyboard = [
            [InlineKeyboardButton("🔙 Назад к настройкам", callback_data='setup_gifts')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📦 **Лимит сапплая обновлен!**\n\n"
            f"Максимальный тираж: {supply_text}\n"
            f"🤖 Автопокупка будет учитывать новый лимит",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data.startswith('buy_stars_'):
        # Обработка покупки звезд
        if query.data == 'buy_stars_100':
            # Вызываем платеж через Telegram Stars
            from telegram import LabeledPrice
            
            await query.edit_message_text(
                "💫 **Оплата 100 звезд**\n\n"
                "Сейчас откроется окно оплаты Telegram Stars.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='main_menu')]])
            )
            
            # Отправляем invoice для оплаты
            await context.bot.send_invoice(
                chat_id=query.from_user.id,
                title="⭐ Пополнение",
                description="Пополнение баланса звезд",
                payload="stars_100",
                provider_token="",  # Для Telegram Stars не нужен
                currency="XTR",  # Telegram Stars
                prices=[LabeledPrice("Звезды", 100)]
            )
            
        elif query.data == 'buy_stars_cheap':
            # Устанавливаем состояние пользователя для ввода суммы пополнения
            user_states[user_id] = 'enter_stars_amount'
            
            keyboard = [
                [InlineKeyboardButton("❌ Отменить", callback_data='cancel_input')],
                [InlineKeyboardButton("🔙 Назад", callback_data='check_balance')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💫 **Пополнение баланса звезд**\n\n"
                "Отправьте В ЧАТ сумму пополнения в звездах:\n"
                "(комиссия сервиса 5%)\n\n"
                "Пример: 100\n\n"
                "Если у вас нет звезд, купите их на ваш аккаунт по ссылке",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        elif query.data == 'buy_stars_telegram':
            # Устанавливаем состояние пользователя для ввода суммы пополнения  
            user_states[user_id] = 'enter_stars_amount'
            
            keyboard = [
                [InlineKeyboardButton("❌ Отменить", callback_data='cancel_input')],
                [InlineKeyboardButton("🔙 Назад", callback_data='check_balance')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💫 **Пополнение через Telegram Stars**\n\n"
                "Введите количество звезд для пополнения:\n\n"
                "Пример: 12\n"
                "Пример: 50\n"
                "Пример: 100",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

    elif query.data == 'cancel_input':
        # Сбрасываем состояние пользователя
        user_id = query.from_user.id
        if user_id in user_states:
            del user_states[user_id]
        
        await query.edit_message_text(
            "❌ **Ввод отменен**\n\nВозвращаемся к настройкам.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎁 Настроить подарки", callback_data='setup_gifts')]])
        )

# Обработчик успешных платежей
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    payment = update.message.successful_payment
    
    if payment.invoice_payload == "stars_100":
        # Добавляем 100 звезд пользователю
        total_stars = add_stars(user_id, 100)

        await update.message.reply_text(
            f"✅ **Оплата прошла успешно!**\n\n"
            f"💫 Добавлено: 100 звезд\n"
            f"💫 Всего у вас: {total_stars} звезд\n\n"
            f"🎁 Теперь можете покупать подарки!",
            parse_mode="Markdown"
        )
    elif payment.invoice_payload.startswith("stars_"):
        # Извлекаем количество звезд из payload
        try:
            stars_amount = int(payment.invoice_payload.replace("stars_", ""))
            total_stars = add_stars(user_id, stars_amount)
            
            await update.message.reply_text(
                f"✅ **Оплата прошла успешно!**\n\n"
                f"💫 Добавлено: {stars_amount} звезд\n"
                f"💫 Всего у вас: {total_stars} звезд\n\n"
                f"🎁 Теперь можете покупать подарки!",
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text(
                f"❌ **Ошибка обработки платежа**\n\n"
                f"Обратитесь в поддержку с указанием ID платежа: {payment.invoice_payload}",
                parse_mode="Markdown"
            )

# Обработчик обычных текстовых сообщений
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Проверяем есть ли состояние ожидания ввода
    if user_id in user_states:
        state = user_states[user_id]
        
        try:
            if state == 'set_cycles':
                cycles = int(text)
                if cycles <= 0:
                    raise ValueError
                
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET auto_buy_cycles = ? WHERE user_id = ?", (cycles, user_id))
                if cursor.rowcount == 0:
                    cursor.execute("INSERT INTO users (user_id, auto_buy_cycles) VALUES (?, ?)", (user_id, cycles))
                conn.commit()
                conn.close()
                
                del user_states[user_id]
                
                keyboard = [[InlineKeyboardButton("🎁 Настроить подарки", callback_data='setup_gifts')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **Количество подарков обновлено!**\n\n"
                    f"Подарков за раз: {cycles}",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return
            
            elif state == 'enter_stars_amount':
                stars_amount = int(text)
                if stars_amount <= 0:
                    raise ValueError
                    
                del user_states[user_id]
                
                # Создаем платеж через Telegram Stars
                from telegram import LabeledPrice
                
                try:
                    # Отправляем invoice для оплаты указанного количества звезд
                    await context.bot.send_invoice(
                        chat_id=user_id,
                        title="⭐ Пополнение",
                        description="⭐ AutoGifts - Покупка подарков Telegram",
                        payload=f"stars_{stars_amount}",
                        provider_token="",  # Для Telegram Stars не нужен
                        currency="XTR",  # Telegram Stars
                        prices=[LabeledPrice("Звезды", stars_amount)]
                    )
                except Exception as e:
                    await update.message.reply_text(
                        f"❌ **Ошибка при создании платежа**\n\n"
                        f"Детали: {str(e)}\n\n"
                        f"Попробуйте еще раз или обратитесь в поддержку.",
                        parse_mode="Markdown"
                    )
                return
            
            elif state == 'enter_check_amount':
                amount = int(text)
                if amount <= 0:
                    raise ValueError
                
                # Проверяем баланс пользователя
                settings = get_user_settings(user_id)
                if not settings or settings['stars'] < amount:
                    await update.message.reply_text(
                        f"❌ **Недостаточно звезд**\n\n"
                        f"Нужно: {amount} звезд\n"
                        f"У вас: {settings['stars'] if settings else 0} звезд",
                        parse_mode="Markdown"
                    )
                    return
                
                # Создаем чек
                check_id, result = create_star_check(user_id, amount)
                
                if check_id:
                    del user_states[user_id]
                    
                    keyboard = [
                        [InlineKeyboardButton("📋 Мои чеки", callback_data='my_checks')],
                        [InlineKeyboardButton("🧾 Чеки", callback_data='check_receipts')],
                        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"✅ **Чек создан успешно!**\n\n"
                        f"🆔 ID чека: `{check_id}`\n"
                        f"💫 Сумма: {amount} звезд\n"
                        f"📤 Получатель: Любой\n\n"
                        f"🔗 Ссылка для активации:\n"
                        f"https://t.me/{context.bot.username}?start=check_{check_id}\n\n"
                        f"💡 Отправьте эту ссылку тому, кому хотите передать звезды!",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(
                        f"❌ **Ошибка создания чека:**\n{result}",
                        parse_mode="Markdown"
                    )
                return
            
            elif state == 'enter_check_id':
                check_id = text.strip()
                del user_states[user_id]
                
                # Активируем чек
                success, result = claim_star_check(check_id, user_id)
                
                if success:
                    keyboard = [
                        [InlineKeyboardButton("💫 Мой баланс", callback_data='check_balance')],
                        [InlineKeyboardButton("🧾 Чеки", callback_data='check_receipts')],
                        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"✅ **Чек активирован успешно!**\n\n"
                        f"💫 Получено: {result['amount']} звезд\n"
                        f"🆔 ID чека: `{check_id}`\n\n"
                        f"🎉 Звезды добавлены на ваш баланс!",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                else:
                    keyboard = [
                        [InlineKeyboardButton("📥 Попробовать еще", callback_data='activate_check')],
                        [InlineKeyboardButton("🧾 Чеки", callback_data='check_receipts')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"❌ **Ошибка активации чека:**\n{result}",
                        reply_markup=reply_markup,
                        parse_mode="Markdown"
                    )
                return
            
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ **Неверный формат!**\n\n"
                "Попробуйте еще раз или нажмите ❌ Отменить"
            )
            return
    
    # Если состояния нет, показываем справку
    await update.message.reply_text(
        "❓ **Не понимаю команду**\n\n"
        "💡 **Для настройки используйте команды:**\n"
        "/setgiftcount <число> - количество подарков\n"
        "/setpricerange <мин>-<макс> - диапазон цен\n"
        "/setsupply <число> - лимит сапплая\n"
        "/setmaxstars <число> - лимит звезд\n"
        "/setcycles <число> - циклы автопокупки\n\n"
        "📋 **Основные команды:**\n"
        "/start - главное меню\n"
        "/addstars - пополнить звезды\n"
        "/buygift - купить подарки\n"
        "/autobuy - включить автопокупку",
        parse_mode="Markdown"
    )

# Добавление звёзд
async def addstars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Если указано число - добавляем сразу (для тестирования)
    if context.args:
        try:
            stars = int(context.args[0])
            if stars <= 0:
                raise ValueError
            
            total_stars = add_stars(user_id, stars)
            
            await update.message.reply_text(
                f"✨ Добавлено {stars} звезд!\n"
                f"💫 Всего у вас: {total_stars} звезд\n\n"
                f"🎁 Используйте /buygift для покупки подарков"
            )
            return
        except (ValueError, IndexError):
            pass
    
    # Показываем инструкцию по пополнению
    keyboard = [
        [InlineKeyboardButton("⭐ Оплатить 100 STARS", callback_data='buy_stars_100')],
        [InlineKeyboardButton("⭐ Купить звезды дёшево", callback_data='buy_stars_cheap')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💫 **Пополнение баланса звезд**\n\n"
        "Выберите способ пополнения:\n\n"
        "⭐ **Telegram Stars** - быстро и безопасно\n"
        "💰 **Дешевая покупка** - по выгодной цене\n\n"
        "💡 Для тестирования: `/addstars <число>`",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Покупка подарка
async def buygift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    settings = get_user_settings(user_id)
    
    if not settings:
        await update.message.reply_text("❌ Сначала настройте параметры подарков командой /start")
        return
        
    if settings['stars'] <= 0:
        await update.message.reply_text("❌ У вас нет звезд для покупки подарка.\n💫 Используйте /addstars <число>")
        return
    
    # Помечаем запрос на покупку в базе
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET want_to_buy = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"🎁 Запрос на покупку принят!\n\n"
        f"📋 Ваши настройки:\n"
        f"🎁 Подарков: {settings['gift_count']}\n"
        f"💰 Бюджет: {settings['max_price']}₽ за подарок\n"
        f"💫 Звезд: {settings['stars']}\n\n"
        f"⏳ Обработка заказа..."
    )

# Проверка баланса
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    settings = get_user_settings(user_id)
    
    if settings:
        min_supply = settings.get('min_released_thousands', 1)
        max_supply = settings['released_thousands']
        
        await update.message.reply_text(
            f"💫 Ваш баланс: {settings['stars']} звезд\n\n"
            f"⚙️ Настройки:\n"
            f"🎁 Подарков за раз: {settings['gift_count']}\n"
            f"💰 Макс. цена: {settings['max_price']}₽\n"
            f"📦 Лимит сапплая: {min_supply}k-{max_supply}k"
        )
    else:
        await update.message.reply_text("❌ Сначала настройте параметры подарков командой /start")

# Доступные подарки
async def gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT name, price_stars, price_rubles, emoji FROM available_gifts WHERE is_active = 1')
    gifts = c.fetchall()
    conn.close()
    
    gifts_text = "🎁 Доступные подарки:\n\n"
    for name, stars, rubles, emoji in gifts:
        gifts_text += f"{emoji} {name} - {stars}⭐ ({rubles}₽)\n"
        
    await update.message.reply_text(gifts_text)

# Автопокупка команды
async def autobuy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Проверяем аргументы
    if context.args:
        try:
            max_stars = int(context.args[0])
            if max_stars <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Использование: /autobuy [макс_звезд_за_подарок]\nПример: /autobuy 25")
            return
    else:
        max_stars = 50  # По умолчанию
    
    settings = get_user_settings(user_id)
    if not settings:
        await update.message.reply_text("❌ Сначала настройте параметры подарков командой /start")
        return
        
    if settings['stars'] <= 0:
        await update.message.reply_text("❌ У вас нет звезд. Используйте /addstars <число>")
        return
    
    enable_auto_buy(user_id, enable_new_gifts=True, max_stars_per_gift=max_stars)
    
    await update.message.reply_text(
        f"🟢 **Автопокупка ВКЛЮЧЕНА!**\n\n"
        f"⚡ Автопокупка новых подарков: ВКЛ\n"
        f"⭐ Макс. звезд за подарок: {max_stars}\n"
        f"💫 Ваш баланс: {settings['stars']} звезд\n\n"
        f"🤖 Бот будет автоматически покупать новые Telegram подарки при их появлении!",
        parse_mode="Markdown"
    )

async def stopautobuy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    disable_auto_buy(user_id)
    
    await update.message.reply_text(
        "🔴 **Автопокупка ВЫКЛЮЧЕНА**\n\n"
        "Бот больше не будет автоматически покупать подарки.\n"
        "Используйте /autobuy для повторного включения.",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    history, stats = get_purchase_stats(user_id, limit=20)
    
    if not history:
        await update.message.reply_text("📊 У вас пока нет покупок")
        return
    
    stats_text = f"📊 **Ваша статистика:**\n\n"
    stats_text += f"🎁 Всего куплено: **{stats[0]}** подарков\n"
    stats_text += f"💫 Потрачено звезд: **{stats[1]}**\n"
    stats_text += f"🤖 Автопокупок: **{stats[2]}**\n"
    stats_text += f"👤 Ручных покупок: **{stats[0] - stats[2]}**\n\n"
    
    if len(history) > 0:
        stats_text += f"**Последние {min(10, len(history))} покупок:**\n"
        for gift_name, stars_spent, date, status, auto in history[:10]:
            status_emoji = "✅" if status == "success" else "❌"
            auto_emoji = "🤖" if auto else "👤"
            stats_text += f"{status_emoji}{auto_emoji} {gift_name} - {stars_spent}⭐\n"
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

# Команда для возврата в главное меню
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update)

# Команды для расширенных настроек автопокупки
async def setmaxstars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        max_stars = int(context.args[0]) if context.args else 0
        if max_stars <= 0:
            raise ValueError
        
        # Обновляем в базе данных
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET max_stars_per_gift = ? WHERE user_id = ?", (max_stars, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"⭐ **Лимит звезд обновлен!**\n\n"
            f"Максимум за подарок: {max_stars} звезд\n"
            f"🤖 Автопокупка будет учитывать новый лимит",
            parse_mode="Markdown"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /setmaxstars <число>\nПример: /setmaxstars 75")

async def setpricerange(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        if not context.args or '-' not in context.args[0]:
            raise ValueError
        
        price_range = context.args[0].split('-')
        min_price = int(price_range[0])
        max_price = int(price_range[1])
        
        if min_price < 0 or max_price < min_price:
            raise ValueError
        
        # Обновляем в базе данных
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET min_price = ?, max_price = ? WHERE user_id = ?", (min_price, max_price, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"💰 **Диапазон цен обновлен!**\n\n"
            f"От {min_price}₽ до {max_price}₽\n"
            f"🤖 Автопокупка будет покупать подарки в этом диапазоне",
            parse_mode="Markdown"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /setpricerange <мин>-<макс>\nПример: /setpricerange 100-1000")

async def setsupply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        supply_limit = int(context.args[0]) if context.args else 0
        if supply_limit < 0:
            raise ValueError
        
        # Обновляем в базе данных
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET released_thousands = ? WHERE user_id = ?", (supply_limit, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"📦 **Лимит сапплая обновлен!**\n\n"
            f"Максимальный тираж: {supply_limit}k подарков\n"
            f"🤖 Автопокупка будет покупать только подарки с тиражом до {supply_limit}000",
            parse_mode="Markdown"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /setsupply <число>\nПример: /setsupply 50")

async def setcycles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        cycles = int(context.args[0]) if context.args else 0
        if cycles <= 0:
            raise ValueError
        
        # Обновляем в базе данных
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET auto_buy_cycles = ? WHERE user_id = ?", (cycles, user_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"🔄 **Количество подарков обновлено!**\n\n"
            f"Подарков за раз: {cycles}\n"
            f"🤖 Бот будет покупать {cycles} штук подарков при каждой покупке",
            parse_mode="Markdown"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /setcycles <число>\nПример: /setcycles 5")

async def setgiftcount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        gift_count = int(context.args[0]) if context.args else 0
        if gift_count <= 0:
            raise ValueError
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET gift_count = ? WHERE user_id = ?", (gift_count, user_id))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO users (user_id, gift_count) VALUES (?, ?)", (user_id, gift_count))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"🎁 **Количество подарков обновлено!**\n\n"
            f"За раз будет покупаться: {gift_count} подарков",
            parse_mode="Markdown"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /setgiftcount <число>\nПример: /setgiftcount 3")

# Служебная команда для сброса баланса (только для исправления бага)
async def resetbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Сбрасываем баланс до 0
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET stars = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "✅ **Баланс сброшен до 0 звезд**\n\n"
        "🔧 Баг с автоматическим добавлением звезд исправлен!\n"
        "💫 Теперь звезды добавляются только после реальной оплаты",
        parse_mode="Markdown"
    )

# Команда для отправки звезд другому пользователю
async def sendstars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "💫 **Отправка звезд**\n\n"
                "Использование: `/sendstars <@username или user_id> <количество>`\n\n"
                "Примеры:\n"
                "`/sendstars @username 100`\n"
                "`/sendstars 123456789 50`",
                parse_mode="Markdown"
            )
            return
            
        recipient = context.args[0]
        amount = int(context.args[1])
        
        if amount <= 0:
            raise ValueError
            
        # Проверяем баланс отправителя
        settings = get_user_settings(user_id)
        if not settings or settings['stars'] < amount:
            await update.message.reply_text(
                f"❌ **Недостаточно звезд**\n\n"
                f"Нужно: {amount} звезд\n"
                f"У вас: {settings['stars'] if settings else 0} звезд",
                parse_mode="Markdown"
            )
            return
        
        # Создаем чек и сразу получаем ссылку
        check_id, result = create_star_check(user_id, amount, to_username=recipient.replace('@', ''))
        
        if check_id:
            bot_username = context.bot.username or "YourBotName"
            
            await update.message.reply_text(
                f"✅ **Звезды готовы к отправке!**\n\n"
                f"💫 Сумма: {amount} звезд\n"
                f"👤 Получатель: {recipient}\n\n"
                f"🔗 **Ссылка для получения:**\n"
                f"`https://t.me/{bot_username}?start=check_{check_id}`\n\n"
                f"📤 Отправьте эту ссылку пользователю {recipient}\n"
                f"💡 Как только он нажмет на ссылку, звезды будут переданы!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ **Ошибка создания перевода:**\n{result}",
                parse_mode="Markdown"
            )
            
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ **Неверный формат**\n\n"
            "Использование: `/sendstars <@username> <количество>`\n"
            "Пример: `/sendstars @friend 100`",
            parse_mode="Markdown"
        )

# Запуск
init_db()
app = ApplicationBuilder().token(TOKEN).build()

# Основные обработчики
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("addstars", addstars))
app.add_handler(CommandHandler("buygift", buygift))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("gifts", gifts))
app.add_handler(CommandHandler("autobuy", autobuy))
app.add_handler(CommandHandler("stopautobuy", stopautobuy))
app.add_handler(CommandHandler("stats", stats))

# Расширенные настройки
app.add_handler(CommandHandler("setmaxstars", setmaxstars))
app.add_handler(CommandHandler("setpricerange", setpricerange))
app.add_handler(CommandHandler("setsupply", setsupply))
app.add_handler(CommandHandler("setcycles", setcycles))
app.add_handler(CommandHandler("setgiftcount", setgiftcount))
app.add_handler(CommandHandler("resetbalance", resetbalance))
app.add_handler(CommandHandler("sendstars", sendstars))

# Новые обработчики
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

print("🚀 StarBot запущен и готов к работе!")
app.run_polling()


