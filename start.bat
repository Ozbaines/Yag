@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat

echo Останавливаем старые процессы...
taskkill /F /FI "WINDOWTITLE eq yag_admin*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq yag_video*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq yag_publisher*" >nul 2>&1
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
    wmic process where "ProcessId=%%i and CommandLine like '%%tg_admin_bot%%'" delete >nul 2>&1
    wmic process where "ProcessId=%%i and CommandLine like '%%video_factory%%'" delete >nul 2>&1
    wmic process where "ProcessId=%%i and CommandLine like '%%publisher%%'" delete >nul 2>&1
)

echo Ожидаем освобождения сессии бота...
timeout /t 5 /nobreak >nul

start "yag_admin"     cmd /c "python -m tg_admin_bot.main  > logs\yag_admin.log    2>&1"
start "yag_video"     cmd /c "python -m video_factory.main > logs\yag_video.log    2>&1"
start "yag_publisher" cmd /c "python -m publisher.main     > logs\yag_publisher.log 2>&1"

echo.
echo [OK] Сервисы запущены
echo      Admin bot     -^> logs\yag_admin.log
echo      Video factory -^> logs\yag_video.log
echo      Publisher     -^> logs\yag_publisher.log
