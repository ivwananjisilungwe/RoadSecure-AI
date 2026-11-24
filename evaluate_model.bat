@echo off
setlocal
cd /d "%~dp0"
if not defined ROADSECURE_DATA_DIR set "ROADSECURE_DATA_DIR=%~dp0database\runtime"
.venv\Scripts\python.exe -m backend.app.detection evaluate
