# Конфигурация для StarBot автопокупки подарков
import os

# Telegram Bot API
BOT_TOKEN = os.getenv("BOT_TOKEN", "8183658865:AAHQjtIJWA8d_yk7cPceKFZ2f8x1riijxH0")

# Telegram Client API (для userbot)
API_ID = int(os.getenv("API_ID", 23355959))
API_HASH = os.getenv("API_HASH", 'b1f4e47d212838b44762a1c3b04fe37f')
PHONE = os.getenv("PHONE", '+48795405315')

# Настройки мониторинга
MONITOR_INTERVAL = 30  # секунд между проверками новых подарков
NEW_GIFT_THRESHOLD = 3600  # считать подарок новым, если он появился менее часа назад

# Настройки автопокупки
DEFAULT_MAX_STARS_PER_GIFT = 50
DEFAULT_GIFT_COUNT = 3
DEFAULT_MAX_PRICE = 500  # рублей

# Настройки уведомлений
ENABLE_NOTIFICATIONS = True
NOTIFICATION_DELAY = 2  # секунд между покупками

# База данных
DATABASE_PATH = 'users.db'

# Логи
ENABLE_LOGGING = True
LOG_LEVEL = 'INFO' 