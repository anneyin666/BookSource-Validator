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
from app.config import settings
from app.services.search_validator import SearchValidatorService
from app.services.session_manager import session_manager
from app.services.validation_scheduler import AdaptiveWorkQueue
from app.services.validation_strategy import (
    AdaptiveValidationController,
    ValidationOptions,
    get_retry_delay,
    is_retryable_reason,
    is_timeout_reason,
)

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
                keyword = getattr(session, 'search_keyword', '玄幻')
                validate_type = getattr(session, 'validate_type', 'search')

                valid_sources = []
                failed_sources = {}
                processed = 0
                running_tasks = set()

                def record_failure(reason, source, url, name, rule_type):
                    if reason not in failed_sources:
                        failed_sources[reason] = []
                    failed_source = source.copy()
                    failed_source.update({
                        'url': url,
                        'name': name,
                        'reason': reason,
                        '_failureReason': reason,
                        '_ruleType': rule_type,
                    })
                    failed_sources[reason].append(failed_source)

                async def validate_single(work_item, request_timeout):
                    source = work_item.source
                    url = source.get('bookSourceUrl', '')
                    name = source.get('bookSourceName', '')
                    started = time.perf_counter()
                    has_search = SearchValidatorService.has_search_rule(source)
                    has_explore = SearchValidatorService.has_explore_rule(source)

                    if validate_type == 'search':
                        if not has_search:
                            return (
                                work_item, url, name, False,
                                '无搜索规则',
                                time.perf_counter() - started, '仅搜索',
                            )
                        is_valid, reason, _ = await SearchValidatorService.validate_search(
                            source, keyword, request_timeout, max_retries=0
                        )
                        rule_type = '仅搜索'
                    elif validate_type == 'explore':
                        if not has_explore:
                            return (
                                work_item, url, name, False,
                                '无发现规则',
                                time.perf_counter() - started, '仅发现',
                            )
                        is_valid, reason, _ = await SearchValidatorService.validate_explore(
                            source, request_timeout, max_retries=0
                        )
                        rule_type = '仅发现'
                    else:
                        if not has_search and not has_explore:
                            return (
                                work_item, url, name, False,
                                '无规则',
                                time.perf_counter() - started, '无规则',
                            )
                        search_valid = False
                        search_reason = ''
                        explore_valid = False
                        explore_reason = ''
                        if has_search:
                            search_valid, search_reason, _ = await SearchValidatorService.validate_search(
                                source, keyword, request_timeout, max_retries=0
                            )
                        if has_explore:
                            explore_valid, explore_reason, _ = await SearchValidatorService.validate_explore(
                                source, request_timeout, max_retries=0
                            )
                        is_valid = search_valid or explore_valid
                        if is_valid:
                            reason = ''
                        else:
                            reasons = []
                            if has_search and not search_valid:
                                reasons.append('搜索:%s' % (search_reason or '未知错误'))
                            if has_explore and not explore_valid:
                                reasons.append('发现:%s' % (explore_reason or '未知错误'))
                            reason = '; '.join(reasons) if reasons else '校验失败'
                        rule_type = (
                            '搜索+发现' if has_search and has_explore
                            else ('仅搜索' if has_search else '仅发现')
                        )

                    return (
                        work_item, url, name, is_valid, reason,
                        time.perf_counter() - started, rule_type,
                    )

                def process_completed_tasks(done_tasks):
                    nonlocal processed
                    for task in done_tasks:
                        if task.cancelled():
                            continue
                        exc = task.exception()
                        if exc:
                            logger.warning(
                                '单个搜索校验异常: session_id=%s error=%s',
                                session_id,
                                exc,
                            )
                            continue

                        (
                            work_item, url, name, is_valid, reason,
                            duration, rule_type,
                        ) = task.result()

                        if work_item.attempt == 0:
                            adjustment = controller.record(
                                duration,
                                is_valid,
                                reason,
                            )
                            if adjustment is not None:
                                logger.info(
                                    '搜索校验智能策略: session_id=%s phase=%s '
                                    'samples=%s network_error_rate=%.3f timeout_rate=%.3f '
                                    'p75=%.2f concurrency=%s->%s timeout=%s->%s reason=%s',
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
                            if not is_valid and is_retryable_reason(reason):
                                session.primary_network_failures += 1

                        # 超时占比很高的批次（多为死源）不再重试超时
                        retryable = is_retryable_reason(reason)
                        if (
                            retryable
                            and is_timeout_reason(reason)
                            and not controller.should_retry_timeout()
                        ):
                            retryable = False

                        scheduled_retry = False
                        if not is_valid and retryable:
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
                                # 记录规则类型用于统计（结果接口返回前会剥离内部字段）
                                source_with_type = work_item.source.copy()
                                source_with_type['_ruleType'] = rule_type
                                valid_sources.append(source_with_type)
                            else:
                                record_failure(
                                    reason,
                                    work_item.source,
                                    url,
                                    name,
                                    rule_type,
                                )

                        snapshot = controller.snapshot()
                        session.current_concurrency = snapshot['currentConcurrency']
                        session.current_timeout = snapshot['currentTimeout']
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

                while work_queue.has_work or running_tasks:
                    if session.status == 'cancelled':
                        completed_tasks = {
                            task for task in running_tasks if task.done()
                        }
                        for task in running_tasks - completed_tasks:
                            task.cancel()
                        process_completed_tasks(completed_tasks)
                        break

                    if session.status == 'paused':
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

                    work_queue.advance_phase(active_count=len(running_tasks))
                    session.validation_phase = work_queue.phase
                    active_limit = controller.current_concurrency
                    if work_queue.phase == 'retry':
                        active_limit = min(
                            active_limit,
                            controller.min_concurrency,
                        )

                    capacity = max(0, active_limit - len(running_tasks))
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
                                controller.current_timeout,
                            )
                        )
                        running_tasks.add(task)

                    session.validation_tasks = list(running_tasks)
                    if not running_tasks:
                        delay = work_queue.next_delay(now=time.monotonic())
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

                if session.status != 'cancelled':
                    await session_manager.complete_session(
                        session_id,
                        valid_sources,
                        failed_sources,
                    )
                    elapsed = time.perf_counter() - started_at
                    invalid_count = sum(len(v) for v in failed_sources.values())
                    log_method = (
                        logger.warning
                        if elapsed >= SLOW_VALIDATION_SECONDS
                        else logger.info
                    )
                    log_method(
                        '搜索校验完成: session_id=%s total=%s valid=%s invalid=%s '
                        'type=%s keyword=%s concurrency=%s timeout=%s duration=%.2fs '
                        'final_concurrency=%s final_timeout=%s retries=%s',
                        session_id,
                        len(session.sources),
                        len(valid_sources),
                        invalid_count,
                        validate_type,
                        keyword,
                        session.concurrency,
                        session.timeout,
                        elapsed,
                        session.current_concurrency,
                        session.current_timeout,
                        session.retry_attempts,
                    )

            except asyncio.CancelledError:
                elapsed = time.perf_counter() - started_at
                logger.info(
                    '搜索校验任务被取消: session_id=%s duration=%.2fs',
                    session_id,
                    elapsed,
                )

            except Exception:
                logger.exception('搜索校验异常: session_id=%s', session_id)
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
                "strategy": build_strategy_payload(session),
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
