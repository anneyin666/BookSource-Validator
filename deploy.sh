#!/bin/bash

# 阅读书源去重校验工具 - Docker 一键部署脚本
# 适用于 Linux 服务器

set -e

echo "======================================"
echo "  阅读书源去重校验工具 - Docker 部署"
echo "======================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    echo "   安装命令: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    echo "   Docker 20.10+ 已内置 compose，请更新 Docker"
    exit 1
fi

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "📦 构建 Docker 镜像..."
docker-compose build

echo ""
echo "🚀 启动容器..."
docker-compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "======================================"
    echo "  ✅ 部署成功！"
    echo "======================================"
    echo ""
    echo "访问地址:"
    echo "  前端页面: http://localhost:8000"
    echo "  API 文档: http://localhost:8000/docs"
    echo ""
    echo "常用命令:"
    echo "  查看日志:   docker-compose logs -f"
    echo "  停止服务:   docker-compose down"
    echo "  重启服务:   docker-compose restart"
    echo "  更新部署:   git pull && docker-compose up -d --build"
    echo ""
else
    echo "❌ 服务启动失败，请检查日志:"
    echo "   docker-compose logs"
    exit 1
fi