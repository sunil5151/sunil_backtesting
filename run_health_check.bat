@echo off
cd /d "%~dp0"
python scripts\daily_health_check.py --sync-github
echo.
echo Done! Press any key to close...
pause >nul
