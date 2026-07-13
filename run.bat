@echo off
REM Start the shared web app (Windows). Runs install-on-first-use, then opens the browser.
cd /d "%~dp0"
call webapp\run.bat %*
