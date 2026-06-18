#!/bin/bash
# Однократный поиск видео: достаёт 40 штук, отправляет лучшие (score ≥ 8) в бот
cd "$(dirname "$0")"

# Флаг: если файл content.off существует — поиск отключён
if [ -f "content.off" ]; then
    echo "🔴 Поиск видео отключён (файл content.off существует)"
    echo "   Чтобы включить: rm content.off"
    exit 0
fi

source yag-env/bin/activate
pkill -9 -f "python.*content_engine" 2>/dev/null
sleep 1

echo "🔍 Ищу видео..."
python -m content_engine.main 2>&1 | tee /tmp/yag_content.log
echo "✅ Поиск завершён. Черновики отправлены в бот."
