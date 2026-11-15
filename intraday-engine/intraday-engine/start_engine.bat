@echo off
rem Double-click to start intraday-engine. Uses the Python already installed on this laptop.
cd /d "%~dp0"
title intraday-engine (keep this window open)

where python >nul 2>nul
if %errorlevel%==0 (
    python -m engine.app
) else (
    py -3 -m engine.app
)

if errorlevel 1 (
    echo.
    echo The engine stopped with an error. Read the message above.
    pause
)
