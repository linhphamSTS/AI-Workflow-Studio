@echo off
REM Diagram Workflow - one-click launcher (Windows).
REM First run installs everything into webapp\.venv, then starts the app.
cd /d "%~dp0"

set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py -3"
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
  echo.
  echo [!] Python 3.10+ was not found.
  echo     Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"),
  echo     then double-click this file again.
  echo.
  pause
  exit /b 1
)

%PYEXE% launch.py
if errorlevel 1 pause
