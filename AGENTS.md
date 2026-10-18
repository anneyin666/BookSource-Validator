# AGENTS.md

此文件为 AI（Codex.ai/Code/GLM/Qwen）在此代码库中工作时提供指导。

---

## 项目概述

**阅读书源·净源工坊** - 开源阅读 App 书源去重校验工具

一个基于 FastAPI + Vue 3 的 Web 应用，用于处理开源阅读 App 的书源文件，支持去重、格式校验和深度校验功能。

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ / FastAPI / Pydantic / httpx |
| 前端 | Vue 3 (JavaScript) / Element Plus / Axios / Vite |
| 测试 | pytest / pytest-asyncio |

---

## 开发规范

### 代码风格规范

#### Python 后端代码

1. **遵循 PEP 8**：所有 Python 代码必须符合 PEP 8 编码规范

2. **静态检查**：提交前必须通过 flake8/pylint 静态检查

3. **命名约定**：
   - 变量/函数：`snake_case`（如：`user_id`，`get_user_info()`）
   - 类：`PascalCase`（如：`UserModel`，`APIService`）
   - 常量：`UPPER_SNAKE_CASE`（如：`MAX_RETRY_COUNT`，`API_VERSION`）

4. **类型提示**：为函数参数和返回值添加类型提示
   ```python
   def get_user(user_id: int) -> User:
       """获取用户信息"""
       pass
   ```

5. **文档字符串**：所有公共函数和类必须包含 docstring

#### JavaScript/Vue 前端代码

1. **命名约定**：
   - 组件名：`PascalCase`（如：`UserProfile.vue`，`ApiList.vue`）
   - 变量/函数：`camelCase`（如：`userId`，`getUserInfo()`）
   - HTML 属性：`kebab-case`（如：`<user-profile :user-id="id">`）
   - 常量：`UPPER_SNAKE_CASE`（如：`MAX_PAGE_SIZE`）

2. **避免混用**：不要在同一个文件中混用 snake_case 和 camelCase

3. **Composition API**：新组件必须使用 `<script setup>` 语法

4. **语言**：前端使用 JavaScript，**不使用 TypeScript**

---

### 模块设计规范

1. **单一职责**：每个模块、类、函数只负责一个明确的功能

2. **文件组织**：
   - 相关功能放在同一个目录下
   - 每个模块不超过 500 行代码
   - 复杂逻辑拆分为多个函数

3. **文档要求**：
   - 新增文件必须包含文件级文档字符串
   - 公共函数必须包含详细的 docstring
   - 复杂逻辑必须添加行内注释

---

### 测试规范

1. **测试覆盖**：
   - 所有新增代码必须有对应的单元测试
   - 核心业务逻辑测试覆盖率 ≥ 80%
   - 关键路径必须有集成测试

2. **测试通过**：
   - 提交前必须运行 pytest 确保所有测试通过
   - CI/CD 管道中的测试必须全部通过

3. **测试命名**：使用描述性的测试名称
   ```python
   def test_user_login_with_valid_credentials():
       """测试使用有效凭证登录"""
       pass
   ```

---

### 文档规范

1. **更新文档**：代码修改后必须同步更新相关文档

2. **API文档**：新增API端点必须在 Swagger/OpenAPI 中注册

3. **会话总结**：每次会话结束后生成总结文档

---

## 开发命令

### 后端开发

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 运行测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_deduper.py -v
```

### 前端开发

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

---

## 会话总结规范

每次对话结束后，必须创建会话总结文档：

### 文档位置

所有会话总结文档必须存放在 `docs/sessions/` 目录下

### 命名规范

格式：`SESSION_{编号}_{功能描述}.md` 或 `session-{编号}-{功能描述}.md`

示例：
- `SESSION_01_URL_DEDUPLICATION_OPTIMIZATION.md`
- `session-02-api-design.md`

### 内容要求

1. 会话目标
2. 完成任务
3. 技术决策
4. 修改文件清单
5. 测试结果
6. 功能验证清单
7. 使用说明
8. 后续建议

使用中文编写，结构清晰，便于后续查阅。

---

## 项目关键文件

### 后端关键文件

| 文件 | 描述 |
|------|------|
| `backend/app/main.py` | FastAPI 应用入口 |
| `backend/app/config.py` | 配置管理 |
| `backend/app/api/sources.py` | 书源解析 API |
| `backend/app/services/deduper.py` | 去重服务 |
| `backend/app/services/validator.py` | 校验服务 |
| `backend/app/models/response.py` | 响应数据模型 |

### 前端关键文件

| 文件 | 描述 |
|------|------|
| `frontend/src/App.vue` | 根组件 |
| `frontend/src/composables/useSources.js` | 状态管理 |
| `frontend/src/api/sources.js` | API 封装 |
| `frontend/src/components/StatsCardGroup.vue` | 统计展示 |

---

## 自定义规则

1. **语言**：始终使用中文进行用户交流

2. **前端语言**：使用 JavaScript，不使用 TypeScript

3. **会话总结**：每次对话结束后生成总结文档

---

## 会话历史

### 会话 01 - 2026-03-11

**主题**：书源去重功能优化 - URL标准化处理 + 重复URL可视化展示

**完成任务**：
1. 实现 URL 标准化处理（小写、去斜杠、去空白）
2. 新增重复 URL 统计功能
3. 创建 DuplicateUrls.vue 组件实现可视化展示
4. 更新数据模型和 API 返回结构

**技术决策**：
- URL 标准化时机：去重比较时动态标准化
- 重复URL展示数量：前20个
- 前端展示方式：可折叠列表

详细文档：[SESSION_01](docs/sessions/SESSION_01_URL_DEDUPLICATION_OPTIMIZATION.md)

### 会话 02 - 2026-03-12

**主题**：深度校验多线程并发支持 + 校验策略优化

**完成任务**：
1. 后端使用 asyncio.Semaphore 实现并发校验
2. 支持 1/4/8/16/32 线程并发选择
3. 创建 ConcurrencySelector.vue 前端组件
4. API 参数扩展支持 concurrency 参数
5. 优化深度校验策略（HEAD→GET回退，SSL验证禁用）

**技术决策**：
- 并发控制：asyncio.Semaphore + asyncio.Lock
- 默认并发数：16线程
- 最大并发数：32线程
- HTTP策略：HEAD优先，GET回退

详细文档：[SESSION_02](docs/sessions/SESSION_02_CONCURRENT_VALIDATION.md)

### 会话 03 - 2026-03-12

**主题**：校验优化 - 重试机制、超时配置、失败原因分组

**完成任务**：
1. 实现网络波动自动重试机制（最多2次）
2. 403 错误处理（Cloudflare 防护视为有效）
3. 超时时间可配置（15/30/45/60秒，默认30秒）
4. 失败书源按原因分组展示
5. 失败书源导出功能
6. 用户设置历史记录（localStorage）

**技术决策**：
- 重试次数：最多2次，间隔1秒
- 403处理：视为有效（避免误判 Cloudflare 防护网站）
- 设置持久化：localStorage 存储

详细文档：[SESSION_03](docs/sessions/SESSION_03_VALIDATION_OPTIMIZATION.md)

### 会话 04 - 2026-03-12

**主题**：SSE 实时进度条与取消校验功能

**完成任务**：
1. 后端 SSE 端点实现实时进度推送
2. 创建 ValidationProgress.vue 进度条组件
3. 实现取消校验功能
4. 会话管理服务（SessionManager）

**技术决策**：
- 进度推送：SSE（Server-Sent Events）
- 会话管理：内存存储 + asyncio.Lock
- 进度更新频率：每 0.3 秒

详细文档：[SESSION_04](docs/sessions/SESSION_04_SSE_PROGRESS.md)

### 会话 05 - 2026-03-12

**主题**：功能增强与用户体验优化

**完成任务**：
1. 网站图标（书本 SVG favicon）
2. 黑暗模式支持（CSS 变量 + 主题切换）
3. 书源分组保留原有分组
4. 书源类型过滤功能（正版、听书、漫画、影视）
5. 快捷键支持（Ctrl+V 粘贴解析）
6. 在线解析后支持深度校验

**技术决策**：
- 主题切换：CSS 变量 + data-theme 属性
- 过滤检测：bookSourceType 数值 + 关键词双重检测
- 分组逻辑：保留原分组，逗号分隔追加新分组

详细文档：[SESSION_05](docs/sessions/SESSION_05_FEATURE_ENHANCEMENT.md)

### 会话 06 - 2026-03-12

**主题**：移动端优化与批量处理功能

**完成任务**：
1. 移动端触摸交互优化（CSS 触摸区域增大）
2. 移动端文件上传优化（响应式布局）
3. 后端批量文件上传接口（`/api/parse/batch-files`）
4. 后端批量URL解析接口（`/api/parse/batch-urls`）
5. 前端批量处理组件（BatchProcessor.vue）

**技术决策**：
- 触摸优化：按钮最小高度 44px（Apple HIG 规范）
- 响应式断点：768px、575px 两级
- 批量处理：合并所有文件/URL后统一去重校验

详细文档：[SESSION_06](docs/sessions/SESSION_06_MOBILE_BATCH.md)

### 会话 07 - 2026-03-13

**主题**：UI/UX 优化与功能完善

**完成任务**：
1. 单个处理清除功能
2. 批量处理按钮重复问题修复
3. 批量处理加载动画
4. 批量处理参数设置
5. 进度信息组件显示优化
6. 过滤选项可见性优化
7. 失败书源导出功能完善

详细文档：[SESSION_07](docs/sessions/SESSION_07_UI_UX_OPTIMIZATION.md)

### 会话 08 - 2026-03-13

**主题**：搜索校验功能

**完成任务**：
1. 新增搜索校验功能（测试书源搜索/发现功能）
2. 支持校验类型选择（仅搜索/仅发现/搜索+发现）
3. 只校验有对应规则的书源
4. 失败按原因分组显示
5. 支持并发数和超时时间设置

详细文档：[SESSION_08](docs/sessions/SESSION_08_SEARCH_VALIDATION_COMBINED_MODE.md)

### 会话 09 - 2026-03-13

**主题**：搜索校验错误提示优化

**完成任务**：
1. 修复"空白"失败原因问题
2. 优化 JS 加密检测功能
3. 搜索校验相对路径 URL 处理
4. 多行 JSON 配置格式解析
5. 正版网站域名过滤增强

详细文档：[SESSION_09](docs/sessions/SESSION_09_JS_ERROR_OPTIMIZATION.md)

### 会话 10 - 2026-03-14

**主题**：生产环境部署配置

**完成任务**：
1. 后端静态文件服务（支持 SPA 路由）
2. Linux 启动脚本（前台/后台/停止）
3. 完整部署文档
4. 外网访问配置说明

详细文档：[SESSION_10](docs/sessions/SESSION_10_PRODUCTION_DEPLOYMENT.md)

### 会话 11 - 2026-03-14

**主题**：功能优化 - Toast提示、预估时间、错误分类、Docker部署

**完成任务**：
1. 操作 Toast 提示（基于 Element Plus ElMessage）
2. 预估剩余时间（SSE 实时推送）
3. 错误分类展示（可修复/不可修复/需检查）
4. Docker 一键部署脚本（多阶段构建）

详细文档：[SESSION_11](docs/sessions/SESSION_11_FEATURE_OPTIMIZATION.md)

### 会话 12~17 - 2026-03

**主题**：智能校验策略、窗口式吞吐优化、SSE 断线恢复等

详见 `docs/sessions/` 目录（SESSION_12 ~ SESSION_17）。

### 会话 18 - 2026-10-18

**主题**：技术债集中修复 + 移动端 SSE 断链治理

**完成任务**：
1. 统一 URL 清洗工具（url_utils），消除三处重复实现，修复 scheme 长度硬编码
2. URL 安全校验异步化（不再阻塞事件循环）；深度/搜索校验增加轻量 SSRF 拦截
3. search_validator 重构：修复恒真判断、抽取共享重试方法、修复异常捕获顺序死代码
4. session/export 存储加上限保护（100 会话 / 200 导出），会话 ID 防碰撞
5. SSE 增加 `retry: 2000` 重连提示
6. 前端新增 useSSEValidation 组合式函数：统一 5 处 SSE 处理器 + 强制重连看门狗（消息停滞/CLOSED/visibilitychange/online）
7. useSources 单例化；App.vue 清理调试日志
8. 更新 API接口设计.md

**技术决策**：
- 移动端断链主因是系统静默掐断连接且 onerror 不触发，采用前端看门狗主动重建（复用 sessionId，后端重放终态）
- 深度校验只做无 DNS 的轻量 SSRF 检查，避免大批量校验时双重解析开销

详细文档：[SESSION_18](docs/sessions/SESSION_18_TECH_DEBT_MOBILE_SSE.md)

### 会话 19 - 2026-10-18

**主题**：低配服务器（2核2G/3M）与手机弱网优化

**完成任务**：
1. 新增 `GET /api/validate/result/{session_id}` 完整结果接口（支持 GZip，85KB→16KB）
2. SSE 终态消息瘦身：只传统计数字（80KB+ → 300 bytes），明细改走结果接口
3. 前端五种校验流程改为完成消息后拉取结果接口，失败自动重试一次
4. 内存上限可配置并下调：`MAX_SESSIONS=20`、`MAX_EXPORTS=50`、`SESSION_RETENTION_SECONDS=1800`
5. 部署指南修正 `gunicorn -w 4` → `-w 1`（内存会话架构必须单进程），新增低配/弱网优化章节

**技术决策**：
- 结果走独立 HTTP GET 而非继续塞 SSE：可 gzip、可重试、超长消息中断不可恢复
- 内存会话架构下多 worker 是正确性问题，不只是性能问题

详细文档：[SESSION_19](docs/sessions/SESSION_19_LOW_END_SERVER_OPTIMIZATION.md)

---

文档版本：v1.4
最后更新：2026-10-18