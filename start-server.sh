#!/bin/bash

# 阅读书源去重校验工具 - Linux 启动脚本

echo "======================================"
echo "  阅读书源去重校验工具 - 生产环境"
echo "======================================"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查前端是否已构建
if [ ! -d "frontend/dist" ]; then
    echo "[1/3] 前端未构建，开始构建..."
    cd frontend
    npm install
    npm run build
    cd ..
else
    echo "[1/3] 前端已构建，跳过"
fi

# 检查后端依赖
echo "[2/3] 检查后端依赖..."
cd backend
if [ ! -d "venv" ]; then
    echo "    创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q
cd ..

# 启动服务
echo "[3/3] 启动服务..."
echo ""
echo "服务地址: http://0.0.0.0:8000"
echo "API 文档: http://0.0.0.0:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "--------------------------------------"

cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000