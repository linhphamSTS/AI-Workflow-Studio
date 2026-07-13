@echo off
REM One-time installer for the whole monorepo (Windows): deploys both skills + sets up the web app.
cd /d "%~dp0"

set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
  echo.
  echo [!] Python 3.10+ was not found. Install it from https://www.python.org/downloads/
  echo     ^(tick "Add python.exe to PATH"^), then run this again.
  echo.
  pause
  exit /b 1
)

%PYEXE% install.py
if errorlevel 1 pause
