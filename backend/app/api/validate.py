# 深度校验路由
"""深度校验（SSE）与会话控制路由。"""
import asyncio
import json
import logging
import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.helpers import (
    append_failed_source,
    build_session_result,
    build_strategy_payload,
    validate_runtime_options,
)
from app.api.ingest import load_sources_from_upload
from app.config import settings
from app.services import DeduperService, FilterService, ValidatorService
from app.services.session_manager import session_manager
from app.services.validation_scheduler import AdaptiveWorkQueue
from app.services.validation_strategy import (
    AdaptiveValidationController,
    ValidationOptions,
    get_retry_delay,
    is_retryable_reason,
)

router = APIRouter()
logger = logging.getLogger(__name__)
SLOW_VALIDATION_SECONDS = 5 * 60


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

    # 1. 读取并解析文件
    sources, error_message = await load_sources_from_upload(file)
    if error_message:
        return {"code": 400, "message": error_message}

    # 2. 解析过滤类型
    filter_list = [f.strip() for f in filter_types.split(',') if f.strip()] if filter_types else []

    # 3. 处理书源（去重 + 格式校验 + 类型过滤）
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

        # 告知浏览器断线后 2 秒内重连，提升移动端弱网恢复速度
        yield "retry: 2000\n\n"

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

                    # 设置分组（结果接口返回的数据已带分组）
                    ValidatorService.set_source_group(valid_sources, len(valid_sources))

                    # 只发送统计信息：完整结果由 /api/validate/result/{session_id} 单独拉取，
                    # 避免弱网/低带宽下单条 SSE 消息携带数 MB 数据被代理或移动网络掐断。
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
                    logger.info(
                        "SSE完成消息: validCount=%s invalidCount=%s result_url=%s",
                        result_data["validCount"],
                        result_data["invalidCount"],
                        result_data["resultUrl"],
                    )
                    yield f"data: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                elif session.status == "cancelled":
                    valid_sources = session.valid_sources
                    failed_sources = session.failed_sources
                    ValidatorService.set_source_group(valid_sources, len(valid_sources))
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


@router.get("/validate/result/{session_id}")
async def get_validation_result(session_id: str):
    """获取校验完整结果。

    弱网/低带宽环境下，SSE 完成消息只携带统计数字，
    前端收到完成消息后再通过此接口拉取书源明细（支持 gzip 压缩与重试）。
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    if session.status not in ("completed", "cancelled"):
        return {"code": 409, "message": "校验尚未完成"}

    return {"code": 200, "data": build_session_result(session)}


