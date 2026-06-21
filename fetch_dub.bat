@echo off
cd /d "%~dp0"

if exist dub.off (
    echo [OFF] Озвучка отключена ^(файл dub.off существует^)
    echo       Чтобы включить: del dub.off
    exit /b 0
)

call venv\Scripts\activate.bat

if not exist logs mkdir logs

echo [DUB] Ищу видео с канала и озвучиваю по-русски...
echo       ^(скачать + расшифровать + перевести + XTTS озвучить + смонтировать^)
python -m dub_factory.main %* > logs\yag_dub.log 2>&1
type logs\yag_dub.log
echo [OK] Готово. Видео с русской озвучкой отправлены в бот.
