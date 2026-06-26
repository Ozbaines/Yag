@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist Yag\Scripts\activate.bat (
    call Yag\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] venv не найден. Создай: python -m venv Yag
    exit /b 1
)

if not exist logs mkdir logs

echo [DUB] Ищу видео с канала и озвучиваю по-русски...
echo       (скачать + расшифровать + перевести + XTTS озвучить + смонтировать)
python -m dub_factory.main %* > logs\yag_dub.log 2>&1
type logs\yag_dub.log
echo [OK] Готово. Видео с русской озвучкой отправлены в бот.
