@echo off
title OMEGA-ARC
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0OMEGA-ARC-Launcher.ps1"
if errorlevel 1 pause
