@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Install Python 3.12 with the Windows Python launcher. & exit /b 1)
where node >nul 2>nul || (echo Install a supported Node.js LTS release. & exit /b 1)
if not exist .venv\Scripts\python.exe (
    py -3.12 -m venv .venv || exit /b 1
)
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || exit /b 1
call npm --prefix frontend ci || exit /b 1
call "%~dp0train_model.bat" || exit /b 1
echo Setup complete. Run start.bat to initialize or reopen the local database.
