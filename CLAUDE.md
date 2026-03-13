# CLAUDE.md

此文件为 AI（Claude.ai/Code/GLM/Qwen）在此代码库中工作时提供指导。

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

3. **会话总结**：每次对话结束后生成总结文档并更新 README.md

---

文档版本：v1.0
最后更新：2026-03-12