# API 接口详细设计文档

## 1. 概述

### 1.1 基本信息
- **基础路径**: `/api`
- **协议**: HTTP/HTTPS
- **数据格式**: JSON
- **编码**: UTF-8

### 1.2 通用约定

#### 请求头
```
Content-Type: application/json
Accept: application/json
```

#### 响应格式
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

#### 错误响应格式
```json
{
  "code": 400,
  "message": "错误描述"
}
```

---

## 2. 接口列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/health | 健康检查 |
| POST | /api/parse/file | 解析上传文件 |
| POST | /api/parse/url | 解析在线链接 |
| POST | /api/validate/start | 开始深度校验 |
| GET | /api/validate/progress | 获取校验进度（SSE） |
| POST | /api/validate/cancel | 取消校验 |

---

## 3. 接口详情

### 3.1 健康检查

检查服务是否正常运行。

#### 请求

```
GET /api/health
```

#### 参数

无

#### 响应

**成功响应 (200 OK)**

```json
{
  "status": "ok"
}
```

#### 示例

**请求**
```bash
curl -X GET http://localhost:8000/api/health
```

**响应**
```json
{
  "status": "ok"
}
```

---

### 3.2 解析上传文件

上传 JSON 文件并解析书源数据，支持两种操作模式。

#### 请求

```
POST /api/parse/file
Content-Type: multipart/form-data
```

#### 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| file | File | 是 | JSON 文件，最大 10MB |
| mode | string | 否 | 操作模式：`dedup`(只查重复，默认) 或 `full`(全部校验) |

#### 请求示例

**只查重复（默认）**
```bash
curl -X POST http://localhost:8000/api/parse/file \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sources.json"
```

**全部校验**
```bash
curl -X POST http://localhost:8000/api/parse/file \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sources.json" \
  -F "mode=full"
```

#### 响应

**成功响应 (200 OK) - 只查重复模式**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 125,
    "dedupCount": 110,
    "formatInvalid": 15,
    "deepInvalid": null,
    "validCount": 110,
    "dedupedSources": [
      {
        "bookSourceName": "示例书源1",
        "bookSourceUrl": "https://example1.com",
        "bookSourceGroup": "小说",
        "enabled": true
      }
    ]
  }
}
```

**成功响应 (200 OK) - 全部校验模式**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 125,
    "dedupCount": 110,
    "formatInvalid": 15,
    "deepInvalid": 12,
    "validCount": 98,
    "dedupedSources": [
      {
        "bookSourceName": "示例书源1",
        "bookSourceUrl": "https://example1.com",
        "bookSourceGroup": "小说",
        "enabled": true
      }
    ]
  }
}
```

**响应字段说明**

| 字段 | 类型 | 描述 |
|------|------|------|
| code | integer | 状态码，200 表示成功 |
| message | string | 响应消息 |
| data | object | 响应数据 |
| data.total | integer | 原始书源总数 |
| data.dedupCount | integer | 去重后书源数量 |
| data.formatInvalid | integer | 格式失效书源数量（URL格式错误） |
| data.deepInvalid | integer \| null | 深度校验失效数量（仅 mode=full），null 表示未进行深度校验 |
| data.validCount | integer | 最终有效书源数量 |
| data.dedupedSources | array | 去重后的有效书源数组 |

**错误响应**

| 状态码 | code | message | 场景 |
|--------|------|---------|------|
| 400 | 400 | 文件不能为空 | 未上传文件 |
| 400 | 400 | 仅支持 JSON 格式文件 | 文件格式错误 |
| 400 | 400 | 文件大小超过限制（最大10MB） | 文件过大 |
| 400 | 400 | JSON 解析失败：具体错误信息 | JSON 格式错误 |
| 400 | 400 | 书源数据格式不正确 | 数据不是数组或对象 |

#### 示例

**请求文件 (sources.json)**
```json
[
  {
    "bookSourceName": "书源A",
    "bookSourceUrl": "https://source-a.com",
    "bookSourceGroup": "小说"
  },
  {
    "bookSourceName": "书源B",
    "bookSourceUrl": "https://source-b.com",
    "bookSourceGroup": "小说"
  },
  {
    "bookSourceName": "书源A重复",
    "bookSourceUrl": "https://source-a.com",
    "bookSourceGroup": "小说"
  },
  {
    "bookSourceName": "无效书源",
    "bookSourceUrl": "",
    "bookSourceGroup": "小说"
  }
]
```

**响应**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 4,
    "valid": 3,
    "invalid": 1,
    "dedupValid": 2,
    "dedupedSources": [
      {
        "bookSourceName": "书源A",
        "bookSourceUrl": "https://source-a.com",
        "bookSourceGroup": "小说"
      },
      {
        "bookSourceName": "书源B",
        "bookSourceUrl": "https://source-b.com",
        "bookSourceGroup": "小说"
      }
    ]
  }
}
```

---

### 3.3 解析在线链接

通过 URL 获取远程书源数据并解析。

#### 请求

```
POST /api/parse/url
Content-Type: application/json
```

#### 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| url | string | 是 | 书源 JSON 文件的 URL 地址 |
| mode | string | 否 | 操作模式：`dedup`(只查重复，默认) 或 `full`(全部校验) |

#### 请求体

```json
{
  "url": "https://example.com/sources.json",
  "mode": "full"
}
```

#### 请求示例

```bash
curl -X POST http://localhost:8000/api/parse/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/sources.json", "mode": "full"}'
```

#### 响应

响应格式与 `POST /api/parse/file` 相同。

**错误响应**

| 状态码 | code | message | 场景 |
|--------|------|---------|------|
| 400 | 400 | URL 不能为空 | 未提供 URL |
| 400 | 400 | URL 格式不正确 | URL 格式非法 |
| 400 | 400 | 仅支持 HTTP/HTTPS 协议 | 协议不支持 |
| 400 | 400 | 不允许访问该地址 | SSRF 防护拦截 |
| 502 | 502 | 获取远程数据失败：连接超时 | 网络超时 |
| 502 | 502 | 获取远程数据失败：HTTP 404 | 远程资源不存在 |
| 502 | 502 | 获取远程数据失败：具体错误 | 其他网络错误 |
| 400 | 400 | JSON 解析失败：具体错误信息 | 响应不是有效 JSON |
| 400 | 400 | 书源数据格式不正确 | 数据格式错误 |

#### 示例

**请求**
```bash
curl -X POST http://localhost:8000/api/parse/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://raw.githubusercontent.com/example/sources/main/books.json"}'
```

**响应**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 200,
    "dedupCount": 195,
    "formatInvalid": 5,
    "deepInvalid": null,
    "validCount": 195,
    "dedupedSources": [ ... ]
  }
}
```

---

### 3.4 开始深度校验

对已解析的书源进行深度校验（实际访问书源URL检测可用性）。

#### 请求

```
POST /api/validate/start
Content-Type: application/json
```

#### 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| sources | array | 是 | 需要校验的书源数组 |
| sessionId | string | 否 | 会话ID，用于关联进度查询 |

#### 请求体

```json
{
  "sources": [
    { "bookSourceName": "书源A", "bookSourceUrl": "https://source-a.com" }
  ],
  "sessionId": "user-session-123"
}
```

#### 响应

```json
{
  "code": 200,
  "message": "校验已开始",
  "data": {
    "sessionId": "user-session-123",
    "total": 100
  }
}
```

---

### 3.5 获取校验进度（SSE）

通过 Server-Sent Events 实时获取深度校验进度。

#### 请求

```
GET /api/validate/progress?sessionId={sessionId}
Accept: text/event-stream
```

#### 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| sessionId | string | 是 | 会话ID |

#### 响应（SSE 流）

```
event: progress
data: {"processed": 50, "total": 100, "current": "https://example.com", "valid": 45, "invalid": 5}

event: progress
data: {"processed": 100, "total": 100, "current": "https://last-source.com", "valid": 90, "invalid": 10}

event: complete
data: {"total": 100, "valid": 90, "invalid": 10, "dedupedSources": [...]}
```

#### 前端调用示例

```javascript
const eventSource = new EventSource('/api/validate/progress?sessionId=xxx');

eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log(`进度: ${data.processed}/${data.total}`);
});

eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('校验完成', data);
  eventSource.close();
});
```

---

### 3.6 取消校验

取消正在进行的深度校验。

#### 请求

```
POST /api/validate/cancel
Content-Type: application/json
```

#### 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| sessionId | string | 是 | 会话ID |

#### 请求体

```json
{
  "sessionId": "user-session-123"
}
```

#### 响应

```json
{
  "code": 200,
  "message": "已取消校验"
}
```

---

## 4. 数据格式兼容

### 4.1 支持的书源格式

API 自动识别并解析以下常见格式：

#### 格式1：直接数组
```json
[
  { "bookSourceName": "书源1", "bookSourceUrl": "https://..." },
  { "bookSourceName": "书源2", "bookSourceUrl": "https://..." }
]
```

#### 格式2：sources 包装
```json
{
  "sources": [
    { "bookSourceName": "书源1", "bookSourceUrl": "https://..." }
  ]
}
```

#### 格式3：data 包装
```json
{
  "data": [
    { "bookSourceName": "书源1", "bookSourceUrl": "https://..." }
  ]
}
```

#### 格式4：嵌套对象（自动提取数组）
```json
{
  "code": 200,
  "data": {
    "list": [...],
    "total": 100
  }
}
```

### 4.2 解析优先级

1. 如果是数组 → 直接使用
2. 如果是对象，检查 `sources` 字段
3. 如果是对象，检查 `data` 字段
4. 如果是对象，检查第一个数组类型的字段
5. 都不匹配 → 返回错误

---

## 5. 校验规则

### 5.1 格式校验

书源格式被认为是**有效**的条件：
- `bookSourceUrl` 字段存在
- `bookSourceUrl` 不为空字符串
- `bookSourceUrl` 以 `http://` 或 `https://` 开头
- `bookSourceUrl` 是合法的 URL 格式

### 5.2 深度校验

深度校验通过实际访问书源URL检测可用性：

#### 请求配置
```python
# 手机端请求头配置
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

REQUEST_HEADERS = {
    "User-Agent": MOBILE_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}
```

#### 校验条件
- 使用 HEAD 请求（部分网站不支持则降级为 GET）
- HTTP 状态码 200-399 视为有效
- 单个书源校验超时：10秒
- 支持重定向跟踪（最多5次）

### 5.3 去重规则

- 去重键：`bookSourceUrl` 字段值（去除首尾空白）
- 保留策略：保留首次出现的书源，丢弃后续重复项
- 大小写：不区分大小写（可选配置）

### 5.4 书源分组设置规则

校验完成后，自动设置书源分组字段：

```
分组格式：YYYY-MM-DD校验XXX条书源
示例：2026-03-11校验98条书源
```

**处理逻辑**：
```python
from datetime import datetime

def set_source_group(sources: list, valid_count: int) -> list:
    """设置书源分组"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    group_name = f"{date_str}校验{valid_count}条书源"

    for source in sources:
        source["bookSourceGroup"] = group_name

    return sources
```

### 5.5 校验逻辑流程

```
输入数据
    │
    ▼
┌────────────────────────┐
│  步骤1：去重处理        │
│  基于 bookSourceUrl    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  步骤2：格式校验        │
│  检查 URL 格式合法性    │
└───────────┬────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
  格式有效        格式失效
    │               │
    │               └── 记录 formatInvalid
    │
    ▼
┌────────────────────────┐
│  步骤3：深度校验        │  (仅 mode=full)
│  模拟手机端请求        │
│  实际访问 URL         │
└───────────┬────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
  访问成功        访问失败
    │               │
    │               └── 记录 deepInvalid
    │
    ▼
┌────────────────────────┐
│  步骤4：设置分组        │
│  YYYY-MM-DD校验XXX条   │
└───────────┬────────────┘
            │
            ▼
      返回有效书源
```

---

## 6. 错误码定义

### 6.1 HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|---------|
| 200 | OK | 请求成功 |
| 400 | Bad Request | 请求参数错误 |
| 413 | Payload Too Large | 文件过大 |
| 422 | Unprocessable Entity | 参数验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |
| 502 | Bad Gateway | 上游服务错误（远程获取失败） |

### 6.2 业务错误码

| code | 含义 | message 示例 |
|------|------|-------------|
| 200 | 成功 | success |
| 400 | 请求错误 | 文件不能为空 |
| 401 | 未授权 | （预留） |
| 403 | 禁止访问 | 不允许访问该地址 |
| 404 | 资源不存在 | （预留） |
| 500 | 服务器错误 | 服务器内部错误 |
| 502 | 上游错误 | 获取远程数据失败 |

---

## 7. 请求限制

### 7.1 文件上传限制

| 限制项 | 值 |
|--------|------|
| 最大文件大小 | 10 MB |
| 允许的文件扩展名 | .json |
| 允许的 MIME 类型 | application/json |

### 7.2 URL 获取限制

| 限制项 | 值 |
|--------|------|
| 请求超时 | 30 秒 |
| 最大响应大小 | 10 MB |
| 允许的协议 | http, https |
| 禁止访问的 IP | 私有网络、本地回环 |

### 7.3 请求频率限制（可选）

| 限制项 | 值 |
|--------|------|
| 每分钟请求数 | 60 次 |
| 每小时请求数 | 1000 次 |

---

## 8. OpenAPI 规范

### 8.1 完整 OpenAPI 文档

```yaml
openapi: 3.0.3
info:
  title: 阅读书源去重校验工具 API
  description: |
    开源阅读 App 书源文件处理工具 API

    功能：
    - 上传 JSON 文件解析书源
    - 在线获取书源链接
    - 自动去重和失效检测
  version: 1.0.0
  contact:
    name: API Support

servers:
  - url: http://localhost:8000/api
    description: 开发环境
  - url: https://api.example.com/api
    description: 生产环境

paths:
  /health:
    get:
      summary: 健康检查
      description: 检查服务是否正常运行
      operationId: healthCheck
      responses:
        '200':
          description: 服务正常
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok
                required:
                  - status

  /parse/file:
    post:
      summary: 解析上传文件
      description: 上传 JSON 文件并解析书源数据，自动去重和校验
      operationId: parseFile
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                  description: JSON 文件
              required:
                - file
      responses:
        '200':
          description: 解析成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ParseResponse'
        '400':
          description: 请求错误
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '413':
          description: 文件过大
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /parse/url:
    post:
      summary: 解析在线链接
      description: 通过 URL 获取远程书源数据并解析
      operationId: parseUrl
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UrlParseRequest'
      responses:
        '200':
          description: 解析成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ParseResponse'
        '400':
          description: 请求错误
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '502':
          description: 获取远程数据失败
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:
    ParseResponse:
      type: object
      properties:
        code:
          type: integer
          example: 200
        message:
          type: string
          example: success
        data:
          $ref: '#/components/schemas/SourceData'
      required:
        - code
        - message

    SourceData:
      type: object
      properties:
        total:
          type: integer
          description: 原始书源总数
          example: 125
        valid:
          type: integer
          description: 有效书源数量
          example: 110
        invalid:
          type: integer
          description: 失效书源数量
          example: 15
        dedupValid:
          type: integer
          description: 去重后有效数量
          example: 98
        dedupedSources:
          type: array
          description: 去重后的有效书源数组
          items:
            $ref: '#/components/schemas/BookSource'
      required:
        - total
        - valid
        - invalid
        - dedupValid
        - dedupedSources

    BookSource:
      type: object
      description: 书源对象
      properties:
        bookSourceName:
          type: string
          description: 书源名称
          example: 示例书源
        bookSourceUrl:
          type: string
          description: 书源地址
          example: https://example.com
        bookSourceGroup:
          type: string
          description: 书源分组
          example: 小说
        enabled:
          type: boolean
          description: 是否启用
          example: true

    UrlParseRequest:
      type: object
      properties:
        url:
          type: string
          format: uri
          description: 书源 JSON 文件 URL
          example: https://example.com/sources.json
      required:
        - url

    ErrorResponse:
      type: object
      properties:
        code:
          type: integer
          example: 400
        message:
          type: string
          example: 错误描述
      required:
        - code
        - message
```

---

## 9. 后端实现参考

### 9.1 常量配置

```python
# app/config.py

# 手机端请求头
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

REQUEST_HEADERS = {
    "User-Agent": MOBILE_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 超时配置
VALIDATE_TIMEOUT = 10  # 单个书源校验超时(秒)
MAX_REDIRECTS = 5      # 最大重定向次数
```

### 9.2 路由定义 (FastAPI)

```python
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import json
import asyncio
from datetime import datetime

app = FastAPI()

# 存储校验任务状态
validation_tasks = {}

class UrlParseRequest(BaseModel):
    url: str
    mode: str = "dedup"  # dedup | full

class ValidateStartRequest(BaseModel):
    sources: List[dict]
    sessionId: Optional[str] = None

class SourceData(BaseModel):
    total: int
    dedupCount: int
    formatInvalid: int
    deepInvalid: Optional[int] = None
    validCount: int
    dedupedSources: list

class ParseResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[SourceData] = None

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/parse/file", response_model=ParseResponse)
async def parse_file(
    file: UploadFile = File(...),
    mode: str = Form(default="dedup")
):
    # 1. 验证文件
    if not file.filename.endswith('.json'):
        return ParseResponse(code=400, message="仅支持 JSON 格式文件")

    # 2. 读取内容
    content = await file.read()

    # 3. 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return ParseResponse(code=400, message=f"JSON 解析失败：{str(e)}")

    # 4. 处理书源
    result = process_sources(data, mode)

    return ParseResponse(data=result)

@app.post("/api/parse/url", response_model=ParseResponse)
async def parse_url(request: UrlParseRequest):
    # 1. 验证 URL
    if not request.url.startswith(('http://', 'https://')):
        return ParseResponse(code=400, message="仅支持 HTTP/HTTPS 协议")

    # 2. 获取远程数据
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(request.url)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return ParseResponse(code=502, message="获取远程数据失败：连接超时")
    except Exception as e:
        return ParseResponse(code=502, message=f"获取远程数据失败：{str(e)}")

    # 3. 处理书源
    result = process_sources(data, request.mode)

    return ParseResponse(data=result)

def process_sources(data, mode: str = "dedup") -> dict:
    """处理书源数据"""
    # 提取书源数组
    sources = extract_sources(data)
    total = len(sources)

    # 步骤1：去重
    seen = set()
    deduped = []
    for s in sources:
        url = s.get('bookSourceUrl', '').strip()
        if url and url not in seen:
            seen.add(url)
            deduped.append(s)

    # 步骤2：格式校验
    format_valid = []
    format_invalid = 0
    for s in deduped:
        if is_format_valid(s):
            format_valid.append(s)
        else:
            format_invalid += 1

    # 步骤3：深度校验（仅 mode=full）
    deep_invalid = None
    final_valid = format_valid

    if mode == "full":
        final_valid, deep_invalid = asyncio.run(deep_validate(format_valid))

    # 步骤4：设置分组
    valid_count = len(final_valid)
    set_source_group(final_valid, valid_count)

    return {
        "total": total,
        "dedupCount": len(deduped),
        "formatInvalid": format_invalid,
        "deepInvalid": deep_invalid,
        "validCount": valid_count,
        "dedupedSources": final_valid
    }

def extract_sources(data) -> list:
    """从各种格式中提取书源数组"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ['sources', 'data', 'list']:
            if key in data and isinstance(data[key], list):
                return data[key]
        for value in data.values():
            if isinstance(value, list):
                return value
    return []

def is_format_valid(source: dict) -> bool:
    """判断书源格式是否有效"""
    url = source.get('bookSourceUrl', '')
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    return url.startswith(('http://', 'https://'))

async def deep_validate(sources: list) -> tuple:
    """深度校验书源"""
    import httpx

    valid = []
    invalid = 0

    async with httpx.AsyncClient(
        timeout=VALIDATE_TIMEOUT,
        follow_redirects=True,
        max_redirects=MAX_REDIRECTS
    ) as client:
        for source in sources:
            url = source.get('bookSourceUrl', '')
            try:
                response = await client.head(url, headers=REQUEST_HEADERS)
                if 200 <= response.status_code < 400:
                    valid.append(source)
                else:
                    invalid += 1
            except Exception:
                invalid += 1

    return valid, invalid

def set_source_group(sources: list, valid_count: int) -> None:
    """设置书源分组"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    group_name = f"{date_str}校验{valid_count}条书源"

    for source in sources:
        source["bookSourceGroup"] = group_name
```

---

## 10. 前端调用示例

### 10.1 使用 Axios

```typescript
import axios from 'axios';

const API_BASE = '/api';

// 健康检查
async function healthCheck() {
  const response = await axios.get(`${API_BASE}/health`);
  return response.data;
}

// 解析文件 - 只查重复
async function parseFileDedup(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(`${API_BASE}/parse/file`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}

// 解析文件 - 全部校验
async function parseFileFull(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', 'full');

  const response = await axios.post(`${API_BASE}/parse/file`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}

// 解析 URL
async function parseUrl(url: string, mode: 'dedup' | 'full' = 'dedup') {
  const response = await axios.post(`${API_BASE}/parse/url`, { url, mode });
  return response.data;
}

// 监听深度校验进度
function listenValidateProgress(
  sessionId: string,
  onProgress: (data: any) => void,
  onComplete: (data: any) => void
) {
  const eventSource = new EventSource(
    `${API_BASE}/validate/progress?sessionId=${sessionId}`
  );

  eventSource.addEventListener('progress', (event) => {
    onProgress(JSON.parse(event.data));
  });

  eventSource.addEventListener('complete', (event) => {
    onComplete(JSON.parse(event.data));
    eventSource.close();
  });

  return () => eventSource.close();
}

// 取消校验
async function cancelValidation(sessionId: string) {
  const response = await axios.post(`${API_BASE}/validate/cancel`, { sessionId });
  return response.data;
}
```

### 10.2 使用 Fetch

```typescript
// 解析文件
async function parseFile(file: File, mode: 'dedup' | 'full' = 'dedup') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', mode);

  const response = await fetch('/api/parse/file', {
    method: 'POST',
    body: formData
  });

  return response.json();
}

// 解析 URL
async function parseUrl(url: string, mode: 'dedup' | 'full' = 'dedup') {
  const response = await fetch('/api/parse/url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, mode })
  });

  return response.json();
}
```

---

文档版本：v1.1
最后更新：2026-03-11