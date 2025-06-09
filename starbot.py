from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    ConversationHandler, filters, CallbackQueryHandler
)
import sqlite3
from db import init_db, add_stars, get_user_settings, get_suitable_gifts, enable_auto_buy, disable_auto_buy, get_purchase_stats

TOKEN = "8183658865:AAHQjtIJWA8d_yk7cPceKFZ2f8x1riijxH0"

# Шаги разговора
GIFT_COUNT, MAX_PRICE, RELEASED = range(3)

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎁 Настроить подарки", callback_data='setup_gifts')],
        [InlineKeyboardButton("💫 Мой баланс", callback_data='check_balance')],
        [InlineKeyboardButton("🤖 Автопокупка", callback_data='auto_buy_settings')],
        [InlineKeyboardButton("📊 История покупок", callback_data='purchase_history')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Привет! Я ваш личный бот для автопокупки Telegram подарков!\n\n"
        "☁️ **Работаю 24/7 на Fly.io - независимо от вашего компьютера!**\n\n"
        "🎁 Настройте параметры подарков\n"
        "💫 Пополните баланс звезд\n"
        "🤖 Включите автопокупку новых подарков\n"
        "🚀 Запустите покупки\n\n"
        "💡 Доступные команды:\n"
        "/addstars <число> - добавить звезды\n"
        "/buygift - купить подарки сейчас\n"
        "/autobuy - включить автопокупку\n"
        "/stopautobuy - выключить автопокупку\n"
        "/balance - проверить баланс\n"
        "/stats - статистика покупок",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'setup_gifts':
        await query.edit_message_text(
            "🎁 Настройка подарков\n\n"
            "Сколько подарков вы хотите получать за раз?"
        )
        return GIFT_COUNT
    
    elif query.data == 'check_balance':
        settings = get_user_settings(user_id)
        if settings:
            balance_text = f"💫 Ваш баланс: **{settings['stars']} звезд**\n\n"
            balance_text += f"⚙️ Настройки:\n"
            balance_text += f"🎁 Подарков за раз: {settings['gift_count']}\n"
            balance_text += f"💰 Макс. цена: {settings['max_price']}₽\n"
            balance_text += f"📦 Лимит выпуска: {settings['released_thousands']}k\n"
            balance_text += f"🤖 Автопокупка: {'🟢 ВКЛ' if settings['auto_buy'] else '🔴 ВЫКЛ'}\n"
            balance_text += f"⚡ Новые подарки: {'🟢 ВКЛ' if settings['auto_buy_new_gifts'] else '🔴 ВЫКЛ'}\n"
            balance_text += f"💎 Макс. звезд за подарок: {settings['max_stars_per_gift']}"
        else:
            balance_text = "❌ Сначала настройте параметры подарков!"
            
        await query.edit_message_text(balance_text, parse_mode="Markdown")
        
    elif query.data == 'auto_buy_settings':
        settings = get_user_settings(user_id)
        auto_status = "🟢 ВКЛЮЧЕНА" if settings and settings['auto_buy'] else "🔴 ВЫКЛЮЧЕНА"
        new_gifts_status = "🟢 ВКЛ" if settings and settings['auto_buy_new_gifts'] else "🔴 ВЫКЛ"
        
        keyboard = [
            [InlineKeyboardButton("🟢 Включить автопокупку", callback_data='enable_auto')],
            [InlineKeyboardButton("🔴 Выключить автопокупку", callback_data='disable_auto')],
            [InlineKeyboardButton("⚡ Настроить новые подарки", callback_data='setup_new_gifts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🤖 **Настройки автопокупки**\n\n"
            f"Статус: {auto_status}\n"
            f"Новые подарки: {new_gifts_status}\n\n"
            f"💡 **Как работает:**\n"
            f"• Бот мониторит новые подарки в Telegram\n"
            f"• Автоматически покупает их при появлении\n"
            f"• Учитывает ваши лимиты по цене и звездам\n"
            f"• Отправляет уведомления о покупках",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    elif query.data == 'enable_auto':
        enable_auto_buy(user_id, enable_new_gifts=True, max_stars_per_gift=50)
        await query.edit_message_text(
            "🟢 **Автопокупка ВКЛЮЧЕНА!**\n\n"
            "⚡ Автопокупка новых подарков: ВКЛ\n"
            "💎 Макс. звезд за подарок: 50\n\n"
            "🤖 Бот будет автоматически покупать новые подарки при их появлении в Telegram!",
            parse_mode="Markdown"
        )
        
    elif query.data == 'disable_auto':
        disable_auto_buy(user_id)
        await query.edit_message_text(
            "🔴 **Автопокупка ВЫКЛЮЧЕНА**\n\n"
            "Бот больше не будет автоматически покупать подарки.",
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
            
        await query.edit_message_text(history_text, parse_mode="Markdown")

# Количество подарков
async def get_gift_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text)
        if count <= 0:
            raise ValueError
        context.user_data['gift_count'] = count
        await update.message.reply_text("💰 Какой максимальный бюджет на *один* подарок? (в рублях)", parse_mode="Markdown")
        return MAX_PRICE
    except ValueError:
        await update.message.reply_text("❌ Введите положительное число, например: 3")
        return GIFT_COUNT

# Максимальная цена
async def get_max_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text)
        if price <= 0:
            raise ValueError
        context.user_data['max_price'] = price
        await update.message.reply_text("🎉 Лимит выпущенных подарков (в тысячах)? (например: 50)")
        return RELEASED
    except ValueError:
        await update.message.reply_text("❌ Введите число, например: 500")
        return MAX_PRICE

# Количество выпущенных
async def get_released(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        released = int(update.message.text)
        if released < 0:
            raise ValueError

        user_id = update.message.from_user.id
        gift_count = context.user_data['gift_count']
        max_price = context.user_data['max_price']

        # Сохраняем в БД
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, gift_count, max_price, released_thousands)
            VALUES (?, ?, ?, ?)
        """, (user_id, gift_count, max_price, released))
        conn.commit()
        conn.close()

        # Показываем подходящие подарки
        suitable_gifts = get_suitable_gifts(max_price, released * 1000)
        
        gift_list = ""
        for name, stars, price, total, emoji in suitable_gifts[:5]:
            gift_list += f"{emoji} {name} - {stars}⭐ ({price}₽)\n"

        await update.message.reply_text(
            f"✅ Настройки сохранены!\n\n"
            f"🎁 Подарков за раз: {gift_count}\n"
            f"💸 Бюджет на 1: {max_price}₽\n"
            f"📦 Лимит выпуска: {released}k\n\n"
            f"🎯 Подходящие подарки:\n{gift_list}\n"
            f"💫 Используйте /addstars для пополнения баланса\n"
            f"🎁 Используйте /buygift для покупки",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число, например: 50")
        return RELEASED

# Добавление звёзд
async def addstars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        stars = int(context.args[0]) if context.args else 0
        if stars <= 0:
            raise ValueError
        
        total_stars = add_stars(user_id, stars)
        
        await update.message.reply_text(
            f"✨ Добавлено {stars} звезд!\n"
            f"💫 Всего у вас: {total_stars} звезд\n\n"
            f"🎁 Используйте /buygift для покупки подарков"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /addstars <число>\nПример: /addstars 100")

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
        await update.message.reply_text(
            f"💫 Ваш баланс: {settings['stars']} звезд\n\n"
            f"⚙️ Настройки:\n"
            f"🎁 Подарков за раз: {settings['gift_count']}\n"
            f"💰 Макс. цена: {settings['max_price']}₽\n"
            f"📦 Лимит выпуска: {settings['released_thousands']}k"
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

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Отменено. Начните заново — /start", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

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
        f"💎 Макс. звезд за подарок: {max_stars}\n"
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

# Запуск
init_db()
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        GIFT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gift_count)],
        MAX_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_max_price)],
        RELEASED: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_released)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("addstars", addstars))
app.add_handler(CommandHandler("buygift", buygift))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("gifts", gifts))
app.add_handler(CommandHandler("autobuy", autobuy))
app.add_handler(CommandHandler("stopautobuy", stopautobuy))
app.add_handler(CommandHandler("stats", stats))

print("🚀 StarBot запущен и готов к работе!")
app.run_polling()


