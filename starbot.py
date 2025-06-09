from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    ConversationHandler, filters
)
import sqlite3

TOKEN = "8183658865:AAHQjtIJWA8d_yk7cPceKFZ2f8x1riijxH0"

# Шаги разговора
GIFT_COUNT, MAX_PRICE, RELEASED = range(3)

# Создаём БД
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        gift_count INTEGER,
        max_price INTEGER,
        released_thousands INTEGER,
        stars INTEGER DEFAULT 0,
        want_to_buy INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу выбрать подарки.\n\n🎁 Сколько подарков ты хочешь получить?\n\n💫 Также доступны команды:\n/addstars <число> - добавить звёзды\n/buygift - купить подарок"
    )
    return GIFT_COUNT

# Добавление звёзд
async def addstars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        stars = int(context.args[0]) if context.args else 0
        if stars <= 0:
            raise ValueError
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users(user_id, stars) VALUES (?,0)", (user_id,))
        cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (stars, user_id))
        cursor.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,))
        total_stars = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✨ Добавлено {stars} звёзд!\n💫 Всего у вас: {total_stars} звёзд\n\n🎁 Используйте /buygift для покупки подарка")
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Использование: /addstars <число>\nПример: /addstars 100")

# Покупка подарка
async def buygift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT stars, gift_count, max_price, released_thousands FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        await update.message.reply_text("❌ Сначала настройте параметры подарков командой /start")
        return
        
    stars, gift_count, max_price, released_thousands = row
    
    if stars <= 0:
        conn.close()
        await update.message.reply_text("❌ У вас нет звёзд для покупки подарка.\n💫 Используйте /addstars <число> для добавления звёзд")
        return
    
    if not gift_count or not max_price:
        conn.close()
        await update.message.reply_text("❌ Сначала настройте параметры подарков командой /start")
        return
    
    # Помечаем запрос на покупку в базе (чтобы userbot увидел)
    cursor.execute("UPDATE users SET want_to_buy = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"🎁 Запрос на покупку принят!\n\n📋 Ваши настройки:\n🎁 Подарков: {gift_count}\n💰 Бюджет: {max_price}₽ за подарок\n📦 Выпущено: {released_thousands * 1000 if released_thousands else 0} штук\n💫 Звёзд: {stars}\n\n⏳ Подождите немного...")

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
        await update.message.reply_text("🎉 Сколько тысяч подарков уже выпущено? (например: 20)")
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

        await update.message.reply_text(
            f"✅ Всё сохранено!\n\n🎁 Подарков: {gift_count}\n💸 Бюджет на 1: {max_price}₽\n📦 Выпущено: {released * 1000} штук\n\nОжидайте — подберу лучшие варианты 🎯",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число, например: 20")
        return RELEASED

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Отменено. Начни заново — /start", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

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
app.add_handler(CommandHandler("addstars", addstars))
app.add_handler(CommandHandler("buygift", buygift))

print("🚀 Bot is running...")
app.run_polling()


