# 阅读书源去重校验工具

开源阅读 App 书源文件处理工具 - 支持去重、格式校验、深度校验

## 功能特性

- 🔍 **只查重复**：基于 bookSourceUrl 快速去重（支持 URL 标准化）
- ✅ **全部校验**：去重 + 格式校验 + 深度校验（模拟手机端请求）
- 🔄 **并发校验**：支持 1/4/8/16/32 线程并发选择
- ⏱️ **超时配置**：15/30/45/60 秒可选超时时间
- 🔁 **自动重试**：网络波动时自动重试，提高成功率
- 🛡️ **智能判断**：403 错误视为有效（Cloudflare 防护）
- 🌙 **黑暗模式**：支持亮色/暗色主题切换
- 🎯 **类型过滤**：支持过滤正版、听书、漫画、影视书源
- ⌨️ **快捷键**：Ctrl+V 直接粘贴链接解析
- 📊 **统计展示**：直观显示原始总数、去重后数量、重复数、失效数量
- 📋 **重复URL展示**：可视化展示重复URL列表
- ❌ **失败分析**：按原因分组展示失败书源，支持导出
- 📥 **一键下载**：导出干净的 JSON 文件，保留原有分组
- 💾 **历史记录**：自动记住用户设置（并发数、超时时间、主题）

## 快速开始

### 方式一：一键启动（推荐）

双击运行 `start.bat`，自动安装依赖并启动服务。

启动后访问：
- **前端地址**：http://localhost:5173
- **API文档**：http://localhost:8000/docs

停止服务：运行 `stop.bat`

### 方式二：手动启动

**后端：**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

## 环境要求

- Python 3.10+
- Node.js 18+

## 项目结构

```
shuyuanquchong/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── api/      # API路由
│   │   ├── services/ # 业务逻辑
│   │   └── models/   # 数据模型
│   └── requirements.txt
├── frontend/         # Vue 3 前端 (JavaScript)
│   ├── src/
│   │   ├── components/  # Vue组件
│   │   ├── api/         # API封装
│   │   └── utils/       # 工具函数
│   └── package.json
├── docs/             # 设计文档
│   └── sessions/     # 会话总结
├── CLAUDE.md         # AI开发规范
├── start.bat         # 一键启动
└── stop.bat          # 停止服务
```

## 使用说明

1. 上传 JSON 文件或输入在线链接获取书源
2. 选择操作模式：
   - **只查重复**：快速去重，速度快
   - **全部校验**：去重+深度校验，结果更准确
3. 查看统计结果（含重复URL列表）
4. 点击下载获取干净的 JSON 文件

## 书源分组格式

校验后的书源会**保留原有分组**并追加新分组：

- 原有分组：`优质书源`
- 校验后：`优质书源,2026-03-12去重有效100条`

如果书源没有原有分组，则直接设置新分组：`2026-03-12去重有效100条`

## URL标准化规则

去重时自动进行 URL 标准化处理：
- 转换为小写
- 去除尾部斜杠
- 去除首尾空白字符

## 文档

- [网站功能规划](docs/网站功能规划.md)
- [项目目录结构](docs/项目目录结构.md)
- [API接口设计](docs/API接口设计.md)
- [前端组件设计](docs/前端组件设计.md)
- [系统架构设计](docs/系统架构设计.md)
- [UI设计规范](docs/UI设计规范.md)

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

**修改文件**：
- `backend/app/models/response.py` - 新增 DuplicateUrl 模型
- `backend/app/services/deduper.py` - 返回重复URL统计
- `backend/app/api/sources.py` - 处理新返回值
- `frontend/src/components/DuplicateUrls.vue` - 新增组件
- `frontend/src/components/StatsCardGroup.vue` - 集成组件
- `frontend/src/composables/useSources.js` - 添加重复URL字段

**测试结果**：23 个测试全部通过

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
- SSL验证：禁用（兼容更多网站）

**修改文件**：
- `backend/app/services/validator.py` - 添加并发校验支持，优化校验策略
- `backend/app/models/request.py` - 添加 concurrency 字段
- `backend/app/api/sources.py` - 添加 concurrency 参数
- `frontend/src/components/ConcurrencySelector.vue` - 新增组件
- `frontend/src/api/sources.js` - API 添加 concurrency 参数
- `frontend/src/App.vue` - 集成并发选择器

**测试结果**：23 个测试全部通过

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
- 失败原因分类：超时、连接失败、HTTP错误等
- 设置持久化：localStorage 存储

**修改文件**：
- `backend/app/config.py` - 添加超时选项、重试配置
- `backend/app/services/validator.py` - 重试机制、失败原因记录
- `backend/app/models/request.py` - 添加 timeout 参数
- `backend/app/models/response.py` - 添加 FailedSourceGroup 模型
- `frontend/src/components/TimeoutSelector.vue` - 新增组件
- `frontend/src/App.vue` - 超时选择、失败分组展示、历史记录

**测试结果**：23 个测试全部通过

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

**修改文件**：
- `backend/app/services/session_manager.py` - 新增会话管理服务
- `backend/app/api/sources.py` - 添加 SSE 端点、取消端点
- `frontend/src/api/sources.js` - 添加 SSE 相关 API
- `frontend/src/components/ValidationProgress.vue` - 新增进度条组件
- `frontend/src/App.vue` - 集成 SSE 进度显示

**测试结果**：23 个测试全部通过

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

**修改文件**：
- `frontend/public/favicon.svg` - 新增书本图标
- `frontend/src/styles/index.css` - CSS 变量 + 黑暗模式
- `frontend/src/components/ThemeToggle.vue` - 主题切换组件
- `frontend/src/components/FilterOptions.vue` - 过滤选项组件
- `backend/app/services/filter.py` - 书源过滤服务
- `backend/app/api/sources.py` - 添加过滤参数、新接口

**测试结果**：33 个测试全部通过

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

**修改文件**：
- `backend/app/api/sources.py` - 添加批量上传接口
- `frontend/src/components/BatchProcessor.vue` - 新增批量处理组件
- `frontend/src/styles/index.css` - 移动端触摸优化

**测试结果**：33 个测试全部通过

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

**技术决策**：
- 清除按钮：上传/解析后显示，处理中禁用
- 批量模式：内置操作按钮，移除重复组件
- 加载动画：按钮内 spinner + 文字提示

**修改文件**：
- `frontend/src/App.vue` - 清除功能、显示优化
- `frontend/src/components/BatchProcessor.vue` - 加载动画、参数设置

**测试结果**：前端构建成功

详细文档：[SESSION_07](docs/sessions/SESSION_07_UI_UX_OPTIMIZATION.md)

### 会话 08 - 2026-03-13

**主题**：搜索校验功能

**完成任务**：
1. 新增搜索校验功能（测试书源搜索/发现功能）
2. 支持校验类型选择（仅搜索/仅发现/搜索+发现）
3. 只校验有对应规则的书源
4. 失败按原因分组显示
5. 支持并发数和超时时间设置
6. 规则类型统计（仅搜索、仅发现、搜索+发现、无规则）
7. 失败书源导出完整信息

**技术决策**：
- 校验关键词：预设"玄幻、重生、穿越"，支持自定义
- 组合模式：至少一个通过即有效
- SSE 进度：实时显示校验进度

**修改文件**：
- `backend/app/services/search_validator.py` - 搜索校验服务
- `backend/app/services/js_processor.py` - JS 规则解析
- `backend/app/api/sources.py` - 搜索校验接口
- `frontend/src/components/SearchValidator.vue` - 搜索校验组件

**测试结果**：前端构建成功，搜索校验功能正常

详细文档：[SESSION_08](docs/sessions/SESSION_08_SEARCH_VALIDATION_COMBINED_MODE.md)

### 会话 09 - 2026-03-13

**主题**：搜索校验错误提示优化

**完成任务**：
1. 修复"空白"失败原因问题
2. 优化 JS 加密检测功能
3. 添加不支持的加密提示

**技术决策**：
- 空错误回退：显示"未知错误"而非空白
- 加密检测：提前检测不支持的加密功能
- 不支持提示：明确告知用户具体原因

**修改文件**：
- `backend/app/services/search_validator.py` - 空错误回退
- `backend/app/services/js_processor.py` - 加密检测方法
- `backend/app/api/sources.py` - 空原因处理
- `frontend/src/App.vue` - 前端显示优化

**测试结果**：Python 语法检查通过，前端构建成功

详细文档：[SESSION_09](docs/sessions/SESSION_09_JS_ERROR_OPTIMIZATION.md)