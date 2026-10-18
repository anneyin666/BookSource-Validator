# 书源解析路由
"""书源解析相关路由：单文件/单链接解析、批量解析与批量校验启动。"""
import json
import logging
import time
from typing import List, Optional

import httpx
from fastapi import APIRouter, File, Form, UploadFile

from app.api.helpers import (
    build_empty_source_data,
    validate_runtime_options,
)
from app.api.ingest import (
    collect_sources_from_files,
    collect_sources_from_urls,
    load_sources_from_upload,
)
from app.config import settings
from app.models import ParseResponse, SourceData, UrlParseRequest
from app.services import DeduperService, FilterService, ParserService, ValidatorService
from app.services.session_manager import session_manager
from app.services.url_security import UrlSecurityService
from app.services.validation_strategy import ValidationOptions

router = APIRouter()
logger = logging.getLogger(__name__)
SLOW_VALIDATION_SECONDS = 5 * 60


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

    # 1. 读取并解析文件
    sources, error_message = await load_sources_from_upload(file)
    if error_message:
        return ParseResponse(code=400, message=error_message)

    # 2. 解析过滤类型
    filter_list = [f.strip() for f in filter_types.split(',') if f.strip()] if filter_types else []

    # 3. 处理书源
    result = await process_sources(sources, mode, options, filter_list)
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

    is_safe, error_message = await UrlSecurityService.is_safe_remote_url(request.url)
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

    # 3. 验证数据结构并提取书源
    if not ParserService.validate_json_structure(data):
        return ParseResponse(code=400, message="书源数据格式不正确")
    sources = ParserService.extract_sources(data)

    # 4. 解析过滤类型
    filter_list = request.filter_types.split(',') if request.filter_types else []

    # 5. 处理书源
    result = await process_sources(sources, request.mode, options, filter_list)
    return ParseResponse(data=result)


async def process_sources(
    sources: List[dict],
    mode: str = "dedup",
    options: Optional[ValidationOptions] = None,
    filter_types: list = None,
) -> SourceData:
    """
    处理书源数据

    Args:
        sources: 已提取的书源列表
        mode: 操作模式
        options: 归一化后的校验参数
        filter_types: 过滤类型列表

    Returns:
        处理结果
    """
    if filter_types is None:
        filter_types = []
    if options is None:
        options = validate_runtime_options(16, 30)
    started_at = time.perf_counter()

    total = len(sources)
    logger.info(f"处理书源数量: {total}")

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

    all_sources, file_stats = await collect_sources_from_files(files)

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

    all_sources, url_stats = await collect_sources_from_urls(urls)

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

    all_sources, file_stats = await collect_sources_from_files(files)

    if not all_sources:
        return ParseResponse(
            code=400,
            message="没有有效的书源数据",
            data=build_empty_source_data(file_stats=file_stats)
        )

    # 解析过滤类型
    filter_list = [f.strip() for f in filter_types.split(',') if f.strip()] if filter_types else []

    # 处理合并后的书源
    result = await process_sources(all_sources, mode, options, filter_list)

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

    all_sources, url_stats = await collect_sources_from_urls(urls)

    if not all_sources:
        return ParseResponse(
            code=400,
            message="没有有效的书源数据",
            data=build_empty_source_data(url_stats=url_stats)
        )

    # 解析过滤类型
    filter_list = filter_types.split(',') if filter_types else []

    # 处理合并后的书源
    result = await process_sources(all_sources, mode, options, filter_list)

    # 添加URL统计信息
    result.urlStats = url_stats

    return ParseResponse(data=result)


