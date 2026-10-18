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
| POST | `/api/feedback` | 用户反馈提交 |
| POST | `/api/parse/file` | 单文件解析 |
| POST | `/api/parse/url` | 单 URL 解析 |
| POST | `/api/validate/start` | 从文件开始深度校验 |
| POST | `/api/validate/start-data` | 从已有书源数组开始深度校验 |
| GET | `/api/validate/progress/{session_id}` | 深度校验 SSE |
| GET | `/api/validate/result/{session_id}` | 获取校验完整结果（书源明细） |
| POST | `/api/validate/cancel` | 取消深度校验 |
| POST | `/api/validate/pause` | 暂停深度校验 |
| POST | `/api/validate/resume` | 恢复深度校验 |
| POST | `/api/parse/batch-files/start` | 批量文件 SSE 校验启动 |
| POST | `/api/parse/batch-urls/start` | 批量 URL SSE 校验启动 |
| POST | `/api/parse/batch-files` | 批量文件普通解析 |
| POST | `/api/parse/batch-urls` | 批量 URL 普通解析 |
| POST | `/api/validate/search/start` | 搜索校验启动（文件） |
| POST | `/api/validate/search/start-data` | 搜索校验启动（书源数组，用于失败重试） |
| GET | `/api/validate/search/progress/{session_id}` | 搜索校验 SSE |
| POST | `/api/export/book-source` | 创建临时导出链接 |
| GET | `/api/export/book-source/{export_id}` | 下载临时导出的书源 JSON |

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
| `failedGroups` | 失败详情，按原因分组（每组含 `category`：fixable/unfixable/checkable） |
| `fileStats` | 批量文件来源统计 |
| `urlStats` | 批量 URL 来源统计 |

## 4. 基础接口

### 4.1 健康检查

`GET /api/health`

返回：

```json
{
  "status": "ok",
  "presets": ["balanced", "fast", "stable", "turbo"]
}
```

`presets` 用于排查前后端版本不一致：如果前端已显示"极速"但这里没有 `turbo`，
说明后端未更新或未重启。

### 4.2 单文件解析

`POST /api/parse/file`

请求类型：`multipart/form-data`

字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | `.json` 或 `.txt`，内容需为 JSON |
| `mode` | string | `dedup` 或 `full` |
| `concurrency` | int | 并发数，范围 1-64，默认 16 |
| `timeout` | int | 超时秒数，范围 5-120，默认 30 |
| `validation_mode` | string | 预设：`turbo` / `fast` / `balanced` / `stable` / `custom`，默认 `custom` |
| `smart_enabled` | bool | 是否启用智能调参，默认 `true`（`turbo` 预设会强制关闭） |
| `filter_types` | string | 逗号分隔，如 `official,audio` |

以上运行时参数（concurrency/timeout/validation_mode/smart_enabled）适用于所有校验类接口。

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
- `validation_mode`
- `smart_enabled`

参数限制：
- `concurrency` 范围 1-64
- `timeout` 范围 5-120 秒

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

连接建立后服务端会先发送 `retry: 2000` 提示（浏览器断线后 2 秒重连），随后每 0.3 秒推送进度。校验 runner 独立于 SSE 连接运行，断线重连不会重复执行校验；终止状态会话结果在内存中保留 30 分钟，重连后可重放最终结果。

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
  "status": "running",
  "strategy": {
    "mode": "balanced",
    "smartEnabled": true,
    "phase": "primary",
    "currentConcurrency": 16,
    "currentTimeout": 30
  }
}
```

完成消息（**只含统计数字，不含书源明细**）：

```json
{
  "status": "completed",
  "processed": 100,
  "total": 100,
  "validCount": 92,
  "invalidCount": 8,
  "resultReady": true,
  "resultUrl": "/api/validate/result/abc12345",
  "strategy": {
    "mode": "balanced",
    "smartEnabled": true,
    "phase": "retry",
    "currentConcurrency": 16,
    "currentTimeout": 30
  }
}
```

> 设计说明：早期版本会把 `validSources` / `failedGroups` 全量数据塞进这条 SSE 消息，
> 上千条书源时单条消息可达数 MB，弱网或低带宽下极易被代理/移动网络掐断。
> 现在前端收到完成消息后，再通过 `GET /api/validate/result/{session_id}` 拉取明细，
> 该接口走普通 HTTP 并自动 GZip（实测 85KB → 16KB），且失败可重试。

### 5.4 获取完整结果

`GET /api/validate/result/{session_id}`

返回：

```json
{
  "code": 200,
  "data": {
    "status": "completed",
    "total": 125,
    "dedupCount": 110,
    "duplicates": 15,
    "formatInvalid": 3,
    "totalOriginal": 125,
    "validCount": 92,
    "invalidCount": 8,
    "validSources": [],
    "failedGroups": [],
    "failedCategories": {},
    "fileStats": null,
    "urlStats": null,
    "strategy": {}
  }
}
```

说明：
- 搜索校验会话额外返回 `ruleTypeStats`
- 会话不存在或已过期返回 `404`；未完成（运行中/暂停）返回 `code=409`
- 终态结果默认保留 30 分钟（`SESSION_RETENTION_SECONDS` 可配置）

### 5.5 取消

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

完成消息同样只含统计数字：

```json
{
  "status": "completed",
  "validCount": 120,
  "invalidCount": 80,
  "resultReady": true,
  "resultUrl": "/api/validate/result/abc12345",
  "strategy": {}
}
```

完整结果（含 `ruleTypeStats`）同样通过 `GET /api/validate/result/{session_id}` 获取：

```json
{
  "ruleTypeStats": {
    "searchOnly": { "valid": 10, "invalid": 5, "total": 15 },
    "exploreOnly": { "valid": 20, "invalid": 10, "total": 30 },
    "both": { "valid": 90, "invalid": 60, "total": 150 },
    "none": { "valid": 0, "invalid": 5, "total": 5 }
  }
}
```

搜索校验说明：

- 进度消息的 `strategy` 与深度校验一致，包含 `phase`（primary/retry）、
  `currentConcurrency`、`currentTimeout`
- 调度策略相同：首轮任务优先，全部结束后进入重试阶段；
  只有网络类失败（超时/连接失败等）会重试，规则类失败（无搜索规则、HTTP 4xx 等）不重试
- `ruleTypeStats` 对单一模式（仅搜索/仅发现）的有效与失效书源都会统计
- 结果接口返回的 `validSources` 已剥离 `_ruleType` 等内部字段

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
- HEAD 优先；仅当 HEAD 有响应但状态不可用（如 405/501）时才回退 GET
- HEAD 超时 / 连接失败直接判失败，不再用 GET 二次等待
- 200-399 视为有效
- 403 视为有效（Cloudflare 防护）
- 默认重试 2 次（指数退避）；重试只在首轮结束后进行
- 智能策略仅在出现"接近超时的成功样本"时才提高超时；全超时窗口保持基础值
- 超时范围 5-120 秒，默认 30
- 请求目标执行轻量 SSRF 拦截（本地主机名、私网/回环字面量 IP 返回"不允许访问该地址"）

### 8.5 远程 URL 安全校验

在线获取书源时会拒绝以下地址（异步 DNS 解析，全部 IP 必须为公网）：
- `localhost`
- `.local`
- 回环地址
- 私网地址
- 链路本地地址
- 保留地址

深度校验与搜索校验的请求目标还会执行轻量检查（不做 DNS 解析）：拦截本地主机名与私网/回环字面量 IP。

校验请求默认不校验证书（`VERIFY_SSL=false`），以兼容书源站点常见的过期/自签名证书；
如需更高安全性，可在 `.env` 中设置 `VERIFY_SSL=true`（部分证书异常站点会被判为失效）。

书源中的 JS 规则默认允许执行（`ENABLE_JS_EXECUTION=true`），但会拦截 `require` / `pyimport` /
`eval` / `new Function` 等危险模式，并跳过超过 `JS_MAX_CODE_LENGTH` 的代码；
对不可信书源可设置 `ENABLE_JS_EXECUTION=false`，只使用静态解析。

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
