"""Adaptive validation strategy and runtime option helpers."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
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
}

PRESET_OPTIONS = {
    "fast": {"concurrency": 32, "timeout": 15, "max_retries": 1},
    "balanced": {"concurrency": 16, "timeout": 30, "max_retries": 2},
    "stable": {"concurrency": 8, "timeout": 45, "max_retries": 3},
}

MIN_CONCURRENCY = 1
MAX_CONCURRENCY = 64
MIN_TIMEOUT = 5
MAX_TIMEOUT = 120
DEFAULT_MODE = "balanced"


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
    """Single validation result sample."""

    duration: float
    is_valid: bool
    reason: str


def is_retryable_reason(reason: str) -> bool:
    """Return whether the failure reason is worth retrying."""
    return any(keyword in (reason or "") for keyword in NETWORK_RETRY_REASONS)


def get_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 8.0) -> float:
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
        normalized_mode = DEFAULT_MODE

    preset = PRESET_OPTIONS.get(normalized_mode, {})

    try:
        normalized_concurrency = int(
            concurrency if concurrency is not None else preset.get("concurrency", 16)
        )
    except (TypeError, ValueError):
        normalized_concurrency = preset.get("concurrency", 16)

    try:
        normalized_timeout = int(timeout if timeout is not None else preset.get("timeout", 30))
    except (TypeError, ValueError):
        normalized_timeout = preset.get("timeout", 30)

    if normalized_mode != "custom":
        normalized_concurrency = preset["concurrency"]
        normalized_timeout = preset["timeout"]

    if isinstance(smart_enabled, str):
        normalized_smart = smart_enabled.lower() not in {"0", "false", "no", "off"}
    else:
        normalized_smart = bool(smart_enabled)

    normalized_concurrency = max(
        MIN_CONCURRENCY,
        min(MAX_CONCURRENCY, normalized_concurrency),
    )
    normalized_timeout = max(MIN_TIMEOUT, min(MAX_TIMEOUT, normalized_timeout))

    return ValidationOptions(
        concurrency=normalized_concurrency,
        timeout=normalized_timeout,
        mode=normalized_mode,
        smart_enabled=normalized_smart,
        max_retries=preset.get("max_retries", 2),
    )


class AdaptiveValidationController:
    """Track recent validation results and adjust concurrency/timeout hints."""

    def __init__(self, options: ValidationOptions):
        self.options = options
        self.max_concurrency = options.concurrency
        self.current_concurrency = options.concurrency
        self.base_timeout = options.timeout
        self.current_timeout = options.timeout
        self.samples: Deque[ValidationSample] = deque(maxlen=20)

    def record(self, duration: float, is_valid: bool, reason: str) -> None:
        """Record one result and adjust strategy when needed."""
        self.samples.append(ValidationSample(duration, is_valid, reason))
        if not self.options.smart_enabled or len(self.samples) < 8:
            return

        failure_count = sum(1 for sample in self.samples if not sample.is_valid)
        retryable_count = sum(
            1 for sample in self.samples
            if not sample.is_valid and is_retryable_reason(sample.reason)
        )
        avg_duration = sum(sample.duration for sample in self.samples) / len(self.samples)
        failure_rate = failure_count / len(self.samples)
        retryable_rate = retryable_count / len(self.samples)

        should_slow_down = (
            failure_rate >= 0.55
            or retryable_rate >= 0.35
            or avg_duration >= self.current_timeout * 0.75
        )
        can_speed_up = (
            failure_rate <= 0.20
            and retryable_rate <= 0.10
            and avg_duration <= self.current_timeout * 0.45
        )

        if should_slow_down and self.current_concurrency > MIN_CONCURRENCY:
            self.current_concurrency = max(
                MIN_CONCURRENCY,
                max(self.current_concurrency // 2, self.current_concurrency - 8),
            )
        elif can_speed_up and self.current_concurrency < self.max_concurrency:
            self.current_concurrency = min(self.max_concurrency, self.current_concurrency + 2)

        timeout_heavy = retryable_rate >= 0.30 or avg_duration >= self.current_timeout * 0.85
        if timeout_heavy and self.current_timeout < MAX_TIMEOUT:
            self.current_timeout = min(MAX_TIMEOUT, self.current_timeout + 5)
        elif can_speed_up and self.current_timeout > self.base_timeout:
            self.current_timeout = max(self.base_timeout, self.current_timeout - 5)

    def snapshot(self) -> dict:
        """Return strategy state for SSE progress messages."""
        return {
            "mode": self.options.mode,
            "smartEnabled": self.options.smart_enabled,
            "currentConcurrency": self.current_concurrency,
            "maxConcurrency": self.max_concurrency,
            "currentTimeout": self.current_timeout,
            "baseTimeout": self.base_timeout,
        }
