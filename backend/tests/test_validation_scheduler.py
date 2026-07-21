"""Tests for first-pass priority and deferred retry scheduling."""

import pytest

from app.services.validation_scheduler import (
    AdaptiveWorkQueue,
    ValidationWorkItem,
)


def source(index: int) -> dict:
    """Build one deterministic source record."""
    return {
        "bookSourceName": f"source-{index}",
        "bookSourceUrl": f"https://example.com/{index}",
    }


def test_primary_sources_are_taken_before_retry_items():
    """Ready retries must not take slots while primary work remains."""
    queue = AdaptiveWorkQueue([source(1), source(2)], max_retries=2)
    retry_item = ValidationWorkItem(source=source(9), attempt=0)
    assert queue.schedule_retry(retry_item, "超时", now=0, delay=0)

    first = queue.take_ready(limit=1, now=0)

    assert first[0].source["bookSourceName"] == "source-1"
    assert first[0].attempt == 0
    assert queue.phase == "primary"


def test_retry_phase_waits_until_all_primary_tasks_finish():
    """Retry phase starts only after the last active primary task finishes."""
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
    """A delayed retry remains queued instead of occupying a request slot."""
    queue = AdaptiveWorkQueue([], max_retries=2)
    item = ValidationWorkItem(source=source(1), attempt=0)
    assert queue.schedule_retry(item, "连接失败", now=10, delay=2)

    queue.advance_phase(active_count=0)
    assert queue.take_ready(limit=1, now=11.9) == []
    assert queue.next_delay(now=11.9) == pytest.approx(0.1)
    assert queue.take_ready(limit=1, now=12)[0].attempt == 1


def test_retry_is_rejected_after_max_retries():
    """A source becomes final after its configured retries are exhausted."""
    queue = AdaptiveWorkQueue([], max_retries=2)
    item = ValidationWorkItem(source=source(1), attempt=2)

    assert not queue.schedule_retry(item, "超时", now=0, delay=1)
    assert not queue.has_work


def test_retry_phase_refills_free_slots_while_other_retries_run():
    """Active retries must not block filling other free retry slots."""
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
