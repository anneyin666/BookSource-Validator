@echo off
chcp 65001 >nul
echo ====================================
echo   阅读书源去重校验工具 - 部署启动
echo ====================================
echo.

cd /d "%~dp0"

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo [1/4] 安装后端依赖...
cd backend
pip install -r requirements.txt -q

echo [2/4] 安装前端依赖...
cd ..\frontend
call npm install --silent

echo [3/4] 构建前端...
call npm run build

echo [4/4] 启动后端服务...
cd ..\backend
echo.
echo ====================================
echo   服务已启动
echo   前端地址: http://你的服务器IP:8000
echo   API文档:  http://你的服务器IP:8000/docs
echo ====================================
echo.
echo 按 Ctrl+C 停止服务
uvicorn app.main:app --host 0.0.0.0 --port 8000