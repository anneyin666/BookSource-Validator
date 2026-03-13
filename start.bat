@echo off
echo ========================================
echo   Book Source Tool - Starting...
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

:: Check backend dependencies
echo [1/4] Checking backend dependencies...
cd backend
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo       Installing backend dependencies...
    pip install -r requirements.txt -q
) else (
    echo       Backend dependencies already installed.
)

:: Check frontend dependencies
echo [2/4] Checking frontend dependencies...
cd ..\frontend
if not exist "node_modules" (
    echo       Installing frontend dependencies...
    call npm install --silent
) else (
    echo       Frontend dependencies already installed.
)

echo [3/4] Starting backend server (port 8000)...
cd ..\backend
start "Backend" cmd /k python -m uvicorn app.main:app --reload --port 8000

echo [4/4] Starting frontend server (port 5173)...
cd ..\frontend
start "Frontend" cmd /k npm run dev

cd ..

echo.
echo ========================================
echo   Started successfully!
echo ========================================
echo.
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo.
echo   Press any key to open browser...
pause >nul

start http://localhost:5173