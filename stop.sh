#!/bin/bash
# Останавливает все сервисы YAg
pkill -9 -f "python.*content_engine" 2>/dev/null
pkill -9 -f "python.*tg_admin_bot"   2>/dev/null
pkill -9 -f "python.*video_factory"  2>/dev/null
pkill -9 -f "python.*publisher"      2>/dev/null
echo "⛔ Все сервисы остановлены"
