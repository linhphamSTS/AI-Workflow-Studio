@echo off
REM Deploy the linhpham-diagram skill into every Claude profile on this machine.
python "%~dp0tools\deploy.py" %*
