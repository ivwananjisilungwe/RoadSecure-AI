@echo off
setlocal
cd /d "%~dp0"
.venv\Scripts\python.exe -m pytest backend\tests || exit /b 1
call npm --prefix frontend run typecheck || exit /b 1
call npm --prefix frontend run build
