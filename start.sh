#!/bin/sh
# Запускаем оба бота одновременно
python starbot.py &
python userbot.py &

# Ждем завершения любого из процессов
wait
