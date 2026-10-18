# 搜索校验路由
"""搜索/发现规则校验（SSE）路由。"""
import asyncio
import json
import logging
import time

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.api.helpers import build_strategy_payload, validate_runtime_options
from app.api.ingest import load_sources_from_upload
from app.services.search_validator import SearchValidatorService
from app.services.session_manager import session_manager
from app.services.validation_strategy import ValidationOptions

router = APIRouter()
logger = logging.getLogger(__name__)
SLOW_VALIDATION_SECONDS = 5 * 60


# ===================== 搜索校验接口 =====================



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

    # 1. 读取并解析文件
    sources, error_message = await load_sources_from_upload(file)
    if error_message:
        logger.warning("[搜索校验] 文件读取失败: %s", error_message)
        return {"code": 400, "message": error_message}

    logger.info("[搜索校验] 文件解析完成, 书源数量: %s", len(sources))

    # 2. 创建会话
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
            session.is_search = True
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
            session.is_search = True
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

        # 告知浏览器断线后 2 秒内重连，提升移动端弱网恢复速度
        yield "retry: 2000\n\n"

        logger.info(f"搜索校验开始: session_id={session_id}, total={session.total}")

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
                await session_manager.fail_session(session_id)

        # 校验任务独立于 SSE 连接；重连只订阅已有任务。
        await session_manager.ensure_runner(session_id, run_validation)

        # 持续推送进度（直接使用 session 引用，不加锁）
        while True:
            # 检查是否完成（直接读取 session.status）
            if session.status in ["completed", "cancelled", "error"]:
                if session.status == "completed":
                    valid_sources = session.valid_sources
                    failed_sources = session.failed_sources

                    # 只发送统计信息，完整结果（含规则类型分布）由结果接口拉取
                    result_data = {
                        "status": "completed",
                        "processed": session.total,
                        "total": session.total,
                        "valid": len(valid_sources),
                        "invalid": sum(len(v) for v in failed_sources.values()),
                        "validCount": len(valid_sources),
                        "invalidCount": sum(len(v) for v in failed_sources.values()),
                        "resultReady": True,
                        "resultUrl": f"/api/validate/result/{session_id}",
                        "strategy": build_strategy_payload(session),
                    }
                    yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                elif session.status == "cancelled":
                    valid_sources = session.valid_sources
                    failed_sources = session.failed_sources
                    result_data = {
                        "status": "cancelled",
                        "processed": session.processed,
                        "total": session.total,
                        "valid": len(valid_sources),
                        "invalid": sum(len(v) for v in failed_sources.values()),
                        "validCount": len(valid_sources),
                        "invalidCount": sum(len(v) for v in failed_sources.values()),
                        "partial": True,
                        "resultReady": True,
                        "resultUrl": f"/api/validate/result/{session_id}",
                        "strategy": build_strategy_payload(session),
                    }
                    yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                elif session.status == "error":
                    yield f"data: {json.dumps({'status': 'error', 'error': '校验过程发生错误'})}\n\n"

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
