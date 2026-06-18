#!/bin/bash
cd "$(dirname "$0")"
source yag-env/bin/activate

# Kill ALL existing instances
pkill -9 -f "python.*tg_admin_bot"  2>/dev/null
pkill -9 -f "python.*video_factory" 2>/dev/null
pkill -9 -f "python.*publisher"     2>/dev/null

# Wait for Telegram to release the bot session (prevents TelegramConflictError)
echo "Ожидаем освобождения сессии бота..."
sleep 5

python -m tg_admin_bot.main  > /tmp/yag_admin.log    2>&1 &
python -m video_factory.main > /tmp/yag_video.log    2>&1 &
python -m publisher.main     > /tmp/yag_publisher.log 2>&1 &

echo "✅ Сервисы запущены"
echo "   Admin bot     → /tmp/yag_admin.log"
echo "   Video factory → /tmp/yag_video.log"
echo "   Publisher     → /tmp/yag_publisher.log"
