@echo off
setlocal
set "PROJECT_DIR=%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%scripts\start-preview.ps1"
if errorlevel 1 (
  echo.
  echo OMEGA-ARC did not start. Review the error above.
  pause
  exit /b 1
)

echo.
echo OMEGA-ARC is starting.
echo UI:      http://127.0.0.1:5173/
echo Backend: http://127.0.0.1:8001/
echo Ollama:  http://127.0.0.1:11434/
start "" "http://127.0.0.1:5173/"
