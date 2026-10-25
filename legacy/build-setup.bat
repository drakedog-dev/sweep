@echo off
cd /d "%~dp0"
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Inno Setup 6 not found. Download it from jrsoftware.org/isdl.php, install, then run this file again.
  pause
  exit /b 1
)
if not exist "Sweep.exe" (
  echo Sweep.exe not found. Run build-exe.ps1 first ^(right click, Run with PowerShell^).
  pause
  exit /b 1
)
"%ISCC%" "Sweep.iss"
echo.
echo Done. The installer is in the Output folder.
pause
