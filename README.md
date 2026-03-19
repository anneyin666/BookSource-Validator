# 阅读书源·净源工坊

开源阅读 App 书源处理工具，当前实现覆盖：
- URL 标准化去重
- 格式校验
- 深度校验
- 批量文件/批量 URL 处理
- 搜索/发现规则校验
- SSE 实时进度与取消
- 失败原因分组、分类和导出

## 功能特性

- `单个处理`：上传本地文件或输入在线链接，执行去重或全部校验
- `批量处理`：合并多个文件或多个 URL 后统一去重校验
- `搜索校验`：验证书源搜索、发现或搜索+发现规则
- `类型过滤`：支持过滤正版、听书、漫画、影视书源
- `深度校验`：模拟手机端请求，支持并发、超时、重试、403 特殊处理
- `URL 安全校验`：在线获取时拦截回环、私网和本地域名
- `结果导出`：导出有效书源或失败书源，保留原有分组并追加新校验分组
- `设置持久化`：记住并发数、超时时间、主题偏好
- `主题切换`：亮色/暗色主题

## 快速开始

### 方式一：一键启动

运行 `start.bat`。

启动后访问：
- 前端：`http://localhost:5173`
- 后端 Swagger：`http://localhost:8000/docs`

停止服务：
- Windows：`stop.bat`
- Linux：`stop-server.sh`

### 方式二：手动启动

后端：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 环境要求

- Python 3.10+
- Node.js 18+

## 当前主要模式

### 单个处理

1. 上传 `.json`/`.txt` 文件，或输入在线书源 URL
2. 选择：
   - `只查重复`
   - `全部校验`
3. 查看统计、失败详情、重复 URL、下载结果

在线 URL 获取会执行基础安全校验，阻止访问回环地址、私网地址和 `.local` / `localhost` 主机。

### 批量处理

1. 批量上传多个文件，或输入多个在线 URL
2. 合并所有来源后统一去重/校验
3. 返回整体结果和来源级统计

### 搜索校验

1. 上传书源文件
2. 选择：
   - `仅搜索`
   - `仅发现`
   - `搜索+发现`
3. 查看规则类型分布、失败分类和详细失败原因

## 核心规则

### URL 标准化

去重时会自动：
- 转小写
- 去除首尾空白
- 去除尾部斜杠
- 去除 `#` 后附带的作者/制作者信息
- 去除直接拼接在 URL 后的中文作者信息

### 分组回写

有效书源会保留原有分组，并追加：

```text
YYYY-MM-DD去重有效XXX条
```

例如：
- 原分组：`优质书源`
- 校验后：`优质书源,2026-03-19去重有效100条`

## 项目结构

```text
shuyuanquchong/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # 路由
│   │   ├── models/           # 请求/响应模型
│   │   └── services/         # 业务服务
│   └── tests/                # pytest 测试
├── frontend/                 # Vue 3 前端（JavaScript）
│   ├── src/
│   │   ├── api/              # API 封装
│   │   ├── components/       # 组件
│   │   ├── composables/      # 状态与工具钩子
│   │   ├── styles/           # 全局样式
│   │   └── utils/            # 下载等工具
├── docs/                     # 设计文档与会话总结
├── Dockerfile
├── docker-compose.yml
├── start.bat
└── deploy.sh
```

## 关键入口

- 后端入口：[backend/app/main.py](backend/app/main.py)
- 核心路由：[backend/app/api/sources.py](backend/app/api/sources.py)
- 前端入口：[frontend/src/App.vue](frontend/src/App.vue)
- 前端状态：[frontend/src/composables/useSources.js](frontend/src/composables/useSources.js)
- 前端 API：[frontend/src/api/sources.js](frontend/src/api/sources.js)

## 文档

- [项目目录结构](docs/项目目录结构.md)
- [系统架构设计](docs/系统架构设计.md)
- [API接口设计](docs/API接口设计.md)
- [前端组件设计](docs/前端组件设计.md)
- [网站功能规划](docs/网站功能规划.md)
- [部署指南](docs/部署指南.md)

## 开发

后端测试：

```bash
cd backend
pytest tests -q
```

会话记录见：

```text
docs/sessions/
```

## License

MIT
