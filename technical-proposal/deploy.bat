@echo off
REM Windows deploy wrapper. Double-click or run from cmd/PowerShell.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found in PATH.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

python tools\deploy.py %*
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
    echo Deploy succeeded.
) else (
    echo Deploy finished with errors. See output above.
)
pause
exit /b %RC%
