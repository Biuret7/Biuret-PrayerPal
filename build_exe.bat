@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-build\Scripts\python.exe" (
    py -3 -m venv .venv-build
    if errorlevel 1 goto :failed
)
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed
".venv-build\Scripts\python.exe" build.py %*
if errorlevel 1 goto :failed
echo.
echo Build complete: release\BiuretPrayerPal.exe
pause
exit /b 0
:failed
echo.
echo Build failed. Read the error above and artifacts\build\ logs.
pause
exit /b 1
