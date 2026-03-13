#!/bin/bash

# 阅读书源去重校验工具 - Linux 后台启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

# 启动后台服务
echo "启动后台服务..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../app.log 2>&1 &

echo "服务已启动，PID: $!"
echo "访问地址: http://服务器IP:8000"
echo "日志文件: $SCRIPT_DIR/app.log"
echo ""
echo "查看日志: tail -f $SCRIPT_DIR/app.log"
echo "停止服务: kill $!"