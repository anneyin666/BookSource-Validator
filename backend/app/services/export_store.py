import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional

from app.config import settings


@dataclass
class ExportPayload:
    """临时导出的书源内容。"""
    export_id: str
    filename: str
    content: str
    expires_at: int


DEFAULT_MAX_EXPORTS = settings.MAX_EXPORTS


class ExportStore:
    """内存中的临时导出缓存。"""

    def __init__(self, max_exports: int = DEFAULT_MAX_EXPORTS):
        self._exports: Dict[str, ExportPayload] = {}
        self._lock = asyncio.Lock()
        self._max_exports = max_exports

    async def create_export(self, content: str, filename: str, ttl_seconds: int) -> ExportPayload:
        now = int(time.time())
        payload = ExportPayload(
            export_id=uuid.uuid4().hex[:12],
            filename=filename,
            content=content,
            expires_at=now + ttl_seconds,
        )
        async with self._lock:
            self._cleanup_expired_locked(now)
            self._evict_overflow_locked()
            self._exports[payload.export_id] = payload
        return payload

    async def get_export(self, export_id: str) -> Optional[ExportPayload]:
        now = int(time.time())
        async with self._lock:
            self._cleanup_expired_locked(now)
            return self._exports.get(export_id)

    def _cleanup_expired_locked(self, now: int) -> None:
        expired_ids = [
            export_id
            for export_id, payload in self._exports.items()
            if payload.expires_at <= now
        ]
        for export_id in expired_ids:
            self._exports.pop(export_id, None)

    def _evict_overflow_locked(self) -> None:
        """导出数达到上限时淘汰最早的条目，防止内存被无限占用。"""
        while len(self._exports) >= self._max_exports:
            oldest_id = next(iter(self._exports))
            self._exports.pop(oldest_id, None)


export_store = ExportStore()
