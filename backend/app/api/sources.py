# 书源解析路由
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, StreamingResponse
from typing import List, Optional
import json
import asyncio
import time
import logging

from app.models import (
    UrlParseRequest,
    ParseResponse,
    SourceData,
    BookSourceExportRequest,
    BookSourceExportResponse,
    BookSourceExportData,
)
from app.services import ParserService, DeduperService, ValidatorService, FilterService
from app.services.export_store import export_store
from app.services.session_manager import session_manager
from app.services.search_validator import categorize_failed_sources
from app.services.url_security import UrlSecurityService
from app.services.validation_scheduler import AdaptiveWorkQueue
from app.services.validation_strategy import (
    AdaptiveValidationController,
    ValidationOptions,
    get_retry_delay,
    is_retryable_reason,
    normalize_validation_options,
)
from app.config import settings

router = APIRouter()

logger = logging.getLogger(__name__)
SLOW_VALIDATION_SECONDS = 5 * 60


def calculate_rule_type_stats(valid_sources: List[dict], failed_sources: dict) -> dict:
    """
    计算规则类型统计

    Args:
        valid_sources: 有效书源列表
        failed_sources: 失败书源字典

    Returns:
        规则类型统计字典
    """
    stats = {
        'searchOnly': {'valid': 0, 'invalid': 0, 'total': 0},
        'exploreOnly': {'valid': 0, 'invalid': 0, 'total': 0},
        'both': {'valid': 0, 'invalid': 0, 'total': 0},
        'none': {'valid': 0, 'invalid': 0, 'total': 0}
    }

    # 统计有效书源
    for source in valid_sources:
        rule_type = source.get('_ruleType', '未知')
        if rule_type == '仅搜索':
            stats['searchOnly']['valid'] += 1
            stats['searchOnly']['total'] += 1
        elif rule_type == '仅发现':
            stats['exploreOnly']['valid'] += 1
            stats['exploreOnly']['total'] += 1
        elif rule_type == '搜索+发现':
            stats['both']['valid'] += 1
            stats['both']['total'] += 1

    # 统计失败书源
    for reason, sources_list in failed_sources.items():
        for source in sources_list:
            rule_type = source.get('_ruleType', '未知')
            if reason == '无规则':
                stats['none']['invalid'] += 1
                stats['none']['total'] += 1
            elif rule_type == '仅搜索':
                stats['searchOnly']['invalid'] += 1
                stats['searchOnly']['total'] += 1
            elif rule_type == '仅发现':
                stats['exploreOnly']['invalid'] += 1
                stats['exploreOnly']['total'] += 1
            elif rule_type == '搜索+发现':
                stats['both']['invalid'] += 1
                stats['both']['total'] += 1
            elif rule_type == '无规则':
                stats['none']['invalid'] += 1
                stats['none']['total'] += 1
            else:
                # 根据原因判断类型
                if '无搜索规则' in reason:
                    stats['exploreOnly']['invalid'] += 1
                    stats['exploreOnly']['total'] += 1
                elif '无发现规则' in reason:
                    stats['searchOnly']['invalid'] += 1
                    stats['searchOnly']['total'] += 1
                else:
                    # 默认归类
                    stats['both']['invalid'] += 1
                    stats['both']['total'] += 1

    return stats


def is_valid_source_file(filename: str) -> bool:
    """检查是否是有效的书源文件格式（.json 或 .txt）"""
    if not filename:
        return False
    lower_name = filename.lower()
    return lower_name.endswith('.json') or lower_name.endswith('.txt')


def validate_runtime_options(
    concurrency,
    timeout,
    validation_mode: str = "custom",
    smart_enabled=True,
) -> ValidationOptions:
    """校验并归一化运行时参数。"""
    return normalize_validation_options(
        concurrency=concurrency,
        timeout=timeout,
        mode=validation_mode,
        smart_enabled=smart_enabled,
    )


def append_failed_source(failed_sources: dict, reason: str, source: dict, url: str, name: str) -> None:
    """Append a failed source while preserving original source fields for retry/export."""
    if reason not in failed_sources:
        failed_sources[reason] = []
    failed_source = source.copy()
    failed_source.update({
        "url": url,
        "name": name,
        "reason": reason,
        "_failureReason": reason,
    })
    failed_sources[reason].append(failed_source)


def build_failed_groups(failed_sources: dict) -> list:
    """Build sorted failed groups from reason-indexed failed sources."""
    failed_groups = []
    for reason, sources_list in failed_sources.items():
        failed_groups.append({
            "reason": reason,
            "count": len(sources_list),
            "sources": sources_list
        })
    failed_groups.sort(key=lambda x: x["count"], reverse=True)
    return failed_groups


def build_empty_source_data(*, file_stats=None, url_stats=None) -> SourceData:
    """构造空结果，避免错误分支触发响应模型校验失败。"""
    return SourceData(
        total=0,
        dedupCount=0,
        duplicates=0,
        duplicateUrls=[],
        formatInvalid=0,
        deepInvalid=None,
        validCount=0,
        dedupedSources=[],
        fileStats=file_stats,
        urlStats=url_stats
    )


def normalize_export_filename(filename: str) -> str:
    """标准化导出文件名。"""
    safe_name = Path(filename or "").name.strip()
    if not safe_name:
        safe_name = "阅读书源_去重有效.json"
    if not safe_name.lower().endswith(".json"):
        safe_name = f"{safe_name}.json"
    return safe_name


@router.post("/parse/file", response_model=ParseResponse)
async def parse_file(
    file: UploadFile = File(...),
    mode: str = Form(default="dedup"),
    concurrency: int = Form(default=16),
    timeout: int = Form(default=30),
    validation_mode: str = Form(default="custom"),
    smart_enabled: bool = Form(default=True),
    filter_types: str = Form(default="")
):
    """
    解析上传的JSON文件

    Args:
        file: JSON或TXT文件（内容为JSON格式）
        mode: 操作模式 (dedup=只查重复, full=全部校验)
        concurrency: 深度校验并发数 (1/4/8/16/32)
        timeout: 深度校验超时时间 (15/30/45/60秒)
        filter_types: 过滤类型（逗号分隔：official,audio,comic,video）
    """
    logger.info(f"开始解析文件: {file.filename}, 模式: {mode}, 并发: {concurrency}, 超时: {timeout}, 过滤: {filter_types}")

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return ParseResponse(code=400, message=str(exc))

    # 1. 验证文件
    if not is_valid_source_file(file.filename):
        return ParseResponse(code=400, message="仅支持 JSON 或 TXT 格式文件")

    # 2. 检查文件大小
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        return ParseResponse(code=400, message=f"文件大小超过限制（最大{settings.MAX_FILE_SIZE // 1024 // 1024}MB）")

    # 3. 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return ParseResponse(code=400, message=f"JSON 解析失败：{str(e)}")

    # 4. 验证数据结构
    if not ParserService.validate_json_structure(data):
        return ParseResponse(code=400, message="书源数据格式不正确")

    # 5. 解析过滤类型
    filter_list = [f.strip() for f in filter_types.split(',') if f.strip()] if filter_types else []

    # 6. 处理书源
    result = await process_sources(data, mode, options, filter_list)
    return ParseResponse(data=result)


@router.post("/parse/url", response_model=ParseResponse)
async def parse_url(request: UrlParseRequest):
    """
    解析在线链接

    Args:
        request: 包含URL和操作模式的请求
    """
    logger.info(f"开始解析URL: {request.url}, 模式: {request.mode}, 并发: {request.concurrency}, 超时: {request.timeout}")

    try:
        options = validate_runtime_options(
            request.concurrency,
            request.timeout,
            request.validation_mode,
            request.smart_enabled,
        )
    except ValueError as exc:
        return ParseResponse(code=400, message=str(exc))

    # 1. 验证 URL
    if not request.url.startswith(('http://', 'https://')):
        return ParseResponse(code=400, message="仅支持 HTTP/HTTPS 协议")

    is_safe, error_message = UrlSecurityService.is_safe_remote_url(request.url)
    if not is_safe:
        return ParseResponse(code=400, message=error_message)

    # 2. 获取远程数据
    import httpx
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.get(request.url)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return ParseResponse(code=502, message="获取远程数据失败：连接超时")
    except httpx.HTTPStatusError as e:
        return ParseResponse(code=502, message=f"获取远程数据失败：HTTP {e.response.status_code}")
    except json.JSONDecodeError:
        return ParseResponse(code=400, message="获取远程数据失败：响应不是有效的JSON")
    except Exception as e:
        return ParseResponse(code=502, message=f"获取远程数据失败：{str(e)}")

    # 3. 验证数据结构
    if not ParserService.validate_json_structure(data):
        return ParseResponse(code=400, message="书源数据格式不正确")

    # 4. 解析过滤类型
    filter_list = request.filter_types.split(',') if request.filter_types else []

    # 5. 处理书源
    result = await process_sources(data, request.mode, options, filter_list)
    return ParseResponse(data=result)


@router.post("/export/book-source", response_model=BookSourceExportResponse)
async def create_book_source_export(payload: BookSourceExportRequest):
    """为移动端导出生成一个临时可访问的 JSON 链接。"""
    if not payload.sources:
        return BookSourceExportResponse(code=400, message="没有可导出的书源数据")

    filename = normalize_export_filename(payload.filename)
    content = json.dumps(payload.sources, ensure_ascii=False, indent=2)
    export_payload = await export_store.create_export(
        content=content,
        filename=filename,
        ttl_seconds=settings.EXPORT_TTL_SECONDS,
    )

    return BookSourceExportResponse(
        data=BookSourceExportData(
            exportId=export_payload.export_id,
            path=f"/api/export/book-source/{export_payload.export_id}",
            filename=export_payload.filename,
            expiresAt=export_payload.expires_at,
            ttlSeconds=settings.EXPORT_TTL_SECONDS,
        )
    )


@router.get("/export/book-source/{export_id}", name="download_exported_book_source")
async def download_exported_book_source(export_id: str):
    """下载临时导出的书源 JSON。"""
    export_payload = await export_store.get_export(export_id)
    if not export_payload:
        raise HTTPException(status_code=404, detail="导出链接不存在或已过期")

    quoted_filename = quote(export_payload.filename)
    headers = {
        "Cache-Control": "no-store, max-age=0",
        "Content-Disposition": (
            f"attachment; filename=book-sources.json; "
            f"filename*=UTF-8''{quoted_filename}"
        ),
    }
    return Response(
        content=export_payload.content,
        media_type="application/json",
        headers=headers,
    )


async def process_sources(
    data,
    mode: str = "dedup",
    options: Optional[ValidationOptions] = None,
    filter_types: list = None,
) -> SourceData:
    """
    处理书源数据

    Args:
        data: 解析后的JSON数据
        mode: 操作模式
        concurrency: 深度校验并发数
        timeout: 深度校验超时时间
        filter_types: 过滤类型列表

    Returns:
        处理结果
    """
    if filter_types is None:
        filter_types = []
    if options is None:
        options = validate_runtime_options(16, 30)
    started_at = time.perf_counter()

    # 步骤1：提取书源数组
    sources = ParserService.extract_sources(data)
    total = len(sources)
    logger.info(f"提取书源数量: {total}")

    # 打印前5个书源的URL用于调试
    for i, s in enumerate(sources[:5]):
        url = s.get('bookSourceUrl', 'N/A')
        logger.debug(f"书源{i+1} URL: {url}")

    # 步骤2：去重
    deduped, duplicates, duplicate_urls = DeduperService.dedupe(sources)
    logger.info(f"去重后数量: {len(deduped)}, 重复数量: {duplicates}")

    # 步骤3：类型过滤（在格式校验前过滤）
    if filter_types:
        filter_count = FilterService.get_filter_count(deduped, filter_types)
        deduped = FilterService.filter_sources(deduped, filter_types)
        logger.info(f"类型过滤 - 移除: {filter_count}, 剩余: {len(deduped)}")

    # 步骤4：格式校验
    format_valid, format_invalid = ValidatorService.format_validate(deduped)
    logger.info(f"格式校验 - 有效: {len(format_valid)}, 失效: {format_invalid}")

    # 步骤5：深度校验（仅 mode=full）
    deep_invalid = None
    failed_groups = None
    final_valid = format_valid

    if mode == "full":
        final_valid, deep_invalid, failed_groups = await ValidatorService.deep_validate(
            format_valid,
            options.concurrency,
            options.timeout,
            max_retries=options.max_retries,
        )
        logger.info(f"深度校验完成 - 有效: {len(final_valid)}, 失效: {deep_invalid}")

    # 步骤6：设置分组
    valid_count = len(final_valid)
    ValidatorService.set_source_group(final_valid, valid_count)
    elapsed = time.perf_counter() - started_at
    log_method = logger.warning if elapsed >= SLOW_VALIDATION_SECONDS else logger.info
    log_method(
        "校验批次完成: mode=%s total=%s dedup=%s duplicates=%s format_invalid=%s "
        "deep_invalid=%s valid=%s concurrency=%s timeout=%s duration=%.2fs",
        mode,
        total,
        len(deduped),
        duplicates,
        format_invalid,
        deep_invalid,
        valid_count,
        options.concurrency,
        options.timeout,
        elapsed,
    )

    return SourceData(
        total=total,
        dedupCount=len(deduped),
        duplicates=duplicates,
        duplicateUrls=duplicate_urls,
        formatInvalid=format_invalid,
        deepInvalid=deep_invalid,
        validCount=valid_count,
        dedupedSources=final_valid,
        failedGroups=failed_groups
    )


# ===================== SSE 实时进度接口 =====================

@router.post("/validate/start")
async def start_validation(
    file: UploadFile = File(...),
    concurrency: int = Form(default=16),
    timeout: int = Form(default=30),
    validation_mode: str = Form(default="custom"),
    smart_enabled: bool = Form(default=True),
    filter_types: str = Form(default="")
):
    """
    开始深度校验（SSE模式）- 文件上传

    返回 session_id，前端通过 SSE 获取实时进度
    """
    logger.info(f"开始SSE校验: {file.filename}, 并发: {concurrency}, 超时: {timeout}, 过滤: {filter_types}")

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return {"code": 400, "message": str(exc)}

    # 1. 验证文件
    if not is_valid_source_file(file.filename):
        return {"code": 400, "message": "仅支持 JSON 或 TXT 格式文件"}

    # 2. 检查文件大小
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        return {"code": 400, "message": f"文件大小超过限制"}

    # 3. 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return {"code": 400, "message": f"JSON 解析失败：{str(e)}"}

    # 4. 验证数据结构
    if not ParserService.validate_json_structure(data):
        return {"code": 400, "message": "书源数据格式不正确"}

    # 5. 解析过滤类型
    filter_list = [f.strip() for f in filter_types.split(',') if f.strip()] if filter_types else []

    # 6. 处理书源（去重 + 格式校验 + 类型过滤）
    sources = ParserService.extract_sources(data)
    deduped, duplicates, duplicate_urls = DeduperService.dedupe(sources)

    # 类型过滤
    if filter_list:
        deduped = FilterService.filter_sources(deduped, filter_list)

    format_valid, format_invalid = ValidatorService.format_validate(deduped)

    # 7. 创建会话
    session_id = await session_manager.create_session(
        format_valid,
        options.concurrency,
        options.timeout,
        options.mode,
        options.smart_enabled,
        options.max_retries,
    )
    logger.info(
        "SSE校验会话创建: session_id=%s total=%s dedup=%s duplicates=%s "
        "format_invalid=%s deep_total=%s concurrency=%s timeout=%s",
        session_id,
        len(sources),
        len(deduped),
        duplicates,
        format_invalid,
        len(format_valid),
        options.concurrency,
        options.timeout,
    )

    return {
        "code": 200,
        "sessionId": session_id,
        "total": len(sources),
        "dedupCount": len(deduped),
        "duplicates": duplicates,
        "formatInvalid": format_invalid,
        "deepTotal": len(format_valid),
        "validationMode": options.mode,
        "smartEnabled": options.smart_enabled,
        "message": "会话创建成功"
    }


@router.post("/validate/start-data")
async def start_validation_from_data(request: dict):
    """
    开始深度校验（SSE模式）- 从已解析数据

    用于在线链接解析后的深度校验
    """
    sources = request.get('sources', [])
    concurrency = request.get('concurrency', 16)
    timeout = request.get('timeout', 30)
    validation_mode = request.get('validation_mode', 'custom')
    smart_enabled = request.get('smart_enabled', True)

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return {"code": 400, "message": str(exc)}

    logger.info(f"开始SSE校验(数据): 书源数: {len(sources)}, 并发: {options.concurrency}, 超时: {options.timeout}")

    if not sources:
        return {"code": 400, "message": "书源数据为空"}

    # 创建会话
    session_id = await session_manager.create_session(
        sources,
        options.concurrency,
        options.timeout,
        options.mode,
        options.smart_enabled,
        options.max_retries,
    )
    logger.info(
        "SSE数据校验会话创建: session_id=%s deep_total=%s concurrency=%s timeout=%s",
        session_id,
        len(sources),
        options.concurrency,
        options.timeout,
    )

    return {
        "code": 200,
        "sessionId": session_id,
        "deepTotal": len(sources),
        "validationMode": options.mode,
        "smartEnabled": options.smart_enabled,
        "message": "会话创建成功"
    }


@router.get("/validate/progress/{session_id}")
async def get_validation_progress(session_id: str):
    """
    SSE 实时进度推送
    """
    async def event_generator():
        session = await session_manager.get_session(session_id)
        if not session:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        # 标记运行中
        async with session_manager._lock:
            session.status = "running"

        # 存储校验任务，用于取消
        validation_tasks = []

        # 启动校验任务
        async def run_validation():
            nonlocal validation_tasks
            started_at = time.perf_counter()
            try:
                valid_sources = []
                failed_sources = {}
                total = len(session.sources)
                processed = 0
                running_tasks = set()
                options = ValidationOptions(
                    concurrency=session.concurrency,
                    timeout=session.timeout,
                    mode=session.validation_mode,
                    smart_enabled=session.smart_enabled,
                    max_retries=session.max_retries,
                )
                controller = AdaptiveValidationController(options)
                work_queue = AdaptiveWorkQueue(
                    session.sources,
                    options.max_retries,
                )

                async def validate_single(
                    work_item,
                    client,
                    request_timeout,
                ):
                    source = work_item.source
                    url = ValidatorService.clean_source_url(source.get('bookSourceUrl', ''))
                    name = source.get('bookSourceName', '')
                    started = time.perf_counter()
                    is_valid, reason = await ValidatorService.validate_source_access(
                        url,
                        request_timeout,
                        client=client,
                        max_retries=0,
                    )
                    duration = time.perf_counter() - started
                    return work_item, url, name, is_valid, reason, duration

                def process_completed_tasks(done_tasks):
                    nonlocal processed
                    for task in done_tasks:
                        if task.cancelled():
                            continue
                        exc = task.exception()
                        if exc:
                            logger.warning(
                                "单个书源校验异常: session_id=%s error=%s",
                                session_id,
                                exc,
                            )
                            continue

                        (
                            work_item,
                            url,
                            name,
                            is_valid,
                            reason,
                            duration,
                        ) = task.result()
                        if work_item.attempt == 0:
                            adjustment = controller.record(
                                duration,
                                is_valid,
                                reason,
                            )
                            if adjustment is not None:
                                logger.info(
                                    "智能策略评估: session_id=%s phase=%s "
                                    "samples=%s network_error_rate=%.3f "
                                    "timeout_rate=%.3f p75=%.2f "
                                    "concurrency=%s->%s timeout=%s->%s "
                                    "reason=%s",
                                    session_id,
                                    session.validation_phase,
                                    adjustment.sample_count,
                                    adjustment.network_error_rate,
                                    adjustment.timeout_rate,
                                    adjustment.p75_duration,
                                    adjustment.previous_concurrency,
                                    adjustment.current_concurrency,
                                    adjustment.previous_timeout,
                                    adjustment.current_timeout,
                                    adjustment.reason,
                                )

                        scheduled_retry = False
                        if not is_valid and is_retryable_reason(reason):
                            if work_item.attempt == 0:
                                session.primary_network_failures += 1
                            scheduled_retry = work_queue.schedule_retry(
                                work_item,
                                reason,
                                now=time.monotonic(),
                                delay=get_retry_delay(
                                    work_item.attempt,
                                    settings.RETRY_DELAY,
                                ),
                            )

                        if not scheduled_retry:
                            processed += 1
                            if is_valid:
                                valid_sources.append(work_item.source)
                            else:
                                append_failed_source(
                                    failed_sources,
                                    reason,
                                    work_item.source,
                                    url,
                                    name,
                                )

                        snapshot = controller.snapshot()
                        session.current_concurrency = snapshot[
                            "currentConcurrency"
                        ]
                        session.current_timeout = snapshot["currentTimeout"]
                        total_failed = sum(
                            len(items) for items in failed_sources.values()
                        )
                        session.processed = processed
                        session.valid = len(valid_sources)
                        session.invalid = total_failed
                        session.current_url = url
                        session.current_name = name
                        session.valid_sources = valid_sources
                        session.failed_sources = failed_sources

                async with ValidatorService.create_validation_client(options.timeout) as client:
                    while work_queue.has_work or running_tasks:
                        if session.status == "cancelled":
                            completed_tasks = {
                                task for task in running_tasks if task.done()
                            }
                            for task in running_tasks - completed_tasks:
                                task.cancel()
                            process_completed_tasks(completed_tasks)
                            break

                        if session.status == "paused":
                            if not running_tasks:
                                await asyncio.sleep(0.3)
                                continue
                            done, running_tasks = await asyncio.wait(
                                running_tasks,
                                timeout=0.3,
                                return_when=asyncio.FIRST_COMPLETED,
                            )
                            process_completed_tasks(done)
                            continue

                        work_queue.advance_phase(
                            active_count=len(running_tasks),
                        )
                        session.validation_phase = work_queue.phase
                        active_limit = controller.current_concurrency
                        if work_queue.phase == "retry":
                            active_limit = min(
                                active_limit,
                                controller.min_concurrency,
                            )

                        capacity = max(
                            0,
                            active_limit - len(running_tasks),
                        )
                        ready_items = work_queue.take_ready(
                            limit=capacity,
                            now=time.monotonic(),
                        )
                        for work_item in ready_items:
                            if work_item.attempt > 0:
                                session.retry_attempts += 1
                            task = asyncio.create_task(
                                validate_single(
                                    work_item,
                                    client,
                                    controller.current_timeout,
                                )
                            )
                            running_tasks.add(task)

                        validation_tasks = list(running_tasks)
                        session.validation_tasks = validation_tasks
                        if not running_tasks:
                            delay = work_queue.next_delay(
                                now=time.monotonic(),
                            )
                            await asyncio.sleep(
                                min(delay if delay is not None else 0.1, 0.3)
                            )
                            continue

                        done, running_tasks = await asyncio.wait(
                            running_tasks,
                            timeout=0.3,
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        process_completed_tasks(done)

                # 只有未取消时才完成会话
                if session.status != "cancelled":
                    await session_manager.complete_session(session_id, valid_sources, failed_sources)
                    elapsed = time.perf_counter() - started_at
                    invalid_count = sum(len(v) for v in failed_sources.values())
                    log_method = logger.warning if elapsed >= SLOW_VALIDATION_SECONDS else logger.info
                    log_method(
                        "SSE校验完成: session_id=%s total=%s valid=%s invalid=%s "
                        "concurrency=%s timeout=%s duration=%.2fs "
                        "final_concurrency=%s final_timeout=%s "
                        "primary_network_failures=%s retries=%s",
                        session_id,
                        total,
                        len(valid_sources),
                        invalid_count,
                        session.concurrency,
                        session.timeout,
                        elapsed,
                        session.current_concurrency,
                        session.current_timeout,
                        session.primary_network_failures,
                        session.retry_attempts,
                    )

            except asyncio.CancelledError:
                elapsed = time.perf_counter() - started_at
                logger.info("SSE校验任务被取消: session_id=%s duration=%.2fs", session_id, elapsed)
            except Exception:
                logger.exception("SSE校验异常: session_id=%s", session_id)
                session.status = "error"

        # 后台运行校验
        validation_task = asyncio.create_task(run_validation())

        # 持续推送进度（直接使用 session 引用，不加锁）
        while True:
            # 检查是否完成（直接读取 session.status）
            if session.status in ["completed", "cancelled", "error"]:
                if session.status == "completed":
                    # 先获取数据，再删除会话
                    valid_sources = session.valid_sources
                    failed_sources = session.failed_sources

                    failed_groups = build_failed_groups(failed_sources)

                    # 设置分组
                    ValidatorService.set_source_group(valid_sources, len(valid_sources))

                    result_data = {
                        "status": "completed",
                        "processed": session.total,
                        "total": session.total,
                        "valid": len(valid_sources),
                        "invalid": sum(len(v) for v in failed_sources.values()),
                        "validCount": len(valid_sources),
                        "invalidCount": sum(len(v) for v in failed_sources.values()),
                        "validSources": valid_sources,
                        "failedGroups": failed_groups,
                        "failedCategories": categorize_failed_sources(failed_groups),
                        # 批量处理额外信息
                        "fileStats": session.file_stats,
                        "urlStats": session.url_stats,
                        "dedupCount": session.dedup_count if session.dedup_count else session.total,
                        "duplicates": session.duplicates,
                        "formatInvalid": session.format_invalid,
                        "totalOriginal": session.total_original if session.total_original else session.total,
                        "strategy": {
                            "mode": session.validation_mode,
                            "smartEnabled": session.smart_enabled,
                            "phase": session.validation_phase,
                            "currentConcurrency": session.current_concurrency,
                            "currentTimeout": session.current_timeout,
                        },
                    }
                    logger.info(f"SSE完成消息: validCount={len(valid_sources)}, invalidCount={sum(len(v) for v in failed_sources.values())}, validSources数量={len(valid_sources)}, failedGroups数量={len(failed_groups)}")
                    yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                elif session.status == "cancelled":
                    valid_sources = session.valid_sources
                    failed_sources = session.failed_sources
                    failed_groups = build_failed_groups(failed_sources)
                    ValidatorService.set_source_group(valid_sources, len(valid_sources))
                    result_data = {
                        "status": "cancelled",
                        "processed": session.processed,
                        "total": session.total,
                        "valid": len(valid_sources),
                        "invalid": sum(len(v) for v in failed_sources.values()),
                        "validCount": len(valid_sources),
                        "invalidCount": sum(len(v) for v in failed_sources.values()),
                        "validSources": valid_sources,
                        "failedGroups": failed_groups,
                        "failedCategories": categorize_failed_sources(failed_groups),
                        "partial": True,
                        "fileStats": session.file_stats,
                        "urlStats": session.url_stats,
                        "dedupCount": session.dedup_count if session.dedup_count else session.total,
                        "duplicates": session.duplicates,
                        "formatInvalid": session.format_invalid,
                        "totalOriginal": session.total_original if session.total_original else session.total,
                        "strategy": {
                            "mode": session.validation_mode,
                            "smartEnabled": session.smart_enabled,
                            "phase": session.validation_phase,
                            "currentConcurrency": session.current_concurrency,
                            "currentTimeout": session.current_timeout,
                        },
                    }
                    yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                elif session.status == "error":
                    yield f"data: {json.dumps({'status': 'error', 'error': '校验过程发生错误'})}\n\n"

                # 清理会话
                await session_manager.delete_session(session_id)
                break

            # 发送进度消息（不包含 completed 状态）
            # 计算已耗时和预估剩余时间
            elapsed = time.time() - session.start_time if session.start_time > 0 else 0
            estimated_remaining = 0
            if session.processed > 0 and session.processed < session.total:
                avg_time = elapsed / session.processed
                estimated_remaining = (session.total - session.processed) * avg_time

            progress_data = {
                "processed": session.processed,
                "total": session.total,
                "valid": session.valid,
                "invalid": session.invalid,
                "current": session.current_url,
                "currentName": session.current_name,
                "elapsed": round(elapsed, 1),
                "estimatedRemaining": round(estimated_remaining, 1),
                "status": session.status,
                "strategy": {
                    "mode": session.validation_mode,
                    "smartEnabled": session.smart_enabled,
                    "phase": session.validation_phase,
                    "currentConcurrency": session.current_concurrency,
                    "currentTimeout": session.current_timeout,
                },
            }

            yield f"data: {json.dumps(progress_data)}\n\n"

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/validate/cancel")
async def cancel_validation(session_id: str = Form(...)):
    """取消校验"""
    await session_manager.cancel_session(session_id)
    logger.info("校验取消请求: session_id=%s", session_id)
    return {"code": 200, "message": "已取消"}


@router.post("/validate/pause")
async def pause_validation(session_id: str = Form(...)):
    """暂停校验。"""
    await session_manager.pause_session(session_id)
    logger.info("校验暂停请求: session_id=%s", session_id)
    return {"code": 200, "message": "已暂停"}


@router.post("/validate/resume")
async def resume_validation(session_id: str = Form(...)):
    """恢复校验。"""
    await session_manager.resume_session(session_id)
    logger.info("校验恢复请求: session_id=%s", session_id)
    return {"code": 200, "message": "已恢复"}


# ===================== 批量处理接口 =====================

@router.post("/parse/batch-files/start")
async def start_batch_files_validation(
    files: List[UploadFile] = File(...),
    concurrency: int = Form(default=16),
    timeout: int = Form(default=30),
    validation_mode: str = Form(default="custom"),
    smart_enabled: bool = Form(default=True),
    filter_types: str = Form(default="")
):
    """
    批量解析多个JSON文件（SSE模式）

    合并所有文件的书源后统一去重校验，支持实时进度
    """
    logger.info(f"开始批量解析(SSE) {len(files)} 个文件")

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return {"code": 400, "message": str(exc)}

    all_sources = []
    file_stats = []

    for file in files:
        if not is_valid_source_file(file.filename):
            file_stats.append({"name": file.filename or "unknown", "valid": False, "error": "仅支持JSON/TXT格式"})
            continue

        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            file_stats.append({"name": file.filename, "valid": False, "error": "文件过大"})
            continue

        try:
            data = json.loads(content)
            if not ParserService.validate_json_structure(data):
                file_stats.append({"name": file.filename, "valid": False, "error": "格式不正确"})
                continue

            sources = ParserService.extract_sources(data)
            all_sources.extend(sources)
            file_stats.append({"name": file.filename, "valid": True, "count": len(sources)})

        except json.JSONDecodeError as e:
            file_stats.append({"name": file.filename, "valid": False, "error": f"JSON解析失败"})
        except Exception as e:
            file_stats.append({"name": file.filename, "valid": False, "error": str(e)})

    if not all_sources:
        return {"code": 400, "message": "没有有效的书源数据", "fileStats": file_stats}

    # 解析过滤类型
    filter_list = [f.strip() for f in filter_types.split(',') if f.strip()] if filter_types else []

    # 去重和格式校验
    deduped, duplicates, duplicate_urls = DeduperService.dedupe(all_sources)

    if filter_list:
        deduped = FilterService.filter_sources(deduped, filter_list)

    format_valid, format_invalid = ValidatorService.format_validate(deduped)

    # 创建会话
    session_id = await session_manager.create_session(
        format_valid,
        options.concurrency,
        options.timeout,
        options.mode,
        options.smart_enabled,
        options.max_retries,
    )
    logger.info(
        "批量文件SSE会话创建: session_id=%s files=%s total=%s dedup=%s "
        "duplicates=%s format_invalid=%s deep_total=%s concurrency=%s timeout=%s",
        session_id,
        len(files),
        len(all_sources),
        len(deduped),
        duplicates,
        format_invalid,
        len(format_valid),
        options.concurrency,
        options.timeout,
    )

    # 保存文件统计到会话（直接访问 _sessions，避免死锁）
    async with session_manager._lock:
        session = session_manager._sessions.get(session_id)
        if session:
            session.file_stats = file_stats
            session.dedup_count = len(deduped)
            session.duplicates = duplicates
            session.format_invalid = format_invalid
            session.total_original = len(all_sources)

    return {
        "code": 200,
        "sessionId": session_id,
        "total": len(all_sources),
        "dedupCount": len(deduped),
        "duplicates": duplicates,
        "formatInvalid": format_invalid,
        "deepTotal": len(format_valid),
        "fileStats": file_stats,
        "validationMode": options.mode,
        "smartEnabled": options.smart_enabled,
        "message": "会话创建成功"
    }


@router.post("/parse/batch-urls/start")
async def start_batch_urls_validation(request: dict):
    """
    批量解析多个在线链接（SSE模式）

    合并所有URL的书源后统一去重校验，支持实时进度
    """
    urls = request.get('urls', [])
    concurrency = request.get('concurrency', 16)
    timeout = request.get('timeout', 30)
    validation_mode = request.get('validation_mode', 'custom')
    smart_enabled = request.get('smart_enabled', True)
    filter_types = request.get('filter_types', '')

    logger.info(f"开始批量解析(SSE) {len(urls)} 个URL")

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return {"code": 400, "message": str(exc)}

    if not urls:
        return {"code": 400, "message": "URL列表为空"}

    all_sources = []
    url_stats = []

    import httpx
    async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                url_stats.append({"url": url, "valid": False, "error": "无效URL"})
                continue

            is_safe, error_message = UrlSecurityService.is_safe_remote_url(url)
            if not is_safe:
                url_stats.append({"url": url, "valid": False, "error": error_message})
                continue

            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                if not ParserService.validate_json_structure(data):
                    url_stats.append({"url": url, "valid": False, "error": "格式不正确"})
                    continue

                sources = ParserService.extract_sources(data)
                all_sources.extend(sources)
                url_stats.append({"url": url, "valid": True, "count": len(sources)})

            except httpx.TimeoutException:
                url_stats.append({"url": url, "valid": False, "error": "连接超时"})
            except httpx.HTTPStatusError as e:
                url_stats.append({"url": url, "valid": False, "error": f"HTTP {e.response.status_code}"})
            except json.JSONDecodeError:
                url_stats.append({"url": url, "valid": False, "error": "响应不是有效JSON"})
            except Exception as e:
                url_stats.append({"url": url, "valid": False, "error": str(e)})

    if not all_sources:
        return {"code": 400, "message": "没有有效的书源数据", "urlStats": url_stats}

    # 解析过滤类型
    filter_list = filter_types.split(',') if filter_types else []

    # 去重和格式校验
    deduped, duplicates, duplicate_urls = DeduperService.dedupe(all_sources)

    if filter_list:
        deduped = FilterService.filter_sources(deduped, filter_list)

    format_valid, format_invalid = ValidatorService.format_validate(deduped)

    # 创建会话
    session_id = await session_manager.create_session(
        format_valid,
        options.concurrency,
        options.timeout,
        options.mode,
        options.smart_enabled,
        options.max_retries,
    )
    logger.info(
        "批量URL SSE会话创建: session_id=%s urls=%s total=%s dedup=%s "
        "duplicates=%s format_invalid=%s deep_total=%s concurrency=%s timeout=%s",
        session_id,
        len(urls),
        len(all_sources),
        len(deduped),
        duplicates,
        format_invalid,
        len(format_valid),
        options.concurrency,
        options.timeout,
    )

    # 保存统计到会话（直接访问 _sessions，避免死锁）
    async with session_manager._lock:
        session = session_manager._sessions.get(session_id)
        if session:
            session.url_stats = url_stats
            session.dedup_count = len(deduped)
            session.duplicates = duplicates
            session.format_invalid = format_invalid
            session.total_original = len(all_sources)

    return {
        "code": 200,
        "sessionId": session_id,
        "total": len(all_sources),
        "dedupCount": len(deduped),
        "duplicates": duplicates,
        "formatInvalid": format_invalid,
        "deepTotal": len(format_valid),
        "urlStats": url_stats,
        "validationMode": options.mode,
        "smartEnabled": options.smart_enabled,
        "message": "会话创建成功"
    }


@router.post("/parse/batch-files", response_model=ParseResponse)
async def parse_batch_files(
    files: List[UploadFile] = File(...),
    mode: str = Form(default="dedup"),
    concurrency: int = Form(default=16),
    timeout: int = Form(default=30),
    validation_mode: str = Form(default="custom"),
    smart_enabled: bool = Form(default=True),
    filter_types: str = Form(default="")
):
    """
    批量解析多个JSON文件

    合并所有文件的书源后统一去重校验
    """
    logger.info(f"开始批量解析 {len(files)} 个文件, 模式: {mode}")

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return ParseResponse(code=400, message=str(exc))

    all_sources = []
    file_stats = []

    for file in files:
        # 验证文件
        if not is_valid_source_file(file.filename):
            file_stats.append({"name": file.filename or "unknown", "valid": False, "error": "仅支持JSON/TXT格式"})
            continue

        # 检查文件大小
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            file_stats.append({"name": file.filename, "valid": False, "error": "文件过大"})
            continue

        # 解析 JSON
        try:
            data = json.loads(content)
            if not ParserService.validate_json_structure(data):
                file_stats.append({"name": file.filename, "valid": False, "error": "格式不正确"})
                continue

            sources = ParserService.extract_sources(data)
            all_sources.extend(sources)
            file_stats.append({"name": file.filename, "valid": True, "count": len(sources)})
            logger.info(f"文件 {file.filename}: {len(sources)} 条书源")

        except json.JSONDecodeError as e:
            file_stats.append({"name": file.filename, "valid": False, "error": f"JSON解析失败: {str(e)}"})
        except Exception as e:
            file_stats.append({"name": file.filename, "valid": False, "error": str(e)})

    if not all_sources:
        return ParseResponse(
            code=400,
            message="没有有效的书源数据",
            data=build_empty_source_data(file_stats=file_stats)
        )

    # 解析过滤类型
    filter_list = [f.strip() for f in filter_types.split(',') if f.strip()] if filter_types else []

    # 处理合并后的书源
    result = await process_sources({"sources": all_sources}, mode, options, filter_list)

    # 添加文件统计信息
    result.fileStats = file_stats

    return ParseResponse(data=result)


@router.post("/parse/batch-urls", response_model=ParseResponse)
async def parse_batch_urls(request: dict):
    """
    批量解析多个在线链接

    合并所有URL的书源后统一去重校验
    """
    urls = request.get('urls', [])
    mode = request.get('mode', 'dedup')
    concurrency = request.get('concurrency', 16)
    timeout = request.get('timeout', 30)
    validation_mode = request.get('validation_mode', 'custom')
    smart_enabled = request.get('smart_enabled', True)
    filter_types = request.get('filter_types', '')

    logger.info(f"开始批量解析 {len(urls)} 个URL, 模式: {mode}")

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return ParseResponse(code=400, message=str(exc))

    if not urls:
        return ParseResponse(code=400, message="URL列表为空")

    all_sources = []
    url_stats = []

    import httpx
    async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
        for url in urls:
            # 验证 URL
            if not url.startswith(('http://', 'https://')):
                url_stats.append({"url": url, "valid": False, "error": "无效URL"})
                continue

            is_safe, error_message = UrlSecurityService.is_safe_remote_url(url)
            if not is_safe:
                url_stats.append({"url": url, "valid": False, "error": error_message})
                continue

            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                if not ParserService.validate_json_structure(data):
                    url_stats.append({"url": url, "valid": False, "error": "格式不正确"})
                    continue

                sources = ParserService.extract_sources(data)
                all_sources.extend(sources)
                url_stats.append({"url": url, "valid": True, "count": len(sources)})
                logger.info(f"URL {url}: {len(sources)} 条书源")

            except httpx.TimeoutException:
                url_stats.append({"url": url, "valid": False, "error": "连接超时"})
            except httpx.HTTPStatusError as e:
                url_stats.append({"url": url, "valid": False, "error": f"HTTP {e.response.status_code}"})
            except json.JSONDecodeError:
                url_stats.append({"url": url, "valid": False, "error": "响应不是有效JSON"})
            except Exception as e:
                url_stats.append({"url": url, "valid": False, "error": str(e)})

    if not all_sources:
        return ParseResponse(
            code=400,
            message="没有有效的书源数据",
            data=build_empty_source_data(url_stats=url_stats)
        )

    # 解析过滤类型
    filter_list = filter_types.split(',') if filter_types else []

    # 处理合并后的书源
    result = await process_sources({"sources": all_sources}, mode, options, filter_list)

    # 添加URL统计信息
    result.urlStats = url_stats

    return ParseResponse(data=result)


# ===================== 搜索校验接口 =====================

from app.services.search_validator import SearchValidatorService


@router.post("/validate/search/start")
async def start_search_validation(
    file: UploadFile = File(...),
    keyword: str = Form(default="玄幻"),
    validate_type: str = Form(default="search"),  # 'search' 或 'explore'
    concurrency: int = Form(default=16),
    timeout: int = Form(default=30),
    validation_mode: str = Form(default="custom"),
    smart_enabled: bool = Form(default=True),
):
    """
    开始搜索校验（SSE模式）

    Args:
        file: JSON文件
        keyword: 搜索关键词（search模式使用）
        validate_type: 校验类型 'search' 或 'explore'
        concurrency: 并发数
        timeout: 超时时间
    """
    logger.info(f"=== [搜索校验] 开始处理 ===")
    logger.info(f"[搜索校验] 文件: {file.filename}, 关键词: {keyword}, 类型: {validate_type}")

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return {"code": 400, "message": str(exc)}

    # 1. 验证文件
    if not is_valid_source_file(file.filename):
        logger.warning(f"[搜索校验] 文件格式无效: {file.filename}")
        return {"code": 400, "message": "仅支持 JSON 或 TXT 格式文件"}

    logger.info(f"[搜索校验] 步骤1: 文件格式验证通过")

    # 2. 读取文件
    content = await file.read()
    logger.info(f"[搜索校验] 步骤2: 文件读取完成, 大小: {len(content)} bytes")

    if len(content) > settings.MAX_FILE_SIZE:
        return {"code": 400, "message": "文件大小超过限制"}

    # 3. 解析 JSON
    try:
        data = json.loads(content)
        logger.info(f"[搜索校验] 步骤3: JSON解析成功")
    except json.JSONDecodeError as e:
        logger.error(f"[搜索校验] JSON解析失败: {e}")
        return {"code": 400, "message": f"JSON 解析失败：{str(e)}"}

    # 4. 验证数据结构
    if not ParserService.validate_json_structure(data):
        logger.error(f"[搜索校验] 数据结构验证失败")
        return {"code": 400, "message": "书源数据格式不正确"}

    logger.info(f"[搜索校验] 步骤4: 数据结构验证通过")

    # 5. 提取书源
    sources = ParserService.extract_sources(data)
    logger.info(f"[搜索校验] 步骤5: 提取书源完成, 数量: {len(sources)}")

    # 6. 创建会话
    session_id = await session_manager.create_session(
        sources,
        options.concurrency,
        options.timeout,
        options.mode,
        options.smart_enabled,
        options.max_retries,
    )
    logger.info(
        "搜索校验会话创建: session_id=%s total=%s keyword=%s type=%s "
        "concurrency=%s timeout=%s",
        session_id,
        len(sources),
        keyword,
        validate_type,
        options.concurrency,
        options.timeout,
    )
    logger.info(f"[搜索校验] 步骤6: 会话创建成功, sessionId: {session_id}")

    # 保存搜索校验参数（直接访问 _sessions，避免死锁）
    async with session_manager._lock:
        session = session_manager._sessions.get(session_id)
        if session:
            session.search_keyword = keyword
            session.validate_type = validate_type
            session.total_original = len(sources)

    logger.info(f"[搜索校验] 步骤7: 返回响应, sessionId: {session_id}")

    return {
        "code": 200,
        "sessionId": session_id,
        "total": len(sources),
        "keyword": keyword,
        "validateType": validate_type,
        "validationMode": options.mode,
        "smartEnabled": options.smart_enabled,
        "message": "会话创建成功"
    }


@router.post("/validate/search/start-data")
async def start_search_validation_from_data(request: dict):
    """开始搜索校验（SSE模式）- 从失败书源数据重试。"""
    sources = request.get("sources", [])
    keyword = request.get("keyword", "玄幻")
    validate_type = request.get("validate_type", "search")
    concurrency = request.get("concurrency", 16)
    timeout = request.get("timeout", 30)
    validation_mode = request.get("validation_mode", "custom")
    smart_enabled = request.get("smart_enabled", True)

    try:
        options = validate_runtime_options(concurrency, timeout, validation_mode, smart_enabled)
    except ValueError as exc:
        return {"code": 400, "message": str(exc)}

    if not sources:
        return {"code": 400, "message": "书源数据为空"}

    session_id = await session_manager.create_session(
        sources,
        options.concurrency,
        options.timeout,
        options.mode,
        options.smart_enabled,
        options.max_retries,
    )

    async with session_manager._lock:
        session = session_manager._sessions.get(session_id)
        if session:
            session.search_keyword = keyword
            session.validate_type = validate_type
            session.total_original = len(sources)

    logger.info(
        "搜索校验数据会话创建: session_id=%s total=%s keyword=%s type=%s "
        "concurrency=%s timeout=%s",
        session_id,
        len(sources),
        keyword,
        validate_type,
        options.concurrency,
        options.timeout,
    )

    return {
        "code": 200,
        "sessionId": session_id,
        "total": len(sources),
        "keyword": keyword,
        "validateType": validate_type,
        "validationMode": options.mode,
        "smartEnabled": options.smart_enabled,
        "message": "会话创建成功",
    }


@router.get("/validate/search/progress/{session_id}")
async def get_search_validation_progress(session_id: str):
    """
    SSE 搜索校验进度推送
    """
    logger.info(f"SSE端点被调用: session_id={session_id}")

    async def event_generator():
        logger.info(f"event_generator 开始执行")
        session = await session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        logger.info(f"搜索校验开始: session_id={session_id}, total={session.total}")

        # 标记运行中
        async with session_manager._lock:
            session.status = "running"

        # 启动校验任务
        async def run_validation():
            started_at = time.perf_counter()
            try:
                logger.info(f"启动校验任务: validate_type={getattr(session, 'validate_type', 'search')}, keyword={getattr(session, 'search_keyword', '玄幻')}")
                valid_sources = []
                failed_sources = {}
                total = len(session.sources)
                processed = 0
                lock = asyncio.Lock()
                semaphore = asyncio.Semaphore(session.concurrency)
                options = ValidationOptions(
                    concurrency=session.concurrency,
                    timeout=session.timeout,
                    mode=session.validation_mode,
                    smart_enabled=session.smart_enabled,
                    max_retries=session.max_retries,
                )

                keyword = getattr(session, 'search_keyword', '玄幻')
                validate_type = getattr(session, 'validate_type', 'search')

                async def validate_single(source):
                    nonlocal processed, valid_sources, failed_sources
                    url = source.get('bookSourceUrl', '')
                    name = source.get('bookSourceName', '')

                    # 检查是否已取消（直接读取 session 状态，不加锁）
                    if session.status == "cancelled":
                        return
                    while session.status == "paused":
                        await asyncio.sleep(0.3)

                    async with semaphore:
                        # 再次检查取消状态（直接读取，不加锁）
                        if session.status == "cancelled":
                            return
                        while session.status == "paused":
                            await asyncio.sleep(0.3)

                        # 组合模式：分别校验搜索和发现
                        if validate_type == 'both':
                            has_search = SearchValidatorService.has_search_rule(source)
                            has_explore = SearchValidatorService.has_explore_rule(source)

                            # 没有任何规则，跳过
                            if not has_search and not has_explore:
                                async with lock:
                                    processed += 1
                                    if "无规则" not in failed_sources:
                                        failed_sources["无规则"] = []
                                    # 保存完整书源信息
                                    failed_source = source.copy()
                                    failed_source['_failureReason'] = '无规则'
                                    failed_source['_ruleType'] = '无规则'
                                    failed_sources["无规则"].append(failed_source)
                                    total_failed = sum(len(v) for v in failed_sources.values())
                                    # 直接更新 session 进度（不加锁）
                                    session.processed = processed
                                    session.valid = len(valid_sources)
                                    session.invalid = total_failed
                                    session.current_url = url
                                    session.current_name = name
                                    session.valid_sources = valid_sources
                                    session.failed_sources = failed_sources
                                return

                            search_valid = False
                            search_reason = ""
                            explore_valid = False
                            explore_reason = ""

                            # 校验搜索
                            if has_search:
                                search_valid, search_reason, _ = await SearchValidatorService.validate_search(
                                    source,
                                    keyword,
                                    session.current_timeout,
                                    max_retries=options.max_retries,
                                )

                            # 校验发现
                            if has_explore:
                                explore_valid, explore_reason, _ = await SearchValidatorService.validate_explore(
                                    source,
                                    session.current_timeout,
                                    max_retries=options.max_retries,
                                )

                            async with lock:
                                processed += 1

                                # 至少一个有效就算通过
                                if search_valid or explore_valid:
                                    # 添加规则类型标记
                                    source_with_type = source.copy()
                                    if has_search and has_explore:
                                        source_with_type['_ruleType'] = '搜索+发现'
                                    elif has_search:
                                        source_with_type['_ruleType'] = '仅搜索'
                                    elif has_explore:
                                        source_with_type['_ruleType'] = '仅发现'
                                    valid_sources.append(source_with_type)
                                else:
                                    # 记录失败原因
                                    reasons = []
                                    if has_search and not search_valid:
                                        reasons.append(f"搜索:{search_reason if search_reason else '未知错误'}")
                                    if has_explore and not explore_valid:
                                        reasons.append(f"发现:{explore_reason if explore_reason else '未知错误'}")
                                    reason_str = "; ".join(reasons) if reasons else "校验失败"

                                    if reason_str not in failed_sources:
                                        failed_sources[reason_str] = []
                                    # 保存完整书源信息
                                    failed_source = source.copy()
                                    failed_source['_failureReason'] = reason_str
                                    failed_source['_ruleType'] = '仅搜索' if has_search and not has_explore else ('仅发现' if has_explore and not has_search else '搜索+发现')
                                    failed_sources[reason_str].append(failed_source)

                                total_failed = sum(len(v) for v in failed_sources.values())
                                # 直接更新 session 进度（不加锁）
                                session.processed = processed
                                session.valid = len(valid_sources)
                                session.invalid = total_failed
                                session.current_url = url
                                session.current_name = name
                                session.valid_sources = valid_sources
                                session.failed_sources = failed_sources

                        # 单一模式：仅搜索或仅发现
                        elif validate_type == 'search':
                            # 先检查是否有搜索规则
                            if not SearchValidatorService.has_search_rule(source):
                                async with lock:
                                    processed += 1
                                    if "无搜索规则" not in failed_sources:
                                        failed_sources["无搜索规则"] = []
                                    # 保存完整书源信息
                                    failed_source = source.copy()
                                    failed_source['_failureReason'] = '无搜索规则'
                                    failed_source['_ruleType'] = '仅发现'
                                    failed_sources["无搜索规则"].append(failed_source)
                                    total_failed = sum(len(v) for v in failed_sources.values())
                                    # 直接更新 session 进度（不加锁）
                                    session.processed = processed
                                    session.valid = len(valid_sources)
                                    session.invalid = total_failed
                                    session.current_url = url
                                    session.current_name = name
                                    session.valid_sources = valid_sources
                                    session.failed_sources = failed_sources
                                return

                            is_valid, reason, results = await SearchValidatorService.validate_search(
                                source,
                                keyword,
                                session.current_timeout,
                                max_retries=options.max_retries,
                            )

                            async with lock:
                                processed += 1
                                if is_valid:
                                    valid_sources.append(source)
                                else:
                                    if reason not in failed_sources:
                                        failed_sources[reason] = []
                                    # 保存完整书源信息
                                    failed_source = source.copy()
                                    failed_source['_failureReason'] = reason
                                    failed_source['_ruleType'] = '仅搜索'
                                    failed_sources[reason].append(failed_source)

                                total_failed = sum(len(v) for v in failed_sources.values())
                                # 直接更新 session 进度（不加锁）
                                session.processed = processed
                                session.valid = len(valid_sources)
                                session.invalid = total_failed
                                session.current_url = url
                                session.current_name = name
                                session.valid_sources = valid_sources
                                session.failed_sources = failed_sources

                        else:  # explore
                            # 先检查是否有发现规则
                            if not SearchValidatorService.has_explore_rule(source):
                                async with lock:
                                    processed += 1
                                    if "无发现规则" not in failed_sources:
                                        failed_sources["无发现规则"] = []
                                    # 保存完整书源信息
                                    failed_source = source.copy()
                                    failed_source['_failureReason'] = '无发现规则'
                                    failed_source['_ruleType'] = '仅搜索'
                                    failed_sources["无发现规则"].append(failed_source)
                                    total_failed = sum(len(v) for v in failed_sources.values())
                                    # 直接更新 session 进度（不加锁）
                                    session.processed = processed
                                    session.valid = len(valid_sources)
                                    session.invalid = total_failed
                                    session.current_url = url
                                    session.current_name = name
                                    session.valid_sources = valid_sources
                                    session.failed_sources = failed_sources
                                return

                            is_valid, reason, results = await SearchValidatorService.validate_explore(
                                source,
                                session.current_timeout,
                                max_retries=options.max_retries,
                            )

                            async with lock:
                                processed += 1
                                if is_valid:
                                    valid_sources.append(source)
                                else:
                                    if reason not in failed_sources:
                                        failed_sources[reason] = []
                                    # 保存完整书源信息
                                    failed_source = source.copy()
                                    failed_source['_failureReason'] = reason
                                    failed_source['_ruleType'] = '仅发现'
                                    failed_sources[reason].append(failed_source)

                                total_failed = sum(len(v) for v in failed_sources.values())
                                # 直接更新 session 进度（不加锁）
                                session.processed = processed
                                session.valid = len(valid_sources)
                                session.invalid = total_failed
                                session.current_url = url
                                session.current_name = name
                                session.valid_sources = valid_sources
                                session.failed_sources = failed_sources

                # 并发执行
                logger.info(f"开始并发校验 {len(session.sources)} 个书源")
                validation_tasks = [asyncio.create_task(validate_single(s)) for s in session.sources]
                # 保存任务到 session，用于取消（直接访问，不加锁）
                session.validation_tasks = validation_tasks
                await asyncio.gather(*validation_tasks, return_exceptions=True)

                # 只有未取消时才完成会话
                if session.status != "cancelled":
                    await session_manager.complete_session(session_id, valid_sources, failed_sources)
                    elapsed = time.perf_counter() - started_at
                    invalid_count = sum(len(v) for v in failed_sources.values())
                    log_method = logger.warning if elapsed >= SLOW_VALIDATION_SECONDS else logger.info
                    log_method(
                        "搜索校验完成: session_id=%s total=%s valid=%s invalid=%s "
                        "type=%s keyword=%s concurrency=%s timeout=%s duration=%.2fs",
                        session_id,
                        total,
                        len(valid_sources),
                        invalid_count,
                        validate_type,
                        keyword,
                        session.concurrency,
                        session.timeout,
                        elapsed,
                    )

            except asyncio.CancelledError:
                elapsed = time.perf_counter() - started_at
                logger.info("搜索校验任务被取消: session_id=%s duration=%.2fs", session_id, elapsed)

            except Exception:
                logger.exception("搜索校验异常: session_id=%s", session_id)
                session.status = "error"

        # 后台运行校验
        asyncio.create_task(run_validation())

        # 持续推送进度（直接使用 session 引用，不加锁）
        while True:
            # 检查是否完成（直接读取 session.status）
            if session.status in ["completed", "cancelled", "error"]:
                if session.status == "completed":
                    valid_sources = session.valid_sources
                    failed_sources = session.failed_sources

                    failed_groups = build_failed_groups(failed_sources)

                    result_data = {
                        "status": "completed",
                        "processed": session.total,
                        "total": session.total,
                        "valid": len(valid_sources),
                        "invalid": sum(len(v) for v in failed_sources.values()),
                        "validCount": len(valid_sources),
                        "invalidCount": sum(len(v) for v in failed_sources.values()),
                        "validSources": valid_sources,
                        "failedGroups": failed_groups,
                        "failedCategories": categorize_failed_sources(failed_groups),
                        # 规则类型统计
                        "ruleTypeStats": calculate_rule_type_stats(valid_sources, failed_sources),
                        "strategy": {
                            "mode": session.validation_mode,
                            "smartEnabled": session.smart_enabled,
                            "currentConcurrency": session.current_concurrency,
                            "currentTimeout": session.current_timeout,
                        },
                    }
                    yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                elif session.status == "cancelled":
                    valid_sources = session.valid_sources
                    failed_sources = session.failed_sources
                    failed_groups = build_failed_groups(failed_sources)
                    result_data = {
                        "status": "cancelled",
                        "processed": session.processed,
                        "total": session.total,
                        "valid": len(valid_sources),
                        "invalid": sum(len(v) for v in failed_sources.values()),
                        "validCount": len(valid_sources),
                        "invalidCount": sum(len(v) for v in failed_sources.values()),
                        "validSources": valid_sources,
                        "failedGroups": failed_groups,
                        "failedCategories": categorize_failed_sources(failed_groups),
                        "ruleTypeStats": calculate_rule_type_stats(valid_sources, failed_sources),
                        "partial": True,
                    }
                    yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                elif session.status == "error":
                    yield f"data: {json.dumps({'status': 'error', 'error': '校验过程发生错误'})}\n\n"

                # 清理会话
                await session_manager.delete_session(session_id)
                break

            # 发送进度消息
            # 计算已耗时和预估剩余时间
            elapsed = time.time() - session.start_time if session.start_time > 0 else 0
            estimated_remaining = 0
            if session.processed > 0 and session.processed < session.total:
                avg_time = elapsed / session.processed
                estimated_remaining = (session.total - session.processed) * avg_time

            progress_data = {
                "processed": session.processed,
                "total": session.total,
                "valid": session.valid,
                "invalid": session.invalid,
                "current": session.current_url,
                "currentName": session.current_name,
                "elapsed": round(elapsed, 1),
                "estimatedRemaining": round(estimated_remaining, 1),
                "status": session.status,
                "strategy": {
                    "mode": session.validation_mode,
                    "smartEnabled": session.smart_enabled,
                    "currentConcurrency": session.current_concurrency,
                    "currentTimeout": session.current_timeout,
                },
            }

            yield f"data: {json.dumps(progress_data)}\n\n"

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
