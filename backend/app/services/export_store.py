import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ExportPayload:
    """临时导出的书源内容。"""
    export_id: str
    filename: str
    content: str
    expires_at: int


class ExportStore:
    """内存中的临时导出缓存。"""

    def __init__(self):
        self._exports: Dict[str, ExportPayload] = {}
        self._lock = asyncio.Lock()

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


export_store = ExportStore()
