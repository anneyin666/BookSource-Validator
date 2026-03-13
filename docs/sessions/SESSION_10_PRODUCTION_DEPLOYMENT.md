# SESSION_10 生产环境部署配置

## 会话目标

配置生产环境部署，支持云服务器外网访问。

---

## 完成任务

### 1. 后端静态文件服务

**问题描述：**
生产环境需要后端同时提供前端静态文件服务，避免部署 Nginx。

**解决方案：**

修改 `backend/app/main.py`，添加静态文件服务：

```python
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 前端构建后的 dist 目录路径
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

# 检查是否为生产环境（dist 目录存在）
if FRONTEND_DIST.exists() and FRONTEND_DIST.is_dir():
    # 挂载静态资源目录
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

    # SPA 路由处理
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 所有非 API 路由返回 index.html
        ...
```

**工作原理：**

| 请求路径 | 处理方式 |
|----------|----------|
| `/api/*` | API 路由处理 |
| `/assets/*` | 静态文件（JS、CSS、图片） |
| `/` | 返回 index.html |
| `/其他路径` | 返回 index.html（SPA 路由） |

### 2. Linux 启动脚本

**创建文件：**

| 文件 | 说明 |
|------|------|
| `start-server.sh` | 前台启动（可看日志输出） |
| `start-background.sh` | 后台启动（nohup） |
| `stop-server.sh` | 停止服务 |

**start-server.sh 内容：**

```bash
#!/bin/bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**start-background.sh 内容：**

```bash
#!/bin/bash
cd backend
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../app.log 2>&1 &
echo "服务已启动，PID: $!"
echo "日志文件: app.log"
```

**stop-server.sh 内容：**

```bash
#!/bin/bash
PID=$(pgrep -f "uvicorn app.main:app")
if [ -n "$PID" ]; then
    kill $PID
    echo "服务已停止"
fi
```

### 3. 部署文档

创建完整的部署指南 `docs/部署指南.md`，包含：

- 部署架构图
- 环境要求
- 部署步骤
- 配置说明（端口、防火墙、CORS）
- 生产优化（Gunicorn、Systemd、Nginx）
- 常见问题解答

### 4. 关键配置说明

#### 4.1 外网访问配置

启动时必须绑定 `0.0.0.0`：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**错误示例**（仅本机访问）：
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000  # ❌ 外网无法访问
```

#### 4.2 防火墙配置

```bash
# CentOS/RHEL
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent
sudo firewall-cmd --reload

# Ubuntu/Debian
sudo ufw allow 8000/tcp
```

#### 4.3 云服务商安全组

阿里云/腾讯云/AWS 需要在控制台开放安全组端口 8000。

---

## 技术决策

### 1. 单服务架构

**选择：** FastAPI 同时提供 API 和静态文件服务

**理由：**
- 简化部署，无需 Nginx
- 减少运维复杂度
- 适合中小型应用

### 2. SPA 路由处理

**选择：** 所有非 API 路由返回 index.html

**理由：**
- 支持 Vue Router 的 history 模式
- 避免刷新页面 404 错误

### 3. 静态文件路径

**选择：** 使用相对路径 `frontend/dist`

**理由：**
- 项目结构清晰
- 便于开发与生产切换

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/main.py` | 修改 | 添加静态文件服务 |
| `docs/部署指南.md` | 新建 | 完整部署文档 |
| `start-server.sh` | 新建 | Linux 前台启动脚本 |
| `start-background.sh` | 新建 | Linux 后台启动脚本 |
| `stop-server.sh` | 新建 | Linux 停止服务脚本 |
| `README.md` | 修改 | 添加部署文档链接 |

---

## 测试结果

### Python 语法检查
```
Python syntax OK
```

### 单元测试
```
55 passed in 1.60s
```

---

## 部署命令速查

### 开发环境
```bash
# 后端
cd backend && uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm run dev
```

### 生产环境（Linux）

```bash
# 首次部署
cd frontend && npm install && npm run build
cd ../backend && pip install -r requirements.txt

# 前台启动（调试用）
./start-server.sh

# 后台启动（生产用）
./start-background.sh

# 停止服务
./stop-server.sh

# 查看日志
tail -f app.log
```

---

## 访问地址

部署成功后：

| 环境 | 地址 |
|------|------|
| 前端页面 | `http://服务器IP:8000` |
| API 文档 | `http://服务器IP:8000/docs` |
| API 接口 | `http://服务器IP:8000/api/*` |

---

## 后续建议

### 安全加固

1. **HTTPS 配置**
   - 使用 Let's Encrypt 免费证书
   - 配置自动续期
   - 强制 HTTPS 重定向

2. **访问控制**
   - 添加访问速率限制（防止滥用）
   - 配置 IP 白名单（可选）
   - 添加请求签名验证

3. **安全代理**
   - 配置 Nginx 反向代理
   - 隐藏后端服务端口
   - 支持 WebSocket 代理

### 性能优化

1. **Gunicorn 多进程**
   - 使用 Gunicorn + Uvicorn Worker
   - 根据服务器配置调整进程数
   - 支持平滑重启

2. **Systemd 服务**
   - 配置开机自启
   - 自动崩溃恢复
   - 日志轮转配置

3. **资源优化**
   - 启用 Gzip 压缩
   - 静态文件缓存策略
   - CDN 加速静态资源

### 监控告警

1. **健康检查**
   - 配置 `/health` 端点
   - 定时检测服务状态
   - 自动告警通知

2. **日志管理**
   - 结构化日志输出
   - 错误日志告警
   - 日志归档策略

3. **性能监控**
   - Prometheus + Grafana 监控
   - 接口响应时间统计
   - 资源使用率监控

### 运维工具

1. **一键部署脚本**
   - Docker 容器化部署
   - Docker Compose 编排
   - 版本回滚支持

2. **数据备份**
   - 定时备份配置
   - 数据恢复流程
   - 异地容灾方案

---

文档版本：v1.1
创建日期：2026-03-14
更新日期：2026-03-14