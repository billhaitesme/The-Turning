@echo off
cd /d "%~dp0"
py -3.13 -m venv .venv
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"
echo Setup complete.
pause
