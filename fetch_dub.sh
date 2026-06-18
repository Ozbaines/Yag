#!/bin/bash
# Однократный поиск иностранных видео: скачивает, озвучивает по-русски, отправляет в бот
cd "$(dirname "$0")"

if [ -f "dub.off" ]; then
    echo "🔴 Озвучка отключена (файл dub.off существует)"
    echo "   Чтобы включить: rm dub.off"
    exit 0
fi

source yag-env/bin/activate
pkill -9 -f "python.*dub_factory" 2>/dev/null
sleep 1

echo "🎙 Ищу иностранные видео и озвучиваю по-русски..."
echo "   (каждое видео ~2-3 минуты: скачать + распознать + перевести + озвучить)"
python -m dub_factory.main 2>&1 | tee /tmp/yag_dub.log
echo "✅ Готово. Видео с русской озвучкой отправлены в бот."
