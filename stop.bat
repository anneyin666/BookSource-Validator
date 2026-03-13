@echo off
echo ========================================
echo   Stopping all services...
echo ========================================
echo.

:: Stop backend
taskkill /f /im python.exe 2>nul
echo [OK] Backend stopped

:: Stop frontend
taskkill /f /im node.exe 2>nul
echo [OK] Frontend stopped

echo.
echo All services stopped.
pause