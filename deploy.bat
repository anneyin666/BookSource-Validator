@echo off
chcp 65001 >nul
REM 阅读书源去重校验工具 - Docker 一键部署脚本 (Windows)

echo ======================================
echo   阅读书源去重校验工具 - Docker 部署
echo ======================================
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    echo    下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 切换到脚本所在目录
cd /d "%~dp0"

echo 📦 构建 Docker 镜像...
docker-compose build

echo.
echo 🚀 启动容器...
docker-compose up -d

echo.
echo ⏳ 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo ❌ 服务启动失败，请检查日志:
    echo    docker-compose logs
    pause
    exit /b 1
)

echo.
echo ======================================
echo   ✅ 部署成功！
echo ======================================
echo.
echo 访问地址:
echo   前端页面: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo.
echo 常用命令:
echo   查看日志:   docker-compose logs -f
echo   停止服务:   docker-compose down
echo   重启服务:   docker-compose restart
echo   更新部署:   git pull ^&^& docker-compose up -d --build
echo.
pause