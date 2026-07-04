# SESSION_15 智能并发超时策略与校验恢复能力

## 会话目标

围绕 `docs/FUTURE_SUGGESTIONS.md` 中 P0 校验链路可靠性继续优化，重点实现：

- 更灵活的并发与超时参数
- 快速 / 均衡 / 稳定 / 自定义预设模式
- 深度校验的智能降并发与动态超时
- 指数退避重试
- 暂停 / 恢复校验
- 取消校验后保留已完成结果
- 失败书源批量重试，以及仅重试网络 / 超时类失败

---

## 完成任务

### 1. 智能策略模块

新增 `backend/app/services/validation_strategy.py`，集中处理：

- 并发范围：1-64
- 超时范围：5-120 秒
- 预设模式：
  - 快速：32 并发 / 15 秒 / 1 次重试
  - 均衡：16 并发 / 30 秒 / 2 次重试
  - 稳定：8 并发 / 45 秒 / 3 次重试
  - 自定义：使用用户手动输入值
- 指数退避：按重试次数递增等待时间
- 网络 / 超时类失败原因识别
- 深度校验动态策略状态：
  - 当前并发
  - 当前超时
  - 最近错误率
  - 最近响应耗时

### 2. 深度校验动态调度

深度校验 SSE 从固定 `Semaphore` 批量任务模式调整为动态补充任务：

- 根据当前策略决定最多同时跑多少请求
- 错误率高、网络错误多或响应变慢时自动降低当前并发
- 响应慢或超时类错误多时自动提高当前请求超时
- 情况稳定时逐步恢复并发
- SSE 进度中返回当前策略状态，前端可展示当前并发与超时

### 3. 搜索校验恢复能力

搜索校验已接入：

- 预设模式参数
- 指数退避重试
- 暂停 / 恢复
- 取消保留已完成结果
- 从失败书源数据重新发起搜索校验

说明：搜索校验当前仍沿用原有固定任务池，尚未完全改为深度校验同款动态调度器。原因是搜索校验内部包含搜索、发现、组合模式三套分支，建议后续单独重构，降低一次性改动风险。

### 4. 暂停 / 恢复 / 取消保留结果

新增后端接口：

```http
POST /api/validate/pause
POST /api/validate/resume
```

取消接口保持：

```http
POST /api/validate/cancel
```

行为说明：

- 暂停不会强制中断已经发出的 HTTP 请求
- 暂停后队列中的后续请求停止启动
- 恢复后继续启动剩余请求
- 取消后返回已完成的有效书源和失败分组
- 前端不再在点击取消后立即关闭 SSE，而是等待后端返回 partial 结果

### 5. 失败书源重试

结果区新增操作：

- 重试全部失败
- 仅重试网络 / 超时
- 导出失败书源

重试逻辑：

- 深度校验失败项会保留原始书源字段，方便重试和导出
- 搜索校验失败项可从失败书源数据重新发起搜索校验
- 重试完成后将新通过的书源合并回原结果
- 未重试或仍失败的书源继续保留在失败区

### 6. 前端参数体验

调整前端组件：

- `ConcurrencySelector.vue` 从固定下拉改为 1-64 输入
- `TimeoutSelector.vue` 从固定下拉改为 5-120 秒输入
- 新增 `ValidationPresetSelector.vue`
- `ValidationProgress.vue` 增加：
  - 当前策略显示
  - 暂停按钮
  - 继续按钮
  - 取消并保留结果按钮

---

## 技术决策

- 深度校验优先实现真正动态调度，因为它是服务器耗时大头。
- 搜索校验先接入恢复能力和重试策略，不在本轮重构全部分支调度器。
- 暂停采用协作式暂停：已发出的请求先完成，未启动的请求等待恢复。
- 取消采用保留已完成结果，不再把已经校验完的数据丢掉。
- 失败重试优先在前端做结果合并，避免新增复杂的后端任务历史存储。

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/validation_strategy.py` | 新增 | 智能策略、预设、指数退避、可重试原因 |
| `backend/app/services/session_manager.py` | 修改 | 会话支持暂停、恢复、策略状态和重试次数 |
| `backend/app/services/validator.py` | 修改 | 深度校验支持指数退避、动态超时、保留完整失败书源 |
| `backend/app/services/search_validator.py` | 修改 | 搜索/发现校验支持指数退避和可配置重试次数 |
| `backend/app/api/sources.py` | 修改 | 接入预设模式、动态调度、暂停/恢复、partial 结果、搜索失败重试入口 |
| `backend/app/models/request.py` | 修改 | 扩展并发/超时范围和策略参数 |
| `frontend/src/api/sources.js` | 修改 | 接入策略参数、暂停/恢复、搜索数据重试 API |
| `frontend/src/components/ConcurrencySelector.vue` | 修改 | 并发支持 1-64 输入 |
| `frontend/src/components/TimeoutSelector.vue` | 修改 | 超时支持 5-120 秒输入 |
| `frontend/src/components/ValidationPresetSelector.vue` | 新增 | 快速/均衡/稳定/自定义预设 |
| `frontend/src/components/ValidationProgress.vue` | 修改 | 暂停/继续/取消保留结果、策略状态展示 |
| `frontend/src/components/SearchValidator.vue` | 修改 | 搜索校验接入预设模式 |
| `frontend/src/App.vue` | 修改 | 全链路参数传递、失败重试、partial 结果合并 |
| `docs/FUTURE_SUGGESTIONS.md` | 修改 | 标记基础能力已落地并补后续增强方向 |

---

## 测试结果

### 1. 后端语法检查

```bash
cd backend
python -m py_compile app\services\validation_strategy.py app\services\session_manager.py app\services\validator.py app\services\search_validator.py app\api\sources.py app\models\request.py
```

结果：通过。

### 2. FastAPI 健康检查

```powershell
$env:DEBUG='true'
python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); r=c.get('/api/health'); print(r.status_code, r.json())"
```

结果：

```text
200 {'status': 'ok'}
```

### 3. 前端构建

```bash
cd frontend
npm run build
```

结果：通过。

---

## 功能验证清单

- 预设模式切换后是否同步修改并发和超时
- 自定义模式下是否可输入 1-64 并发、5-120 秒超时
- 深度校验进度条是否显示当前策略状态
- 深度校验错误率高时当前并发是否会下降
- 暂停后进度是否停止启动新请求
- 恢复后是否继续校验
- 取消后是否展示已完成结果
- 失败详情区是否可重试全部失败
- 失败详情区是否可仅重试网络 / 超时类失败
- 搜索校验失败结果是否可重新发起重试

---

## 后续建议

- 将搜索校验也重构为与深度校验一致的动态调度器。
- 增加按域名维度的响应耗时统计，避免某个慢站影响整批策略。
- 在服务日志中记录智能策略调整原因，例如错误率、平均耗时、降并发前后值。
- 增加 SSE 断线后的会话恢复，而不是只依赖手机保持前台。

---

---

## 本轮 UI 修正

- 修复策略区在非自定义模式下仍占出参数区域的问题：快速、均衡、稳定模式只显示策略按钮，不显示并发数和超时时间。
- 修复自定义模式下参数标签被隐藏的问题：选择自定义后恢复显示“并发数：”“⏱️ 超时时间：”和“秒”。
- 修复策略、并发、超时组件的中文文案显示异常，避免页面出现乱码或只剩帮助图标。
- 保留自定义参数的灵活输入能力：并发数 1-64，超时时间 5-120 秒。
- 检查自定义参数链路：前端会传递 `validation_mode=custom`，后端会使用用户输入值创建校验会话，不会被预设覆盖。
- 将超时时间输入同步改为与并发数一致的实时同步，避免移动端输入后未触发变更事件导致参数未生效。
- 修复自定义参数控件未显示的问题：补充注册 Element Plus 的 `ElInputNumber` 组件。
- 调整策略默认值：页面刷新后默认回到“均衡”，不再从本地缓存恢复为上次选择的“自定义”。

### 追加验证

```bash
cd frontend
npm run build
```

结果：通过。

### 自定义参数接口检查

```bash
cd backend
$env:DEBUG='false'
python -c "from app.services.validation_strategy import normalize_validation_options; o=normalize_validation_options(7, 55, 'custom'); print(o.concurrency, o.timeout, o.mode)"
```

结果：`7 55 custom`，通过。

---

文档版本：v1.1
创建日期：2026-07-04
