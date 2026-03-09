@echo off
cd /d "%~dp0"
echo ===================================================
echo   RFID Attendance System - Local Launcher
echo ===================================================
echo.
echo [INFO] Setting SQLite Local Mode...
set DATABASE_URL=sqlite+aiosqlite:///./local.db
set LOG_LEVEL=INFO
set AUTO_CREATE_SCHEMA=false

echo [INFO] Access URL: http://127.0.0.1:8000
echo [INFO] Login:      admin@attendance.local / changeme123
echo.
echo [INFO] Applying migrations...
venv\Scripts\python.exe -m alembic upgrade head
if %errorlevel% neq 0 (
    echo [ERROR] Migration step failed.
    pause
    exit /b
)

echo.
echo [INFO] Starting Server...
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo [EXIT] Server stopped.
pause
