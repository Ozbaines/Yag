@echo off
cd /d "%~dp0"

if exist content.off (
    echo [OFF] Поиск видео отключён ^(файл content.off существует^)
    echo       Чтобы включить: del content.off
    exit /b 0
)

call venv\Scripts\activate.bat

if not exist logs mkdir logs

echo [SEARCH] Ищу видео...
python -m content_engine.main > logs\yag_content.log 2>&1
type logs\yag_content.log
echo [OK] Поиск завершён. Черновики отправлены в бот.
