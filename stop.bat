@echo off
echo Останавливаем все сервисы YAg...
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
    wmic process where "ProcessId=%%i and CommandLine like '%%tg_admin_bot%%'" delete >nul 2>&1
    wmic process where "ProcessId=%%i and CommandLine like '%%video_factory%%'" delete >nul 2>&1
    wmic process where "ProcessId=%%i and CommandLine like '%%publisher%%'" delete >nul 2>&1
    wmic process where "ProcessId=%%i and CommandLine like '%%content_engine%%'" delete >nul 2>&1
    wmic process where "ProcessId=%%i and CommandLine like '%%dub_factory%%'" delete >nul 2>&1
)
echo [STOP] Все сервисы остановлены
