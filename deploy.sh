#!/bin/bash
echo "🚀 Деплой StarBot на Fly.io..."
echo "📝 Изменения будут применены через ~1-2 минуты"
echo ""

# Деплой
fly deploy

echo ""
echo "✅ Деплой завершен!"
echo "📊 Проверить статус: fly status"
echo "📋 Посмотреть логи: fly logs --no-tail"
echo ""
echo "🤖 Ваш бот обновлен и работает в облаке!" 