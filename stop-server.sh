#!/bin/bash

# 阅读书源去重校验工具 - 停止服务脚本

echo "正在停止服务..."

# 查找并停止 uvicorn 进程
PID=$(pgrep -f "uvicorn app.main:app")

if [ -n "$PID" ]; then
    kill $PID
    echo "服务已停止 (PID: $PID)"
else
    echo "未找到运行中的服务"
fi