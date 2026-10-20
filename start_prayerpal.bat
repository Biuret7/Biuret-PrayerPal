@echo off
cd /d "%~dp0"
py prayerpal.py
if errorlevel 1 pause
