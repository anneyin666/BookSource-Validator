# Adaptive Validation Throughput Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让深度校验的均衡智能模式在健康批次中保持接近固定 16 并发的吞吐，并通过窗口式调节和延后重试避免异常样本将并发快速压到 1。

**Architecture:** `validation_strategy.py` 只负责基于首轮样本计算并发和超时调整；新增 `validation_scheduler.py` 管理首轮队列、延后重试队列和阶段切换；`sources.py` 将二者接入现有 SSE 会话。网络请求任务只执行一次 HTTP 校验，退避等待保存在调度队列中，不占用活动请求槽。

**Tech Stack:** Python 3.10+、asyncio、FastAPI、httpx、pytest、pytest-asyncio、Vue 3、Element Plus

---

## 文件结构

- Create: `backend/tests/test_validation_strategy.py` - 自适应控制器行为测试。
- Create: `backend/tests/test_validation_scheduler.py` - 首轮优先和延后重试队列测试。
- Create: `backend/app/services/validation_scheduler.py` - 与 HTTP 实现解耦的工作队列状态机。
- Modify: `backend/app/services/validation_strategy.py` - 窗口评估、渐进降并发、超时上限和调整快照。
- Modify: `backend/app/services/session_manager.py` - 保存阶段、首轮网络失败数和实际重试数。
- Modify: `backend/app/api/sources.py` - 深度校验 SSE 接入新控制器和工作队列。
- Modify: `frontend/src/components/ValidationProgress.vue` - 展示首轮校验或网络重试阶段。
- Modify: `docs/FUTURE_SUGGESTIONS.md` - 记录吞吐优化落地情况。
- Create: `docs/sessions/SESSION_16_ADAPTIVE_THROUGHPUT_OPTIMIZATION.md` - 本轮会话总结。

### Task 1: 为窗口式自适应控制器建立失败测试

**Files:**
- Create: `backend/tests/test_validation_strategy.py`
- Test: `backend/tests/test_validation_strategy.py`

- [ ] **Step 1: 创建测试目录和策略测试文件**

在 `backend/tests/test_validation_strategy.py` 写入：

```python
"""Tests for adaptive validation throughput decisions."""

from app.services.validation_strategy import (
    AdaptiveValidationController,
    ValidationOptions,
)


def build_controller(*, smart_enabled: bool = True) -> AdaptiveValidationController:
    """Create a balanced controller for deterministic tests."""
    return AdaptiveValidationController(
        ValidationOptions(
            concurrency=16,
            timeout=30,
            mode="balanced",
            smart_enabled=smart_enabled,
            max_retries=2,
        )
    )


def record_window(
    controller: AdaptiveValidationController,
    *,
    count: int,
    duration: float,
    is_valid: bool,
    reason: str,
):
    """Record a deterministic group and return emitted adjustments."""
    return [
        adjustment
        for _ in range(count)
        if (
            adjustment := controller.record(
                duration=duration,
                is_valid=is_valid,
                reason=reason,
            )
        ) is not None
    ]


def test_fast_http_failures_do_not_reduce_concurrency():
    controller = build_controller()

    adjustments = record_window(
        controller,
        count=32,
        duration=0.2,
        is_valid=False,
        reason="HTTP 404",
    )

    assert controller.current_concurrency == 16
    assert all(item.current_concurrency == 16 for item in adjustments)


def test_controller_waits_for_full_evaluation_interval():
    controller = build_controller()

    adjustments = record_window(
        controller,
        count=15,
        duration=29,
        is_valid=False,
        reason="超时",
    )

    assert adjustments == []
    assert controller.current_concurrency == 16


def test_first_unhealthy_window_reduces_only_once():
    controller = build_controller()

    adjustments = record_window(
        controller,
        count=16,
        duration=29,
        is_valid=False,
        reason="超时",
    )

    assert len(adjustments) == 1
    assert controller.current_concurrency == 12
    assert adjustments[0].previous_concurrency == 16
    assert adjustments[0].current_concurrency == 12


def test_balanced_mode_never_drops_below_eight():
    controller = build_controller()

    record_window(
        controller,
        count=64,
        duration=29,
        is_valid=False,
        reason="超时",
    )

    assert controller.current_concurrency == 8


def test_healthy_windows_restore_two_concurrency_at_a_time():
    controller = build_controller()
    record_window(
        controller,
        count=32,
        duration=29,
        is_valid=False,
        reason="超时",
    )
    assert controller.current_concurrency == 9

    adjustments = record_window(
        controller,
        count=16,
        duration=1,
        is_valid=True,
        reason="",
    )

    assert len(adjustments) == 1
    assert controller.current_concurrency == 11


def test_timeout_is_capped_at_base_timeout_plus_ten():
    controller = build_controller()

    record_window(
        controller,
        count=96,
        duration=39,
        is_valid=False,
        reason="超时",
    )

    assert controller.current_timeout == 40


def test_disabled_smart_mode_never_changes_runtime_options():
    controller = build_controller(smart_enabled=False)

    adjustments = record_window(
        controller,
        count=64,
        duration=60,
        is_valid=False,
        reason="超时",
    )

    assert adjustments == []
    assert controller.current_concurrency == 16
    assert controller.current_timeout == 30
```

- [ ] **Step 2: 运行策略测试并确认按预期失败**

Run:

```powershell
cd backend
$env:DEBUG='false'
pytest tests/test_validation_strategy.py -v
```

Expected: FAIL。现有 `record()` 不返回调整对象，并且异常样本会在每个结果后连续降到 1。

- [ ] **Step 3: 提交失败测试**

```powershell
git add backend/tests/test_validation_strategy.py
git commit -m "test: cover adaptive validation throughput rules"
```

### Task 2: 实现窗口式并发和超时控制

**Files:**
- Modify: `backend/app/services/validation_strategy.py`
- Test: `backend/tests/test_validation_strategy.py`

- [ ] **Step 1: 增加策略常量、调整数据类和错误分类函数**

在 `validation_strategy.py` 增加：

```python
import math
from dataclasses import dataclass


SAMPLE_WINDOW_SIZE = 32
EVALUATION_INTERVAL = 16
MIN_CONCURRENCY_RATIO = 0.5
MAX_TIMEOUT_INCREASE = 10

TIMEOUT_REASONS = {
    "超时",
    "连接超时",
    "读取超时",
    "写入超时",
}


@dataclass(frozen=True)
class StrategyAdjustment:
    """One window-based strategy evaluation result."""

    reason: str
    sample_count: int
    network_error_rate: float
    timeout_rate: float
    p75_duration: float
    previous_concurrency: int
    current_concurrency: int
    previous_timeout: int
    current_timeout: int


def is_timeout_reason(reason: str) -> bool:
    """Return whether a failure is timeout-related."""
    return any(keyword in (reason or "") for keyword in TIMEOUT_REASONS)
```

- [ ] **Step 2: 将控制器改为每 16 个首轮样本评估一次**

控制器初始化和 `record()` 使用以下结构：

```python
self.samples: Deque[ValidationSample] = deque(maxlen=SAMPLE_WINDOW_SIZE)
self.evaluation_samples: list[ValidationSample] = []
self.min_concurrency = max(
    MIN_CONCURRENCY,
    math.ceil(self.max_concurrency * MIN_CONCURRENCY_RATIO),
)
self.max_timeout = min(MAX_TIMEOUT, self.base_timeout + MAX_TIMEOUT_INCREASE)


def record(
    self,
    duration: float,
    is_valid: bool,
    reason: str,
) -> StrategyAdjustment | None:
    """Record a first-pass sample and evaluate at fixed intervals."""
    if not self.options.smart_enabled:
        return None
    sample = ValidationSample(duration, is_valid, reason)
    self.samples.append(sample)
    self.evaluation_samples.append(sample)
    if len(self.evaluation_samples) < EVALUATION_INTERVAL:
        return None

    evaluation_samples = self.evaluation_samples
    self.evaluation_samples = []
    return self._evaluate_window(evaluation_samples)
```

- [ ] **Step 3: 实现单窗口最多一次的渐进调整**

`_evaluate_window(samples)` 只使用本次新增的 16 个独立样本计算排序后的 P75；`self.samples` 中保留的 32 条历史只用于日志和观测，不参与重复决策。核心规则：

```python
samples = list(self.samples)
network_failures = [
    sample
    for sample in samples
    if not sample.is_valid and is_retryable_reason(sample.reason)
]
timeout_failures = [
    sample
    for sample in samples
    if not sample.is_valid and is_timeout_reason(sample.reason)
]
durations = sorted(sample.duration for sample in samples)
p75_index = max(0, math.ceil(len(durations) * 0.75) - 1)
p75_duration = durations[p75_index]
network_error_rate = len(network_failures) / len(samples)
timeout_rate = len(timeout_failures) / len(samples)

should_reduce = (
    network_error_rate >= 0.35
    or timeout_rate >= 0.25
    or (
        network_error_rate > 0
        and p75_duration >= self.current_timeout * 0.8
    )
)
is_healthy = (
    network_error_rate <= 0.10
    and timeout_rate <= 0.05
    and p75_duration < self.base_timeout * 0.6
)

if should_reduce:
    self.current_concurrency = max(
        self.min_concurrency,
        math.ceil(self.current_concurrency * 0.75),
    )
elif is_healthy:
    self.current_concurrency = min(
        self.max_concurrency,
        self.current_concurrency + 2,
    )

if timeout_rate >= 0.35:
    self.current_timeout = min(self.max_timeout, self.current_timeout + 5)
elif is_healthy:
    self.current_timeout = max(self.base_timeout, self.current_timeout - 5)
```

返回 `StrategyAdjustment`；若并发和超时都没有变化，仍返回带指标的评估结果，并将 `reason` 设置为 `healthy`、`network_pressure` 或 `unchanged`，方便日志记录。

- [ ] **Step 4: 运行策略测试并确认全部通过**

Run:

```powershell
cd backend
$env:DEBUG='false'
pytest tests/test_validation_strategy.py -v
```

Expected: 7 passed。

- [ ] **Step 5: 提交控制器实现**

```powershell
git add backend/app/services/validation_strategy.py backend/tests/test_validation_strategy.py
git commit -m "perf: stabilize adaptive validation controller"
```

### Task 3: 为首轮优先和延后重试队列建立失败测试

**Files:**
- Create: `backend/tests/test_validation_scheduler.py`
- Create: `backend/app/services/validation_scheduler.py`
- Test: `backend/tests/test_validation_scheduler.py`

- [ ] **Step 1: 编写调度队列失败测试**

在 `backend/tests/test_validation_scheduler.py` 写入：

```python
"""Tests for first-pass priority and deferred retry scheduling."""

from app.services.validation_scheduler import AdaptiveWorkQueue, ValidationWorkItem


def source(index: int) -> dict:
    return {
        "bookSourceName": f"source-{index}",
        "bookSourceUrl": f"https://example.com/{index}",
    }


def test_primary_sources_are_taken_before_retry_items():
    queue = AdaptiveWorkQueue([source(1), source(2)], max_retries=2)
    retry_item = ValidationWorkItem(source=source(9), attempt=0)
    assert queue.schedule_retry(retry_item, "超时", now=0, delay=0)

    first = queue.take_ready(limit=1, now=0)

    assert first[0].source["bookSourceName"] == "source-1"
    assert first[0].attempt == 0
    assert queue.phase == "primary"


def test_retry_phase_waits_until_all_primary_tasks_finish():
    queue = AdaptiveWorkQueue([source(1)], max_retries=2)
    primary = queue.take_ready(limit=1, now=0)[0]
    assert queue.schedule_retry(primary, "超时", now=0, delay=0)

    queue.advance_phase(active_count=1)
    assert queue.take_ready(limit=1, now=0) == []
    assert queue.phase == "primary"

    queue.advance_phase(active_count=0)
    retry = queue.take_ready(limit=1, now=0)
    assert retry[0].attempt == 1
    assert queue.phase == "retry"


def test_retry_backoff_does_not_create_active_work_before_ready_time():
    queue = AdaptiveWorkQueue([], max_retries=2)
    item = ValidationWorkItem(source=source(1), attempt=0)
    assert queue.schedule_retry(item, "连接失败", now=10, delay=2)

    queue.advance_phase(active_count=0)
    assert queue.take_ready(limit=1, now=11.9) == []
    assert queue.next_delay(now=11.9) == 0.1
    assert queue.take_ready(limit=1, now=12)[0].attempt == 1


def test_retry_is_rejected_after_max_retries():
    queue = AdaptiveWorkQueue([], max_retries=2)
    item = ValidationWorkItem(source=source(1), attempt=2)

    assert not queue.schedule_retry(item, "超时", now=0, delay=1)
    assert not queue.has_work
```

- [ ] **Step 2: 运行调度测试并确认导入失败**

Run:

```powershell
cd backend
$env:DEBUG='false'
pytest tests/test_validation_scheduler.py -v
```

Expected: ERROR，`app.services.validation_scheduler` 尚不存在。

- [ ] **Step 3: 实现可测试的工作队列**

创建 `backend/app/services/validation_scheduler.py`：

```python
"""First-pass priority and deferred retry work scheduling."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import heapq
import itertools
from typing import Deque


@dataclass
class ValidationWorkItem:
    """One source validation attempt."""

    source: dict
    attempt: int = 0
    last_reason: str = ""


@dataclass(order=True)
class ScheduledRetry:
    """Retry item ordered by ready time and insertion sequence."""

    ready_at: float
    sequence: int
    item: ValidationWorkItem = field(compare=False)


class AdaptiveWorkQueue:
    """Prioritize all first attempts before consuming deferred retries."""

    def __init__(self, sources: list[dict], max_retries: int):
        self.primary: Deque[ValidationWorkItem] = deque(
            ValidationWorkItem(source=item) for item in sources
        )
        self.retries: list[ScheduledRetry] = []
        self.max_retries = max(0, max_retries)
        self.phase = "primary"
        self._sequence = itertools.count()

    @property
    def has_work(self) -> bool:
        return bool(self.primary or self.retries)

    def advance_phase(self, *, active_count: int) -> None:
        if self.phase == "primary" and not self.primary and active_count == 0:
            self.phase = "retry"

    def schedule_retry(
        self,
        item: ValidationWorkItem,
        reason: str,
        *,
        now: float,
        delay: float,
    ) -> bool:
        if item.attempt >= self.max_retries:
            return False
        retry = ValidationWorkItem(
            source=item.source,
            attempt=item.attempt + 1,
            last_reason=reason,
        )
        heapq.heappush(
            self.retries,
            ScheduledRetry(now + delay, next(self._sequence), retry),
        )
        return True

    def take_ready(
        self,
        *,
        limit: int,
        now: float,
    ) -> list[ValidationWorkItem]:
        items = []
        if self.phase == "primary":
            while self.primary and len(items) < limit:
                items.append(self.primary.popleft())
            return items

        while (
            self.retries
            and self.retries[0].ready_at <= now
            and len(items) < limit
        ):
            items.append(heapq.heappop(self.retries).item)
        return items

    def next_delay(self, *, now: float) -> float | None:
        if not self.retries:
            return None
        return max(0.0, round(self.retries[0].ready_at - now, 3))
```

补充测试，确认重试阶段已有请求运行时仍能填补空槽：

```python
def test_retry_phase_refills_free_slots_while_other_retries_run():
    queue = AdaptiveWorkQueue([], max_retries=2)
    first = ValidationWorkItem(source=source(1), attempt=0)
    second = ValidationWorkItem(source=source(2), attempt=0)
    queue.schedule_retry(first, "超时", now=0, delay=0)
    queue.schedule_retry(second, "超时", now=0, delay=0)
    queue.advance_phase(active_count=0)

    running = queue.take_ready(limit=1, now=0)
    refill = queue.take_ready(limit=1, now=0)

    assert len(running) == 1
    assert len(refill) == 1
```

- [ ] **Step 4: 运行调度测试并确认通过**

Run:

```powershell
cd backend
$env:DEBUG='false'
pytest tests/test_validation_scheduler.py -v
```

Expected: 5 passed。

- [ ] **Step 5: 提交工作队列**

```powershell
git add backend/app/services/validation_scheduler.py backend/tests/test_validation_scheduler.py
git commit -m "feat: add deferred validation retry queue"
```

### Task 4: 将新调度器接入深度校验 SSE

**Files:**
- Modify: `backend/app/api/sources.py`
- Modify: `backend/app/services/session_manager.py`
- Test: `backend/tests/test_validation_scheduler.py`

- [ ] **Step 1: 扩展会话运行指标**

在 `ValidationSession` 增加：

```python
validation_phase: str = "primary"
primary_network_failures: int = 0
retry_attempts: int = 0
```

- [ ] **Step 2: 修改 SSE 单次任务只执行一次请求**

在 `get_validation_progress()` 的运行函数中导入并创建：

```python
from app.services.validation_scheduler import AdaptiveWorkQueue
from app.services.validation_strategy import get_retry_delay, is_retryable_reason

work_queue = AdaptiveWorkQueue(session.sources, options.max_retries)
```

将 `validate_single()` 改为接收工作项，并强制单次请求：

```python
async def validate_single(work_item, client, request_timeout):
    source = work_item.source
    url = ValidatorService.clean_source_url(source.get("bookSourceUrl", ""))
    name = source.get("bookSourceName", "")
    started = time.perf_counter()
    is_valid, reason = await ValidatorService.validate_source_access(
        url,
        request_timeout,
        client=client,
        max_retries=0,
    )
    return (
        work_item,
        url,
        name,
        is_valid,
        reason,
        time.perf_counter() - started,
    )
```

- [ ] **Step 3: 用工作队列替换 `pending_sources.pop(0)` 循环**

每轮根据阶段计算活动上限：

```python
work_queue.advance_phase(active_count=len(running_tasks))
session.validation_phase = work_queue.phase
active_limit = controller.current_concurrency
if work_queue.phase == "retry":
    active_limit = min(active_limit, controller.min_concurrency)

capacity = max(0, active_limit - len(running_tasks))
ready_items = work_queue.take_ready(
    limit=capacity,
    now=time.monotonic(),
)
session.validation_phase = work_queue.phase

for work_item in ready_items:
    if work_item.attempt > 0:
        session.retry_attempts += 1
    task = asyncio.create_task(
        validate_single(work_item, client, controller.current_timeout)
    )
    running_tasks.add(task)
```

当没有活动任务但有等待中的重试时：

```python
delay = work_queue.next_delay(now=time.monotonic())
await asyncio.sleep(min(delay if delay is not None else 0.1, 0.3))
```

- [ ] **Step 4: 将可恢复失败放入延后队列**

处理任务结果时使用：

```python
if work_item.attempt == 0:
    adjustment = controller.record(duration, is_valid, reason)
    if adjustment is not None:
        logger.info(
            "智能策略评估: session_id=%s phase=%s samples=%s "
            "network_error_rate=%.3f timeout_rate=%.3f p75=%.2f "
            "concurrency=%s->%s timeout=%s->%s reason=%s",
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
        delay=get_retry_delay(work_item.attempt, settings.RETRY_DELAY),
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
```

循环条件改为：

```python
while work_queue.has_work or running_tasks:
```

- [ ] **Step 5: 扩展完成日志**

批次完成日志增加：

```python
"final_concurrency=%s final_timeout=%s primary_network_failures=%s retries=%s"
```

参数使用 `session.current_concurrency`、`session.current_timeout`、`session.primary_network_failures` 和 `session.retry_attempts`。

- [ ] **Step 6: 运行后端策略与调度测试**

Run:

```powershell
cd backend
$env:DEBUG='false'
pytest tests/test_validation_strategy.py tests/test_validation_scheduler.py -v
python -m py_compile app/services/validation_strategy.py app/services/validation_scheduler.py app/services/session_manager.py app/api/sources.py app/services/validator.py
```

Expected: 12 passed；`py_compile` exit code 0。

- [ ] **Step 7: 提交 SSE 集成**

```powershell
git add backend/app/api/sources.py backend/app/services/session_manager.py
git commit -m "perf: defer adaptive validation retries"
```

### Task 5: 在 SSE 和前端显示校验阶段

**Files:**
- Modify: `backend/app/api/sources.py`
- Modify: `frontend/src/components/ValidationProgress.vue`

- [ ] **Step 1: 在所有深度校验策略响应中增加阶段**

在运行、完成和取消响应的 `strategy` 对象中增加：

```python
"phase": session.validation_phase,
```

- [ ] **Step 2: 在进度组件中映射阶段文案**

在 `strategyLabel` 计算属性中增加：

```javascript
const phaseMap = {
  primary: '首轮',
  retry: '网络重试'
}
const phase = phaseMap[props.strategy.phase] || ''
const phaseText = phase ? ` · ${phase}` : ''
return `${mode}${phaseText} · ${props.strategy.currentConcurrency || '-'}并发 · ${props.strategy.currentTimeout || '-'}秒`
```

- [ ] **Step 3: 运行前端生产构建**

Run:

```powershell
cd frontend
npm run build
```

Expected: Vite build exit code 0。

- [ ] **Step 4: 提交阶段展示**

```powershell
git add backend/app/api/sources.py frontend/src/components/ValidationProgress.vue
git commit -m "feat: show adaptive validation phase"
```

### Task 6: 文档、回归检查和会话总结

**Files:**
- Modify: `docs/FUTURE_SUGGESTIONS.md`
- Create: `docs/sessions/SESSION_16_ADAPTIVE_THROUGHPUT_OPTIMIZATION.md`

- [ ] **Step 1: 更新优化建议状态**

在智能并发与超时章节记录：

```markdown
- 已将深度校验智能调度改为 16 个首轮样本评估一次，避免连续降并发。
- 已将网络重试移至首轮完成后的延后队列，退避等待不再占用首轮并发槽。
- 均衡模式并发下限为 8，动态超时上限为 40 秒。
```

- [ ] **Step 2: 创建 SESSION 16 总结**

文档包含：会话目标、根因证据、完成任务、技术决策、修改文件、测试结果、服务器复测步骤和后续建议。服务器复测步骤明确使用同一批约 300 个书源，对比总耗时以及日志中的 `final_concurrency`、`final_timeout`、`primary_network_failures`、`retries`。

- [ ] **Step 3: 运行完整后端检查**

Run:

```powershell
cd backend
$env:DEBUG='false'
pytest tests/ -v
python -m py_compile app/services/validation_strategy.py app/services/validation_scheduler.py app/services/session_manager.py app/services/validator.py app/services/search_validator.py app/api/sources.py app/models/request.py
```

Expected: 所有测试通过；`py_compile` exit code 0。

- [ ] **Step 4: 运行前端构建和 Git 差异检查**

Run:

```powershell
cd frontend
npm run build
cd ..
git diff --check
git status --short
```

Expected: 构建 exit code 0；`git diff --check` 无空白错误；状态只包含本轮预期文档改动和用户未跟踪的 `AGENTS.md`。

- [ ] **Step 5: 提交文档**

`docs/sessions/` 被忽略，因此强制添加 SESSION 16：

```powershell
git add docs/FUTURE_SUGGESTIONS.md
git add -f docs/sessions/SESSION_16_ADAPTIVE_THROUGHPUT_OPTIMIZATION.md
git commit -m "docs: summarize adaptive throughput optimization"
```

- [ ] **Step 6: 最终检查提交历史**

Run:

```powershell
git log --oneline -8
git status --short --branch
```

Expected: 本轮实现提交按测试、策略、队列、SSE、前端、文档顺序出现；除 `AGENTS.md` 外工作区干净。
