"""Tests for validation session runner ownership and retention."""

import asyncio
import time

import pytest

from app.services.session_manager import SessionManager


@pytest.mark.asyncio
async def test_ensure_runner_starts_validation_once_per_session():
    """Repeated subscribers must share one background validation runner."""
    manager = SessionManager()
    session_id = await manager.create_session([])
    runner_started = 0
    release_runner = asyncio.Event()

    async def runner():
        nonlocal runner_started
        runner_started += 1
        await release_runner.wait()

    first_task = await manager.ensure_runner(session_id, runner)
    second_task = await manager.ensure_runner(session_id, runner)
    await asyncio.sleep(0)

    assert first_task is second_task
    assert runner_started == 1

    release_runner.set()
    await first_task


@pytest.mark.asyncio
async def test_terminal_session_expires_after_retention_window():
    """Terminal sessions should be removed after the recovery window."""
    manager = SessionManager(retention_seconds=1800)
    session_id = await manager.create_session([])
    await manager.complete_session(session_id, [], {})
    session = await manager.get_session(session_id)
    session.finished_at = time.time() - 1801

    assert await manager.get_session(session_id) is None
