@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies. Check Python and internet connection.
  pause
  exit /b 1
)
py prayerpal.py
if errorlevel 1 pause
