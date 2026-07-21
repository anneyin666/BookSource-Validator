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
        """Return whether queued primary or retry work remains."""
        return bool(self.primary or self.retries)

    def advance_phase(self, *, active_count: int) -> None:
        """Enter retry phase after all primary work has finished."""
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
        """Schedule the next attempt without occupying an active slot."""
        if item.attempt >= self.max_retries:
            return False

        retry = ValidationWorkItem(
            source=item.source,
            attempt=item.attempt + 1,
            last_reason=reason,
        )
        heapq.heappush(
            self.retries,
            ScheduledRetry(
                ready_at=now + max(0.0, delay),
                sequence=next(self._sequence),
                item=retry,
            ),
        )
        return True

    def take_ready(
        self,
        *,
        limit: int,
        now: float,
    ) -> list[ValidationWorkItem]:
        """Take ready items from the current phase up to the free capacity."""
        if limit <= 0:
            return []

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
        """Return seconds until the next retry becomes ready."""
        if not self.retries:
            return None
        return max(0.0, self.retries[0].ready_at - now)
