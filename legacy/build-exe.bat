@echo off
cd /d "%~dp0"
echo Building Sweep.exe ...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-exe.ps1"
echo.
if exist "Sweep.exe" (echo OK: Sweep.exe is ready.) else (echo FAILED: Sweep.exe was not created. Make a screenshot of this window.)
pause
