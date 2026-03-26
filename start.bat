@echo off
chcp 65001 >nul
echo ========================================
echo   阅读书源去重校验工具 - 手机真机测试模式
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
start "Backend" cmd /k python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

echo [4/4] Starting frontend server (port 5173)...
cd ..\frontend
start "Frontend" cmd /k npm run dev:mobile

cd ..

set "LAN_IP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$text = ipconfig; $preferred = @('Wireless LAN adapter WLAN','Wireless LAN adapter Wi-Fi','无线局域网适配器 WLAN','无线局域网适配器 Wi-Fi'); foreach ($adapter in $preferred) { $pattern = '(?ms)' + [regex]::Escape($adapter) + '\s*:.*?(?:\r?\n\r?\n|$)'; $section = [regex]::Match($text, $pattern).Value; if ($section -match 'IPv4 Address[^\d]*((?:\d{1,3}\.){3}\d{1,3})') { $matches[1]; exit } }; $fallback = [regex]::Matches($text, '(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)') | ForEach-Object { $_.Value } | Where-Object { $_ -notlike '127.*' -and $_ -notlike '169.254*' } | Select-Object -First 1; if ($fallback) { $fallback }"`) do set "LAN_IP=%%i"

echo.
echo ========================================
echo   手机真机测试服务已启动
echo ========================================
echo.
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
if defined LAN_IP (
echo   手机访问: http://%LAN_IP%:5173
) else (
echo   手机访问: http://你的电脑局域网IP:5173
)
echo.
echo   说明:
echo   1. 手机和电脑需要连接同一 Wi-Fi
echo   2. 手机浏览器访问上面的“手机访问”地址
echo   3. “导出到阅读 App”需要手机已安装阅读 App
echo.
echo   按任意键打开本机浏览器...
pause >nul

start http://localhost:5173
