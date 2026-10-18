"""Adaptive validation strategy and runtime option helpers."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Deque


NETWORK_RETRY_REASONS = {
    "超时",
    "连接超时",
    "连接失败",
    "读取错误",
    "写入错误",
    "读取超时",
    "写入超时",
    "服务器断开",
    "协议错误",
    "网络错误",
    "SSL错误",
    "重试耗尽",
    "ConnectError",
    "ConnectTimeout",
    "ReadError",
    "ReadTimeout",
    "WriteError",
    "WriteTimeout",
    "PoolTimeout",
    "RemoteProtocolError",
    "ProtocolError",
    "NetworkError",
    "ProxyError",
    "SSL",
}

TIMEOUT_REASONS = {
    "超时",
    "连接超时",
    "读取超时",
    "写入超时",
    "ConnectTimeout",
    "ReadTimeout",
    "WriteTimeout",
    "PoolTimeout",
}

PRESET_OPTIONS = {
    # 极速：高并发 + 短超时 + 不重试，并强制关闭智能降速，
    # 适合死源多的大批量快速清理。
    "turbo": {
        "concurrency": 32,
        "timeout": 10,
        "max_retries": 0,
        "smart": False,
    },
    "fast": {"concurrency": 32, "timeout": 15, "max_retries": 1},
    "balanced": {"concurrency": 16, "timeout": 30, "max_retries": 2},
    "stable": {"concurrency": 8, "timeout": 45, "max_retries": 3},
}

MIN_CONCURRENCY = 1
MAX_CONCURRENCY = 64
MIN_TIMEOUT = 5
MAX_TIMEOUT = 120
DEFAULT_MODE = "balanced"
SAMPLE_WINDOW_SIZE = 32
EVALUATION_INTERVAL = 16
MIN_CONCURRENCY_RATIO = 0.5
ADAPTIVE_MIN_CONCURRENCY = 4
MAX_TIMEOUT_INCREASE = 10


@dataclass
class ValidationOptions:
    """Normalized validation runtime options."""

    concurrency: int
    timeout: int
    mode: str = DEFAULT_MODE
    smart_enabled: bool = True
    max_retries: int = 2


@dataclass
class ValidationSample:
    """Single first-pass validation result sample."""

    duration: float
    is_valid: bool
    reason: str


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


def is_retryable_reason(reason: str) -> bool:
    """Return whether the failure reason is worth retrying."""
    return any(keyword in (reason or "") for keyword in NETWORK_RETRY_REASONS)


def is_timeout_reason(reason: str) -> bool:
    """Return whether the failure reason is timeout-related."""
    return any(keyword in (reason or "") for keyword in TIMEOUT_REASONS)


def get_retry_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
) -> float:
    """Calculate exponential backoff delay for retry attempts."""
    return min(max_delay, base_delay * (2 ** max(0, attempt)))


def normalize_validation_options(
    concurrency: int | str | None = None,
    timeout: int | str | None = None,
    mode: str | None = None,
    smart_enabled: bool | str | None = True,
) -> ValidationOptions:
    """Normalize validation mode, concurrency and timeout."""
    normalized_mode = (mode or DEFAULT_MODE).strip().lower()
    if normalized_mode not in PRESET_OPTIONS and normalized_mode != "custom":
        # 未知模式常见于前后端版本不一致（如新前端 + 旧后端）。
        # 回退到 custom，至少保留客户端传入的并发/超时，而不是被预设覆盖。
        normalized_mode = "custom"

    preset = PRESET_OPTIONS.get(normalized_mode, {})

    try:
        normalized_concurrency = int(
            concurrency
            if concurrency is not None
            else preset.get("concurrency", 16)
        )
    except (TypeError, ValueError):
        normalized_concurrency = preset.get("concurrency", 16)

    try:
        normalized_timeout = int(
            timeout if timeout is not None else preset.get("timeout", 30)
        )
    except (TypeError, ValueError):
        normalized_timeout = preset.get("timeout", 30)

    if normalized_mode != "custom":
        normalized_concurrency = preset["concurrency"]
        normalized_timeout = preset["timeout"]

    if isinstance(smart_enabled, str):
        normalized_smart = smart_enabled.lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
    else:
        normalized_smart = bool(smart_enabled)

    # 预设可强制覆盖智能调参（如 turbo 关闭降速）
    if "smart" in preset:
        normalized_smart = bool(preset["smart"])

    normalized_concurrency = max(
        MIN_CONCURRENCY,
        min(MAX_CONCURRENCY, normalized_concurrency),
    )
    normalized_timeout = max(
        MIN_TIMEOUT,
        min(MAX_TIMEOUT, normalized_timeout),
    )

    return ValidationOptions(
        concurrency=normalized_concurrency,
        timeout=normalized_timeout,
        mode=normalized_mode,
        smart_enabled=normalized_smart,
        max_retries=preset.get("max_retries", 2),
    )


class AdaptiveValidationController:
    """Evaluate independent first-pass windows and adjust runtime hints."""

    def __init__(self, options: ValidationOptions):
        self.options = options
        self.max_concurrency = options.concurrency
        self.current_concurrency = options.concurrency
        self.min_concurrency = min(
            self.max_concurrency,
            max(
                ADAPTIVE_MIN_CONCURRENCY,
                math.ceil(
                    self.max_concurrency * MIN_CONCURRENCY_RATIO
                ),
            ),
        )
        self.base_timeout = options.timeout
        self.current_timeout = options.timeout
        self.max_timeout = min(
            MAX_TIMEOUT,
            options.timeout + MAX_TIMEOUT_INCREASE,
        )
        self.samples: Deque[ValidationSample] = deque(
            maxlen=SAMPLE_WINDOW_SIZE
        )
        self.evaluation_samples: list[ValidationSample] = []
        # 最近一个评估窗口的超时占比，用于决定是否值得重试超时失败
        self.last_timeout_rate = 0.0

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

    def should_retry_timeout(self) -> bool:
        """超时失败是否值得重试。

        样本足够且近期超时占比过半时，通常说明这是一批死源，
        重试只会让每条再白等一个超时。
        """
        if self.last_timeout_rate >= 0.5:
            return False

        if len(self.samples) >= 8:
            timeout_count = sum(
                1
                for sample in self.samples
                if not sample.is_valid and is_timeout_reason(sample.reason)
            )
            if timeout_count / len(self.samples) >= 0.5:
                return False

        return True

    def _evaluate_window(
        self,
        samples: list[ValidationSample],
    ) -> StrategyAdjustment:
        """Evaluate one independent sample window and adjust once."""
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
        self.last_timeout_rate = timeout_rate

        # 只有出现"成功样本"或"连接类失败"时才认为可能是网络压力。
        # 全超时的窗口更可能是死源，降低并发只会让清理更慢。
        has_success = any(sample.is_valid for sample in samples)
        has_connect_failure = any(
            not sample.is_valid
            and is_retryable_reason(sample.reason)
            and not is_timeout_reason(sample.reason)
            for sample in samples
        )

        should_reduce = (
            (has_success or has_connect_failure)
            and (
                network_error_rate >= 0.35
                or timeout_rate >= 0.25
                or (
                    network_error_rate > 0
                    and p75_duration >= self.current_timeout * 0.8
                )
            )
        )
        is_healthy = (
            network_error_rate <= 0.10
            and timeout_rate <= 0.05
            and p75_duration < self.base_timeout * 0.6
        )

        previous_concurrency = self.current_concurrency
        previous_timeout = self.current_timeout
        adjustment_reasons = []

        if should_reduce:
            self.current_concurrency = max(
                self.min_concurrency,
                math.ceil(self.current_concurrency * 0.75),
            )
            adjustment_reasons.append("network_pressure")
        elif is_healthy:
            self.current_concurrency = min(
                self.max_concurrency,
                self.current_concurrency + 2,
            )
            adjustment_reasons.append("healthy")

        # 只有出现"接近超时的成功样本"时才提高超时；
        # 全是超时失败通常意味着死源，抬高超时只会让尾部更慢。
        slow_success = any(
            sample.is_valid
            and sample.duration >= self.current_timeout * 0.7
            for sample in samples
        )
        if timeout_rate >= 0.35 and slow_success:
            self.current_timeout = min(
                self.max_timeout,
                self.current_timeout + 5,
            )
            adjustment_reasons.append("timeout_pressure")
        elif is_healthy:
            self.current_timeout = max(
                self.base_timeout,
                self.current_timeout - 5,
            )

        if not adjustment_reasons:
            adjustment_reasons.append("unchanged")

        return StrategyAdjustment(
            reason="+".join(adjustment_reasons),
            sample_count=len(samples),
            network_error_rate=network_error_rate,
            timeout_rate=timeout_rate,
            p75_duration=p75_duration,
            previous_concurrency=previous_concurrency,
            current_concurrency=self.current_concurrency,
            previous_timeout=previous_timeout,
            current_timeout=self.current_timeout,
        )

    def snapshot(self) -> dict:
        """Return strategy state for SSE progress messages."""
        return {
            "mode": self.options.mode,
            "smartEnabled": self.options.smart_enabled,
            "currentConcurrency": self.current_concurrency,
            "maxConcurrency": self.max_concurrency,
            "minConcurrency": self.min_concurrency,
            "currentTimeout": self.current_timeout,
            "baseTimeout": self.base_timeout,
            "maxTimeout": self.max_timeout,
        }
