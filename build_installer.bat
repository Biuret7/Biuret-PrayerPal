@echo off
setlocal
cd /d "%~dp0"
if exist ".venv-build\Scripts\python.exe" (
  ".venv-build\Scripts\python.exe" build_installer.py %*
) else (
  py build_installer.py %*
)
set "prayerpal_exit=%ERRORLEVEL%"
if not "%prayerpal_exit%"=="0" echo Installer build failed. See artifacts\installer\.
pause
exit /b %prayerpal_exit%
