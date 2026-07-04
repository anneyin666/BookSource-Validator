# SESSION_14 日志轮转与服务日志查看

## 会话目标

在不增加额外部署依赖的前提下，实现后端服务日志和日志轮转能力，并保证 Windows 本地开发与 Linux 服务器部署都可用。重点满足 1Panel 运维场景下直接查看日志、排查校验慢任务、反馈提交和服务异常。

---

## 完成任务

### 1. 新增统一日志配置

新增 `backend/app/logging_config.py`，使用 Python 标准库 `logging.handlers.RotatingFileHandler`。

默认行为：

- 日志路径：`backend/logs/app.log`
- 单文件大小：10MB
- 保留轮转文件：7 个
- 编码：UTF-8
- 控制台输出默认开启
- `httpx` 和 `httpcore` 日志降为 `WARNING`，避免正常校验时刷屏

支持环境变量：

- `APP_LOG_LEVEL`
- `APP_LOG_DIR`
- `APP_LOG_FILE`
- `APP_LOG_MAX_BYTES`
- `APP_LOG_BACKUP_COUNT`
- `APP_LOG_CONSOLE`

### 2. FastAPI 应用接入日志

在 `backend/app/main.py` 启动时配置日志，并记录：

- 服务启动
- 服务关闭
- 未捕获请求异常
- HTTP 4xx/5xx 请求
- 超过 10 秒的慢请求

### 3. 校验链路关键日志

在 `backend/app/api/sources.py` 中补充关键业务日志：

- 普通解析/全部校验完成日志
- SSE 校验会话创建日志
- SSE 校验完成日志
- SSE 校验取消日志
- 批量文件 SSE 会话创建日志
- 批量 URL SSE 会话创建日志
- 搜索校验会话创建日志
- 搜索校验完成、取消和异常日志

超过 5 分钟的校验批次会使用 `WARNING` 级别记录，方便在服务器上快速定位慢任务。

### 4. 反馈提交日志

在 `backend/app/api/feedback.py` 中增加反馈保存日志。

日志只记录：

- 来源 IP
- 反馈正文长度
- 是否填写联系方式
- 写入文件路径

不会记录完整反馈正文，避免日志中保存过多隐私内容。

### 5. Linux 查看方式文档

更新 `docs/部署指南.md`，补充 Linux 和 1Panel 查看方式：

```bash
cd /path/to/BookSource-Validator/backend
tail -f logs/app.log
```

后台启动示例调整为：

```bash
cd backend
mkdir -p logs
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
```

### 6. 后续建议文档同步

更新 `docs/FUTURE_SUGGESTIONS.md`，将“日志轮转与服务日志查看”标记为基础能力已落地，并保留后续结构化日志、错误告警等增强方向。

---

## 技术决策

- 不新增第三方日志依赖，降低 Linux 服务器部署复杂度。
- 不默认开放网页日志查看接口，避免日志内容暴露到公网。
- 应用日志写入 `backend/logs/app.log`，Uvicorn 标准输出可单独重定向到 `backend/logs/uvicorn.log`。
- 日志目录继续由 `.gitignore` 忽略，避免运行日志提交到 GitHub。

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/logging_config.py` | 新增 | 统一日志配置与轮转 |
| `backend/app/main.py` | 修改 | 应用启动接入日志，记录启动/关闭/异常/慢请求 |
| `backend/app/api/sources.py` | 修改 | 校验链路关键日志与慢任务日志 |
| `backend/app/api/feedback.py` | 修改 | 反馈提交事件日志 |
| `docs/部署指南.md` | 修改 | Linux/1Panel 日志查看说明 |
| `docs/FUTURE_SUGGESTIONS.md` | 修改 | 标记日志轮转基础能力已落地 |

---

## 测试结果

### 1. Python 语法检查

```bash
cd backend
python -m py_compile app\logging_config.py app\main.py app\api\sources.py app\api\feedback.py
```

结果：通过。

### 2. FastAPI 导入与路由检查

```powershell
$env:DEBUG='true'
python -c "from app.main import app, LOG_FILE_PATH; print(LOG_FILE_PATH); print(any(getattr(r, 'path', '') == '/api/feedback' for r in app.routes))"
```

结果：

```text
E:\shuyuanquchong\backend\logs\app.log
True
```

### 3. TestClient 健康检查

```powershell
$env:DEBUG='true'
python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); c.__enter__(); r=c.get('/api/health'); print(r.status_code, r.json()); c.__exit__(None, None, None)"
```

结果：

```text
200 {'status': 'ok'}
```

并确认 `backend/logs/app.log` 中写入服务启动和关闭日志。

### 4. pytest

```bash
cd backend
pytest tests/ -v
```

结果：未运行。当前仓库 `backend/tests/` 不存在，pytest 返回 `file or directory not found: tests/`。

### 5. flake8

```bash
cd backend
python -m flake8 app\logging_config.py app\main.py app\api\feedback.py
```

结果：未运行。当前 Python 环境未安装 `flake8`。

---

## 功能验证清单

- 服务启动后是否自动创建 `backend/logs/app.log`
- Linux 上是否可以使用 `tail -f logs/app.log` 查看实时日志
- 1Panel 文件管理中是否可以直接打开 `backend/logs/app.log`
- 校验完成后是否记录总数、有效数、失败数、并发数、超时时间和耗时
- 超过 5 分钟的校验批次是否以 `WARNING` 记录
- 反馈提交后是否记录提交事件且不打印完整反馈正文
- 日志文件超过配置大小后是否生成轮转文件

---

## 使用说明

Linux 服务器查看应用日志：

```bash
cd /path/to/BookSource-Validator/backend
tail -f logs/app.log
```

查看最近 100 行：

```bash
tail -n 100 logs/app.log
```

调整轮转大小和保留数量：

```bash
export APP_LOG_MAX_BYTES=5242880
export APP_LOG_BACKUP_COUNT=10
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 后续建议

- 如果后续访问人数增加，可增加简单鉴权后的日志摘要页面，但不建议直接公开完整日志。
- 可以进一步把校验日志结构化，便于按 `session_id` 查询一次任务的完整链路。
- 如果 1Panel 已能满足查看需求，暂时不需要引入 ELK、Prometheus 等复杂监控系统。

---

文档版本：v1.0
创建日期：2026-07-04
