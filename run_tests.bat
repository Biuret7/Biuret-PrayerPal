@echo off
setlocal
cd /d "%~dp0"
if not exist ".test-tmp" mkdir ".test-tmp"
set "TEMP=%~dp0.test-tmp"
set "TMP=%TEMP%"
py prayerpal.py --self-test
set "TEST_RESULT=%errorlevel%"
pause
exit /b %TEST_RESULT%
