"""Tests for adaptive validation throughput decisions."""

from app.services.validation_strategy import (
    AdaptiveValidationController,
    ValidationOptions,
    is_retryable_reason,
)


def build_controller(
    *,
    smart_enabled: bool = True,
) -> AdaptiveValidationController:
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
    """Fast HTTP failures must not be treated as local network pressure."""
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
    """A partial window must not change runtime settings."""
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
    """One unhealthy window may perform only one gradual reduction."""
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
    """Repeated unhealthy windows must preserve the balanced floor."""
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
    """A healthy independent window should gradually restore throughput."""
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
    """Dynamic timeout must remain bounded for dead sources."""
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
    """Disabling smart mode must preserve configured runtime options."""
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


def test_custom_mode_never_drops_below_global_floor():
    """Small custom values must still preserve four active slots."""
    controller = AdaptiveValidationController(
        ValidationOptions(
            concurrency=6,
            timeout=30,
            mode="custom",
            smart_enabled=True,
            max_retries=2,
        )
    )

    record_window(
        controller,
        count=64,
        duration=29,
        is_valid=False,
        reason="超时",
    )

    assert controller.current_concurrency == 4


def test_httpx_protocol_and_timeout_names_are_retryable():
    """httpx exception class names must enter the network retry path."""
    retryable_reasons = [
        "RemoteProtocolError",
        "ReadTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "ConnectError",
    ]

    assert all(is_retryable_reason(reason) for reason in retryable_reasons)
