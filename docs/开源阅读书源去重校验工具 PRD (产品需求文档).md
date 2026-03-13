开源阅读书源去重校验工具 PRD (产品需求文档)
1. 项目背景
开源阅读App用户通常需要管理大量书源（JSON格式），这些书源可能来自不同渠道，存在重复、失效条目。手动去重和校验费时费力。因此需要一个轻量、高效的Web工具，帮助用户上传或在线获取书源，自动去重（基于 bookSourceUrl）并标记失效书源，最终提供干净的JSON下载。

2. 目标用户
开源阅读App的普通用户

书源维护者、分享者

任何需要整理书源文件的技术爱好者

3. 核心功能
书源导入：支持上传本地JSON文件；支持输入在线URL并获取远程书源（需考虑CORS）；支持 Ctrl+V 快捷键直接粘贴链接解析。

智能去重：基于书源的 bookSourceUrl 字段进行去重，保留首次出现的书源。

格式校验：判断书源格式是否有效（必须存在 bookSourceUrl 且为合法的 http:// 或 https:// 链接）。

深度校验：通过模拟手机端请求，实际访问书源URL检测书源是否可访问，返回有效状态码（200-399）视为可用。支持 403 状态码特殊处理（Cloudflare 防护网站）。

类型过滤：支持过滤正版书籍、听书源、漫画源、影视源等特定类型书源。

统计展示：直观显示原始书源总数、去重后书源数、格式失效数、深度校验失效数。

结果下载：将去重后的有效书源数组导出为JSON文件，**保留原有分组**并追加新分组标签。

黑暗模式：支持亮色/暗色主题切换，自动保存用户偏好。

操作模式：
- 只查重复：仅执行去重操作，不进行深度校验，速度快
- 全部校验：执行去重 + 格式校验 + 深度校验，结果更准确

4. 数据定义
书源对象（示例）
json
{
  “bookSourceName”: “速读谷伪”,
  “bookSourceUrl”: “http://www.sudugu.co”,
  “bookSourceGroup”: “小说”,
  “bookSourceType”: 0,
  “bookSourceComment”: “优质书源”,
  “enabled”: true,
  “ruleSearch”: { ... },
  “ruleBookInfo”: { ... },
  “ruleToc”: { ... },
  “ruleContent”: { ... }
  // ... 其他字段
}
去重键：bookSourceUrl（字符串）

校验类型：
- 格式校验：bookSourceUrl 存在且为 http:// 或 https:// 协议
- 深度校验：模拟手机端请求访问 bookSourceUrl，HTTP 状态码 200-399 视为有效，403 视为有效（Cloudflare 防护）

类型过滤：
- bookSourceType 数值：0=文字, 1=音频, 2=图片, 3=正版
- 关键词检测：bookSourceComment 和 bookSourceName 中的关键词

手机端请求头（User-Agent）：
```
Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36
```

校验超时：单个书源校验超时时间可配置（15/30/45/60秒）

并发控制：支持 1/4/8/16/32 线程并发选择

5. 功能需求
模块	详细描述
上传文件	点击按钮选择本地JSON文件，自动解析。支持拖拽。
在线链接	输入URL，点击”获取”后通过后端代理请求（解决CORS），返回书源数据。支持 Ctrl+V 快捷键粘贴、📋 一键粘贴按钮。
数据解析	兼容常见的书源包装格式：直接数组、{ sources: [...] }、{ data: [...] } 等。
操作模式	提供两种操作模式按钮：
        • 只查重复：仅执行去重，速度快，适合快速处理大量书源
        • 全部校验：去重 + 格式校验 + 深度校验，结果更准确但耗时较长
类型过滤	勾选过滤类型（正版书籍、听书源、漫画源、影视源），勾选的类型将被移除。
并发设置	选择深度校验并发数（1/4/8/16/32），默认16线程。
超时设置	选择超时时间（15/30/45/60秒），默认30秒。
统计卡片	动态更新四个数字：原始总数、去重后书源数、格式失效数、深度校验失效数。
进度显示	深度校验时显示 SSE 实时进度条（已校验/总数、有效数、失败数、当前URL、耗时），支持取消操作。
失败分析	按失败原因分组展示失败书源，支持展开查看详情和导出失败列表。
下载按钮	仅当存在有效书源时可用，点击下载去重后的JSON文件。
主题切换	点击右上角按钮切换亮色/暗色主题，自动保存偏好。
错误提示	解析失败、网络错误时以醒目方式显示错误信息。
历史记录	自动记住用户设置（并发数、超时时间、主题偏好）。

6. 非功能需求
性能：处理10万条以内书源应无明显卡顿（后端优化去重算法、并发校验）。

可维护性：代码结构清晰，前后端分离，API设计规范。

安全性：上传文件大小限制（建议10MB）；对远程URL进行过滤，避免SSRF。

兼容性：支持现代浏览器（Chrome, Firefox, Edge）。

7. 技术栈
前端：Vue 3 + Vite + Element Plus（JavaScript）

后端：Python 3.10+ + FastAPI + Uvicorn

关键依赖：

文件上传：python-multipart

网络请求：httpx（支持异步）

CORS中间件：fastapi.middleware.cors

8. API设计（后端）
8.1 健康检查
GET /api/health
返回 {“status”: “ok”}

8.2 解析上传文件
POST /api/parse/file

请求：multipart/form-data
- file（JSON文件）
- mode（可选）：”dedup” 只查重复 | “full” 全部校验，默认 “dedup”
- concurrency（可选）：并发数，默认 16
- timeout（可选）：超时时间，默认 30
- filter_types（可选）：过滤类型，逗号分隔

响应：

json
{
  “code”: 200,
  “data”: {
    “total”: 125,
    “dedupCount”: 110,
    “duplicates”: 15,
    “duplicateUrls”: [“http://...”, ...],
    “formatInvalid”: 15,
    “deepInvalid”: 12,        // 仅 mode=full 时有值
    “validCount”: 98,
    “dedupedSources”: [ ... ], // 去重后的有效书源数组
    “failedGroups”: [         // 仅 mode=full 时有值
      {“reason”: “超时”, “count”: 5, “sources”: [...]}
    ]
  },
  “message”: “success”
}
8.3 解析在线链接
POST /api/parse/url

请求：{“url”: “https://example.com/sources.json”, “mode”: “full”, “concurrency”: 16, “timeout”: 30, “filter_types”: “audio,comic”}

响应格式同上。

8.4 开始深度校验（SSE模式）
POST /api/validate/start

请求：multipart/form-data
- file（JSON文件）
- concurrency（可选）：并发数
- timeout（可选）：超时时间
- filter_types（可选）：过滤类型

响应：
json
{
  “code”: 200,
  “sessionId”: “abc12345”,
  “total”: 125,
  “dedupCount”: 110,
  “formatInvalid”: 15,
  “deepTotal”: 98
}

8.5 深度校验进度（SSE 实时推送）
GET /api/validate/progress/{session_id}

响应：Server-Sent Events
```
data: {“processed”: 50, “total”: 100, “valid”: 45, “invalid”: 5, “current”: “https://example.com”, “status”: “running”}

data: {“status”: “completed”, “validCount”: 98, “invalidCount”: 12, “validSources”: [...], “failedGroups”: [...]}
```

8.6 从已解析数据开始深度校验
POST /api/validate/start-data

请求：{“sources”: [...], “concurrency”: 16, “timeout”: 30}

响应格式同 8.4

8.7 取消校验
POST /api/validate/cancel

请求：multipart/form-data
- session_id

响应：{“code”: 200, “message”: “已取消”}

8.8 错误响应
json
{
  “code”: 400,
  “message”: “文件解析失败：JSON格式错误”
}
9. 界面设计（文字原型）
整体布局
text
+---------------------------------------------------+
|   🌙/☀️ [主题切换]                                |
+---------------------------------------------------+
|   📚 阅读书源 · 净源工坊 (标题)                   |
|   ⚡ 上传/在线解析 · 自动去重深度校验              |
+---------------------------------------------------+
|                                                   |
|   [ 上传JSON文件 ]  (支持拖拽)                    |
|                                                   |
|   ---------------------------------------------   |
|                                                   |
|   在线链接: [输入框___________________] [📋] [获取] |
|   💡 提示：按 Ctrl+V 可直接粘贴链接解析           |
|                                                   |
+---------------------------------------------------+
|                                                   |
|   [ 🔍 只查重复 ]    [ ✅ 全部校验 ]              |
|   (快速去重)          (去重+深度校验)             |
|                                                   |
|   并发数: [16 ▼]   超时时间: [30秒 ▼]            |
|   过滤类型: □ 正版书籍 □ 听书源 □ 漫画源 □ 影视源 |
|                                                   |
+---------------------------------------------------+
|                                                   |
|   🔍 深度校验进行中...          50/100            |
|   [████████████░░░░░░░░] 50%                     |
|   ✅ 有效: 45  ❌ 失败: 5  ⏱️ 耗时: 32秒          |
|   当前: https://example.com...                   |
|   [ ⏹️ 取消校验 ]                                 |
|                                                   |
+---------------------------------------------------+
|                                                   |
|    📊 统计结果                                    |
|   +--------+ +--------+ +--------+ +--------+    |
|   |  125   | |  110   | |   15   | |   12   |    |
|   |总书源数| |去重后  | |格式失效| |深度失效|    |
|   +--------+ +--------+ +--------+ +--------+    |
|                                                   |
|   ❌ 失败书源分析                                 |
|   ▶ 超时 (5条)                                   |
|   ▶ 连接失败 (4条)                               |
|   ▼ HTTP 404 (3条)                               |
|     书源名称 - https://example.com               |
|   [ 📥 导出失败书源 ]                             |
|                                                   |
|   [ ⬇️ 下载去重后的JSON (98条) ]                  |
|                                                   |
+---------------------------------------------------+
|   ✦ 去重基于 bookSourceUrl 字段                   |
|   ✦ 深度校验模拟手机端请求，检测书源可访问性       |
+---------------------------------------------------+
交互说明
上传文件或在线解析后选择操作模式：
- 点击”只查重复”：立即执行去重，统计卡片刷新，下载按钮启用
- 点击”全部校验”：显示进度条，实时更新校验进度，完成后刷新统计

深度校验过程中可点击”取消”中断操作。

下载文件命名格式：阅读书源_去重有效_yyyy-mm-dd.json

书源分组格式：保留原有分组，追加新分组
- 原分组：`优质书源`
- 校验后：`优质书源,2026-03-12去重有效98条`

10. 已实现功能清单
✅ 书源导入（文件上传、在线链接）
✅ URL 标准化去重（小写、去斜杠、去空白）
✅ 重复 URL 可视化展示
✅ 格式校验
✅ 深度校验（并发、重试、403特殊处理）
✅ SSE 实时进度条
✅ 取消校验功能
✅ 失败原因分组展示
✅ 失败书源导出
✅ 用户设置历史记录
✅ 书本图标 Favicon
✅ 黑暗模式
✅ 书源类型过滤
✅ 分组保留原有分组
✅ Ctrl+V 快捷键粘贴解析
✅ 在线解析后支持深度校验

11. 附录：算法逻辑（后端实现）

11.1 去重算法
python
def dedupe_sources(raw_list):
    “””去重处理（URL标准化）”””
    total = len(raw_list)
    seen = set()
    deduped = []
    duplicate_urls = []

    for s in raw_list:
        url = s.get(“bookSourceUrl”, “”).strip().lower().rstrip(“/”)
        if url and url not in seen:
            seen.add(url)
            deduped.append(s)
        elif url:
            if len(duplicate_urls) < 20:
                duplicate_urls.append(url)

    return {
        “total”: total,
        “dedupCount”: len(deduped),
        “duplicates”: total - len(deduped),
        “duplicateUrls”: duplicate_urls,
        “dedupedSources”: deduped
    }

11.2 格式校验算法
python
def validate_format(sources):
    “””格式校验”””
    valid = []
    invalid = 0

    for s in sources:
        url = s.get(“bookSourceUrl”, “”)
        if url and isinstance(url, str):
            url = url.strip()
            if url.startswith((“http://”, “https://”)):
                valid.append(s)
                continue
        invalid += 1

    return valid, invalid

11.3 深度校验算法（使用手机端头信息）
python
import httpx
import asyncio

MOBILE_USER_AGENT = (
    “Mozilla/5.0 (Linux; Android 12; SM-G991B) “
    “AppleWebKit/537.36 (KHTML, like Gecko) “
    “Chrome/120.0.0.0 Mobile Safari/537.36”
)

async def validate_source_access(url: str, timeout: int = 30) -> tuple[bool, str]:
    “””深度校验单个书源，返回 (是否有效, 失败原因)”””
    headers = {
        “User-Agent”: MOBILE_USER_AGENT,
        “Accept”: “text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8”,
        “Accept-Language”: “zh-CN,zh;q=0.9”,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
            # 先尝试 HEAD
            try:
                response = await client.head(url, headers=headers)
                if response.status_code == 403:
                    return True, “”  # Cloudflare 防护，视为有效
                if 200 <= response.status_code < 400:
                    return True, “”
            except:
                pass

            # HEAD 失败尝试 GET
            response = await client.get(url, headers=headers)
            if response.status_code == 403:
                return True, “”
            if 200 <= response.status_code < 400:
                return True, “”
            return False, f”HTTP {response.status_code}”
    except httpx.TimeoutException:
        return False, “超时”
    except httpx.ConnectError:
        return False, “连接失败”
    except Exception as e:
        return False, type(e).__name__

async def deep_validate_sources(sources: list, concurrency: int = 16, timeout: int = 30, progress_callback=None):
    “””批量并发深度校验”””
    valid = []
    failed_sources = {}
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    processed = 0

    async def validate_single(source):
        nonlocal processed, valid, failed_sources
        url = source.get(“bookSourceUrl”, “”)
        name = source.get(“bookSourceName”, “”)

        async with semaphore:
            is_valid, reason = await validate_source_access(url, timeout)

            async with lock:
                processed += 1
                if is_valid:
                    valid.append(source)
                else:
                    if reason not in failed_sources:
                        failed_sources[reason] = []
                    failed_sources[reason].append({“url”: url, “name”: name, “reason”: reason})

                if progress_callback:
                    progress_callback(processed, len(sources), url, len(valid), len(failed_sources))

    tasks = [validate_single(s) for s in sources]
    await asyncio.gather(*tasks)

    return valid, failed_sources

11.4 类型过滤算法
python
class FilterService:
    # bookSourceType 数值映射
    SOURCE_TYPES = {
        'audio': 1,      # 听书/音频
        'image': 2,      # 图片/漫画
        'official': 3,   # 正版书籍
    }

    # 关键词过滤
    KEYWORDS = {
        'comic': ['漫画', 'manga', 'comic', '漫'],
        'video': ['影视', '电影', 'video', '电视剧'],
        'audio': ['听书', '有声', '喜马拉雅', 'FM', '听'],
        'official': ['正版', '官方'],
    }

    @staticmethod
    def filter_sources(sources: list, filter_types: list) -> list:
        “””过滤指定类型的书源”””
        filtered = []
        for source in sources:
            if FilterService._should_remove(source, filter_types):
                continue
            filtered.append(source)
        return filtered

    @staticmethod
    def _should_remove(source: dict, filter_types: list) -> bool:
        “””检查书源是否应该被移除”””
        source_type = source.get('bookSourceType')
        comment = str(source.get('bookSourceComment', '')).lower()
        name = str(source.get('bookSourceName', '')).lower()
        combined = comment + ' ' + name

        for ftype in filter_types:
            # 检查 bookSourceType
            if source_type == FilterService.SOURCE_TYPES.get(ftype):
                return True
            # 检查关键词
            if ftype in FilterService.KEYWORDS:
                for keyword in FilterService.KEYWORDS[ftype]:
                    if keyword.lower() in combined:
                        return True
        return False

文档版本：v1.2
最后更新：2026-03-12

