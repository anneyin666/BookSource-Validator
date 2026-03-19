# API 接口设计

本文档描述当前代码中的真实接口。

## 1. 基础信息

- 基础路径：`/api`
- 数据格式：JSON / multipart-form-data / SSE
- 健康检查：`GET /api/health`

## 2. 接口总览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/parse/file` | 单文件解析 |
| POST | `/api/parse/url` | 单 URL 解析 |
| POST | `/api/validate/start` | 从文件开始深度校验 |
| POST | `/api/validate/start-data` | 从已有书源数组开始深度校验 |
| GET | `/api/validate/progress/{session_id}` | 深度校验 SSE |
| POST | `/api/validate/cancel` | 取消深度校验 |
| POST | `/api/parse/batch-files/start` | 批量文件 SSE 校验启动 |
| POST | `/api/parse/batch-urls/start` | 批量 URL SSE 校验启动 |
| POST | `/api/parse/batch-files` | 批量文件普通解析 |
| POST | `/api/parse/batch-urls` | 批量 URL 普通解析 |
| POST | `/api/validate/search/start` | 搜索校验启动 |
| GET | `/api/validate/search/progress/{session_id}` | 搜索校验 SSE |

## 3. 通用返回结构

### 3.1 普通 JSON 接口

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 3.2 `SourceData` 主要字段

```json
{
  "total": 125,
  "dedupCount": 110,
  "duplicates": 15,
  "duplicateUrls": [
    { "url": "https://example.com", "count": 2 }
  ],
  "formatInvalid": 3,
  "deepInvalid": 5,
  "validCount": 102,
  "dedupedSources": [],
  "failedGroups": [],
  "fileStats": [],
  "urlStats": []
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `total` | 原始书源总数 |
| `dedupCount` | 当前流程中去重后的数量 |
| `duplicates` | 重复数量 |
| `duplicateUrls` | 重复 URL 统计 |
| `formatInvalid` | 格式失效数量 |
| `deepInvalid` | 深度校验失效数量 |
| `validCount` | 最终有效数量 |
| `dedupedSources` | 最终有效书源数组 |
| `failedGroups` | 失败详情，按原因分组 |
| `fileStats` | 批量文件来源统计 |
| `urlStats` | 批量 URL 来源统计 |

## 4. 基础接口

### 4.1 健康检查

`GET /api/health`

返回：

```json
{ "status": "ok" }
```

### 4.2 单文件解析

`POST /api/parse/file`

请求类型：`multipart/form-data`

字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | `.json` 或 `.txt`，内容需为 JSON |
| `mode` | string | `dedup` 或 `full` |
| `concurrency` | int | 并发数 |
| `timeout` | int | 超时秒数 |
| `filter_types` | string | 逗号分隔，如 `official,audio` |

参数限制：
- `concurrency` 仅支持 `1/4/8/16/32`
- `timeout` 仅支持 `15/30/45/60`

### 4.3 单 URL 解析

`POST /api/parse/url`

请求体：

```json
{
  "url": "https://example.com/sources.json",
  "mode": "dedup",
  "concurrency": 16,
  "timeout": 30,
  "filter_types": "official,audio"
}
```

在线 URL 获取会执行基础安全校验，拒绝回环、私网和本地域名。

## 5. 深度校验接口

### 5.1 从文件开始

`POST /api/validate/start`

请求类型：`multipart/form-data`

字段：
- `file`
- `concurrency`
- `timeout`
- `filter_types`

参数限制：
- `concurrency` 仅支持 `1/4/8/16/32`
- `timeout` 仅支持 `15/30/45/60`

返回：

```json
{
  "code": 200,
  "sessionId": "abc12345",
  "total": 125,
  "dedupCount": 110,
  "duplicates": 15,
  "formatInvalid": 3,
  "deepTotal": 107,
  "message": "会话创建成功"
}
```

### 5.2 从已有书源数组开始

`POST /api/validate/start-data`

请求体：

```json
{
  "sources": [],
  "concurrency": 16,
  "timeout": 30
}
```

### 5.3 SSE 进度

`GET /api/validate/progress/{session_id}`

运行中消息：

```json
{
  "processed": 20,
  "total": 100,
  "valid": 18,
  "invalid": 2,
  "current": "https://example.com",
  "currentName": "示例书源",
  "elapsed": 12.4,
  "estimatedRemaining": 35.1,
  "status": "running"
}
```

完成消息：

```json
{
  "status": "completed",
  "processed": 100,
  "total": 100,
  "validCount": 92,
  "invalidCount": 8,
  "validSources": [],
  "failedGroups": [],
  "failedCategories": {}
}
```

### 5.4 取消

`POST /api/validate/cancel`

请求类型：`multipart/form-data`

字段：

| 字段 | 类型 |
|------|------|
| `session_id` | string |

## 6. 批量处理接口

### 6.1 批量文件普通解析

`POST /api/parse/batch-files`

请求类型：`multipart/form-data`

字段：
- `files`
- `mode`
- `concurrency`
- `timeout`
- `filter_types`

返回数据额外包含：
- `fileStats`

### 6.2 批量 URL 普通解析

`POST /api/parse/batch-urls`

请求体：

```json
{
  "urls": [
    "https://a.com/sources.json",
    "https://b.com/sources.json"
  ],
  "mode": "full",
  "concurrency": 16,
  "timeout": 30,
  "filter_types": "official"
}
```

返回数据额外包含：
- `urlStats`

### 6.3 批量文件 SSE 启动

`POST /api/parse/batch-files/start`

返回：

```json
{
  "code": 200,
  "sessionId": "abc12345",
  "total": 500,
  "dedupCount": 420,
  "duplicates": 80,
  "formatInvalid": 6,
  "deepTotal": 414,
  "fileStats": [],
  "message": "会话创建成功"
}
```

### 6.4 批量 URL SSE 启动

`POST /api/parse/batch-urls/start`

返回结构与批量文件类似，但统计字段为 `urlStats`。

## 7. 搜索校验接口

### 7.1 启动搜索校验

`POST /api/validate/search/start`

请求类型：`multipart/form-data`

字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | 书源文件 |
| `keyword` | string | 搜索关键词 |
| `validate_type` | string | `search` / `explore` / `both` |
| `concurrency` | int | 并发数 |
| `timeout` | int | 超时秒数 |

返回：

```json
{
  "code": 200,
  "sessionId": "abc12345",
  "total": 200,
  "keyword": "玄幻",
  "validateType": "both",
  "message": "会话创建成功"
}
```

### 7.2 搜索校验 SSE

`GET /api/validate/search/progress/{session_id}`

完成消息额外包含：

```json
{
  "status": "completed",
  "validCount": 120,
  "invalidCount": 80,
  "validSources": [],
  "failedGroups": [],
  "failedCategories": {},
  "ruleTypeStats": {
    "searchOnly": { "valid": 10, "invalid": 5, "total": 15 },
    "exploreOnly": { "valid": 20, "invalid": 10, "total": 30 },
    "both": { "valid": 90, "invalid": 60, "total": 150 },
    "none": { "valid": 0, "invalid": 5, "total": 5 }
  }
}
```

## 8. 当前业务规则

### 8.1 书源提取

支持：
- 直接数组
- `sources`
- `data`
- `list`
- 嵌套对象递归查找

### 8.2 去重

去重键：`bookSourceUrl`

标准化包括：
- 小写
- 去空白
- 去尾斜杠
- 去 `#` 后作者信息
- 去 URL 后拼接中文作者名

### 8.3 格式校验

满足以下条件视为格式有效：
- `bookSourceUrl` 存在
- 为字符串
- 以 `http://` 或 `https://` 开头

### 8.4 深度校验

当前规则：
- HEAD 优先，失败时回退 GET
- 200-399 视为有效
- 403 视为有效
- 默认重试 2 次
- 超时可选：15/30/45/60

### 8.5 远程 URL 安全校验

在线获取书源时会拒绝以下地址：
- `localhost`
- `.local`
- 回环地址
- 私网地址
- 链路本地地址
- 保留地址

### 8.6 分组回写

有效书源会保留原有分组，并追加：

```text
YYYY-MM-DD去重有效XXX条
```

## 9. 前端调用说明

前端封装文件：

[frontend/src/api/sources.js](../frontend/src/api/sources.js)

SSE 连接方式：

```javascript
new EventSource(`/api/validate/progress/${sessionId}`)
new EventSource(`/api/validate/search/progress/${sessionId}`)
```

## 10. 说明

- 早期设计文档中存在部分旧接口写法，例如 `progress?sessionId=...`，当前实现已统一为路径参数版。
- 如果文档与代码不一致，以代码为准。
