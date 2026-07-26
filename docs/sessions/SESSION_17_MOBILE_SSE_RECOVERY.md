# SESSION 17 - 手机端长任务 SSE 断线恢复

## 1. 会话目标

解决手机端校验约 1200 个书源时，页面在保持前台和屏幕常亮的情况下仍可能自行中断，并退回“校验前”状态的问题。

## 2. 根因

问题不在智能并发调度器，而在 SSE 连接生命周期：

- 手机网络、浏览器或反向代理可能让长时间 SSE 连接发生瞬时断流。
- 前端原 `EventSource.onerror` 会立即停止计时、关闭连接并退出校验状态。
- 后端原进度端点每次订阅都会启动新的后台校验任务，直接重连会重复执行同一批书源。
- 后端发送完成、取消或错误消息后立即删除会话，完成瞬间断线时无法重新取回结果。

1200 个书源比常用的 300 个书源运行时间更长，因此更容易遇到瞬时断流。

## 3. 完成任务

### 3.1 后端任务与 SSE 解耦

- 每个 `ValidationSession` 保存唯一 `runner_task`。
- `SessionManager.ensure_runner()` 在锁内保证同一会话只启动一次校验。
- 深度校验和搜索校验的 SSE 重连只订阅当前状态，不重复执行书源请求。
- SSE 客户端断开不会取消服务器后台 runner。
- 重连不会把已暂停的会话误改为运行状态。

### 3.2 终态结果保留

- 完成、取消和错误会话记录 `finished_at`。
- 终态结果在内存中保留 30 分钟。
- 同一 `sessionId` 重连后可再次收到完整终态结果。
- 创建或查询会话时惰性清理超过保留时间的终态会话，避免长期占用内存。

### 3.3 手机端自动重连

- 前端发生瞬时 `error` 时不再调用 `EventSource.close()`。
- 不停止计时器，不将 `validating` 设为 `false`，进度卡片不会退回校验前。
- 使用浏览器原生 EventSource 自动重连同一进度地址。
- 断线时进度区显示“连接恢复中，服务器仍在校验...”。
- 首次断线显示 Toast，连接恢复后显示“连接已恢复”。
- 文件、在线 URL、批量、搜索和失败重试五个入口统一使用恢复逻辑。

### 3.4 生产代理配置

部署指南中的 Nginx/OpenResty 示例增加：

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

1Panel 部署需要把这些配置保留在网站反向代理配置中，并重载 OpenResty/Nginx。

## 4. 技术决策

- 优先使用浏览器原生 EventSource 重连，不额外实现一套 JavaScript 重试计时器。
- runner 归后端会话所有，不归任意一个 SSE 请求所有。
- 结果保留使用内存和惰性清理，适合当前 2 核 2G、小圈子使用场景。
- 本轮不实现页面刷新或浏览器进程被系统销毁后的恢复。
- 服务重启仍会丢失内存会话；如后续需要跨重启恢复，应引入持久化任务存储。

## 5. 修改文件清单

| 文件 | 说明 |
|------|------|
| `backend/app/services/session_manager.py` | 单 runner 所有权、终态时间和 30 分钟清理 |
| `backend/app/api/sources.py` | 深度与搜索 SSE 只订阅同一后台任务 |
| `backend/tests/test_session_recovery.py` | runner 唯一性和过期清理测试 |
| `backend/tests/test_adaptive_validation_sse.py` | 完成结果重放且不重复校验的集成测试 |
| `frontend/src/utils/eventSourceRecovery.js` | EventSource 自动恢复辅助模块 |
| `frontend/tests/eventSourceRecovery.test.js` | 前端断线与恢复单元测试 |
| `frontend/src/App.vue` | 五个校验入口接入恢复逻辑 |
| `frontend/src/components/ValidationProgress.vue` | 连接恢复状态文案 |
| `frontend/package.json` | 增加前端测试命令 |
| `docs/部署指南.md` | 1Panel/Nginx SSE 反向代理配置 |
| `docs/FUTURE_SUGGESTIONS.md` | 更新 SSE 恢复能力状态 |

## 6. 测试结果

### 6.1 后端

```powershell
cd backend
python -m pytest tests/ -v
python -m compileall app
```

结果：19 个测试全部通过，Python 编译通过。pytest 仅保留 FastAPI `on_event` 的既有弃用警告。

定向静态检查：

```powershell
python -m flake8 app/services/session_manager.py tests/test_session_recovery.py --max-line-length=120
python -m flake8 app/api/sources.py --select=E9,F63,F7,F821
```

结果：通过。

### 6.2 前端

```powershell
cd frontend
npm test
npm run build
```

结果：2 个 EventSource 恢复测试全部通过，Vite 生产构建通过。

## 7. 功能验证清单

- 手机保持前台和屏幕常亮时执行约 1200 个书源校验。
- 连接正常时进度持续更新，计时器不中断。
- 临时切换 Wi-Fi/移动网络或制造短时网络抖动后，页面保持进度卡片。
- 断线时显示“连接恢复中，服务器仍在校验...”。
- 恢复后收到 Toast，并继续显示同一批次的后续进度。
- 服务日志中同一 `session_id` 只出现一次校验开始和一次校验完成。
- 完成后 30 分钟内重新订阅同一进度地址仍能取得相同结果。
- 1Panel 的 OpenResty/Nginx 配置已关闭 SSE 缓冲并使用 3600 秒超时。

## 8. 使用说明

服务器拉取代码并重新构建前端后，检查 1Panel 反向代理配置，再重启应用服务和重载 OpenResty/Nginx。建议先用 50 个书源制造一次短时断网测试恢复，再使用原 1200 个书源完成整批复测。

## 9. 后续建议

- 增加页面刷新后的最近会话恢复，需保存少量会话类型和结果组装元数据。
- 增加定期后台清理任务，降低只创建不查询场景下终态会话的内存驻留时间。
- 增加全局运行任务上限，避免多人同时提交超大批次耗尽 2 核 2G 服务器资源。
- 根据生产日志判断是否需要额外 SSE 心跳；当前进度流约每 0.3 秒已有数据，不是首要瓶颈。

---

文档版本：v1.0
创建日期：2026-07-26
