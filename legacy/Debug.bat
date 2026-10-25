@echo off
cd /d "%~dp0"
echo Starting Sweep in debug mode. If the window does not appear, the error will be printed below.
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0Sweep.ps1"
echo.
echo Exit code: %errorlevel%
pause
