# 校验会话管理
import asyncio
import uuid
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field


@dataclass
class ValidationSession:
    """校验会话"""
    session_id: str
    total: int = 0
    processed: int = 0
    valid: int = 0
    invalid: int = 0
    current_url: str = ""
    current_name: str = ""  # 当前处理的书源名称
    status: str = "pending"  # pending, running, completed, cancelled
    result: Optional[Dict] = None
    # 存储校验数据
    sources: List[dict] = field(default_factory=list)
    concurrency: int = 16
    timeout: int = 30
    # 最终结果
    valid_sources: List[dict] = field(default_factory=list)
    failed_sources: Dict[str, List[dict]] = field(default_factory=dict)
    # 批量处理额外信息
    file_stats: Optional[List[dict]] = None
    url_stats: Optional[List[dict]] = None
    dedup_count: int = 0
    duplicates: int = 0
    format_invalid: int = 0
    total_original: int = 0
    # 搜索校验额外信息
    search_keyword: str = ""
    validate_type: str = "search"  # 'search' 或 'explore'
    # 时间统计
    start_time: float = 0.0  # 开始时间戳
    # 任务引用（用于取消）
    validation_tasks: List[Any] = field(default_factory=list)


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self._sessions: Dict[str, ValidationSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, sources: List[dict], concurrency: int = 16, timeout: int = 30) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())[:8]
        session = ValidationSession(
            session_id=session_id,
            total=len(sources),
            sources=sources,
            concurrency=concurrency,
            timeout=timeout,
            start_time=time.time()  # 记录开始时间
        )
        async with self._lock:
            self._sessions[session_id] = session
        return session_id

    async def get_session(self, session_id: str) -> Optional[ValidationSession]:
        """获取会话"""
        async with self._lock:
            return self._sessions.get(session_id)

    async def update_progress(self, session_id: str, processed: int, valid: int, invalid: int, current_url: str, current_name: str = ""):
        """更新进度"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.processed = processed
                session.valid = valid
                session.invalid = invalid
                session.current_url = current_url
                session.current_name = current_name

    async def complete_session(self, session_id: str, valid_sources: List[dict], failed_sources: Dict[str, List[dict]]):
        """完成会话"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = "completed"
                session.valid_sources = valid_sources
                session.failed_sources = failed_sources

    async def cancel_session(self, session_id: str):
        """取消会话"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = "cancelled"
                # 取消所有正在运行的任务
                for task in session.validation_tasks:
                    if not task.done():
                        task.cancel()
                session.validation_tasks = []

    async def delete_session(self, session_id: str):
        """删除会话"""
        async with self._lock:
            self._sessions.pop(session_id, None)


# 全局会话管理器
session_manager = SessionManager()