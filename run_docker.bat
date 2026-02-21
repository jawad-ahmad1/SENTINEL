@echo off
cd /d "%~dp0"
echo ===================================================
echo   RFID Attendance System - Production Launcher
echo ===================================================
echo.
echo [1/3] Building Containers...
docker compose build
if %errorlevel% neq 0 (
    echo [ERROR] Docker Build Failed. Is Docker Desktop running?
    pause
    exit /b
)

echo.
echo [2/3] Starting Services (Detached)...
docker compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Docker Up Failed.
    pause
    exit /b
)

echo.
echo [3/3] Running Migrations...
docker compose exec app alembic upgrade head

echo.
echo ===================================================
echo   SYSTEM IS LIVE
echo ===================================================
echo.
echo Frontend: http://localhost
echo API Docs: http://localhost/docs
echo.
echo Credentials (Production):
echo   User: admin@attendance.local
echo   Pass: changeme123
echo.
echo To stop: Type command 'docker compose down'
pause
