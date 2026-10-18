"""Integration tests for adaptive validation SSE scheduling."""

import json
import asyncio
import threading
import time

from fastapi.testclient import TestClient

from app.main import app
from app.services.search_validator import SearchValidatorService
from app.services.validator import ValidatorService


def test_sse_prioritizes_primary_work_and_reports_retry_phase(monkeypatch):
    """All primary attempts finish before retry and SSE exposes the phase."""
    calls = []
    attempts = {}

    async def fake_validate(
        url,
        timeout=None,
        client=None,
        max_retries=None,
    ):
        calls.append(url)
        attempts[url] = attempts.get(url, 0) + 1
        if url.endswith("/1") and attempts[url] == 1:
            return False, "超时"
        return True, ""

    monkeypatch.setattr(
        ValidatorService,
        "validate_source_access",
        staticmethod(fake_validate),
    )

    client = TestClient(app)
    response = client.post(
        "/api/validate/start-data",
        json={
            "sources": [
                {
                    "bookSourceName": "one",
                    "bookSourceUrl": "https://example.com/1",
                },
                {
                    "bookSourceName": "two",
                    "bookSourceUrl": "https://example.com/2",
                },
                {
                    "bookSourceName": "three",
                    "bookSourceUrl": "https://example.com/3",
                },
            ],
            "concurrency": 2,
            "timeout": 30,
            "validation_mode": "custom",
            "smart_enabled": True,
        },
    )
    session_id = response.json()["sessionId"]

    completed = None
    with client.stream(
        "GET",
        f"/api/validate/progress/{session_id}",
    ) as stream:
        for line in stream.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event.get("status") == "completed":
                completed = event
                break

    assert completed is not None
    assert calls[:3] == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]
    assert calls[3] == "https://example.com/1"
    assert completed["validCount"] == 3
    assert completed["invalidCount"] == 0
    assert completed["strategy"]["phase"] == "retry"


def test_cancel_while_paused_keeps_requests_completed_during_pause(
    monkeypatch,
):
    """A request completed during pause must be included in partial results."""
    first_started = threading.Event()
    second_started = threading.Event()
    finish_first = threading.Event()
    stream_result = {}

    async def fake_validate(
        url,
        timeout=None,
        client=None,
        max_retries=None,
    ):
        if url.endswith("/1"):
            first_started.set()
            while not finish_first.is_set():
                await asyncio.sleep(0.01)
            return True, ""

        second_started.set()
        while True:
            await asyncio.sleep(0.05)

    monkeypatch.setattr(
        ValidatorService,
        "validate_source_access",
        staticmethod(fake_validate),
    )

    control_client = TestClient(app)
    response = control_client.post(
        "/api/validate/start-data",
        json={
            "sources": [
                {
                    "bookSourceName": "one",
                    "bookSourceUrl": "https://example.com/1",
                },
                {
                    "bookSourceName": "two",
                    "bookSourceUrl": "https://example.com/2",
                },
            ],
            "concurrency": 2,
            "timeout": 30,
            "validation_mode": "custom",
            "smart_enabled": True,
        },
    )
    session_id = response.json()["sessionId"]

    def consume_stream():
        stream_client = TestClient(app)
        with stream_client.stream(
            "GET",
            f"/api/validate/progress/{session_id}",
        ) as stream:
            for line in stream.iter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event.get("status") == "cancelled":
                    stream_result.update(event)
                    return

    stream_thread = threading.Thread(target=consume_stream, daemon=True)
    stream_thread.start()
    assert first_started.wait(timeout=3)
    assert second_started.wait(timeout=3)

    control_client.post(
        "/api/validate/pause",
        data={"session_id": session_id},
    )
    time.sleep(0.5)
    finish_first.set()
    time.sleep(0.5)
    control_client.post(
        "/api/validate/cancel",
        data={"session_id": session_id},
    )
    stream_thread.join(timeout=5)

    assert not stream_thread.is_alive()
    assert stream_result["validCount"] == 1
    # 终态 SSE 消息只保留统计字段，避免弱网下超长消息被掐断
    assert "validSources" not in stream_result
    assert stream_result["resultReady"] is True

    result_response = control_client.get(f"/api/validate/result/{session_id}")
    result_data = result_response.json()["data"]
    assert result_data["validCount"] == 1
    assert result_data["validSources"][0]["bookSourceName"] == "one"


def test_completed_sse_result_can_be_replayed_without_rerunning(monkeypatch):
    """A reconnect after completion should receive the retained result."""
    calls = 0

    async def fake_validate(
        url,
        timeout=None,
        client=None,
        max_retries=None,
    ):
        nonlocal calls
        calls += 1
        return True, ""

    monkeypatch.setattr(
        ValidatorService,
        "validate_source_access",
        staticmethod(fake_validate),
    )

    client = TestClient(app)
    response = client.post(
        "/api/validate/start-data",
        json={
            "sources": [
                {
                    "bookSourceName": "one",
                    "bookSourceUrl": "https://example.com/1",
                },
            ],
            "concurrency": 1,
            "timeout": 30,
            "validation_mode": "custom",
            "smart_enabled": True,
        },
    )
    session_id = response.json()["sessionId"]

    def consume_terminal_event():
        with client.stream(
            "GET",
            f"/api/validate/progress/{session_id}",
        ) as stream:
            for line in stream.iter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event.get("status") == "completed" or event.get("error"):
                    return event
        return None

    first_result = consume_terminal_event()
    second_result = consume_terminal_event()

    assert first_result["status"] == "completed"
    assert second_result["status"] == "completed"
    assert second_result["validCount"] == 1
    assert calls == 1


def _search_source():
    return {
        "bookSourceName": "one",
        "bookSourceUrl": "https://example.com/1",
        "searchUrl": "https://example.com/search?q={{key}}",
    }


def _consume_search_stream(client, session_id):
    with client.stream(
        "GET",
        f"/api/validate/search/progress/{session_id}",
    ) as stream:
        for line in stream.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event.get("status") in ("completed", "cancelled", "error"):
                return event
    return None


def test_search_sse_retries_network_failure_then_succeeds(monkeypatch):
    """搜索校验的网络类失败应进入重试阶段并最终成功。"""
    calls = []
    attempts = {}

    async def fake_search(source, keyword, timeout=30, max_retries=2):
        url = source.get("bookSourceUrl")
        calls.append(url)
        attempts[url] = attempts.get(url, 0) + 1
        if attempts[url] == 1:
            return False, "超时", None
        return True, "", []

    monkeypatch.setattr(
        SearchValidatorService,
        "validate_search",
        staticmethod(fake_search),
    )

    client = TestClient(app)
    response = client.post(
        "/api/validate/search/start-data",
        json={
            "sources": [_search_source()],
            "keyword": "test",
            "validate_type": "search",
            "concurrency": 1,
            "timeout": 10,
            "validation_mode": "custom",
            "smart_enabled": True,
        },
    )
    session_id = response.json()["sessionId"]

    completed = _consume_search_stream(client, session_id)

    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["validCount"] == 1
    assert completed["invalidCount"] == 0
    assert len(calls) == 2
    assert completed["strategy"]["phase"] == "retry"

    result = client.get(f"/api/validate/result/{session_id}").json()["data"]
    assert result["validSources"]
    # 内部字段（_ruleType）只用于统计，不应下发给前端
    assert all(not key.startswith("_") for key in result["validSources"][0])
    assert result["ruleTypeStats"]["searchOnly"]["valid"] == 1


def test_search_sse_does_not_retry_rule_failures(monkeypatch):
    """规则类失败（非网络）不应进入重试阶段。"""
    calls = []

    async def fake_search(source, keyword, timeout=30, max_retries=2):
        calls.append(source.get("bookSourceUrl"))
        return False, "搜索无结果", None

    monkeypatch.setattr(
        SearchValidatorService,
        "validate_search",
        staticmethod(fake_search),
    )

    client = TestClient(app)
    response = client.post(
        "/api/validate/search/start-data",
        json={
            "sources": [_search_source()],
            "keyword": "test",
            "validate_type": "search",
            "concurrency": 1,
            "timeout": 10,
            "validation_mode": "custom",
            "smart_enabled": True,
        },
    )
    session_id = response.json()["sessionId"]

    completed = _consume_search_stream(client, session_id)

    assert completed is not None
    assert completed["validCount"] == 0
    assert completed["invalidCount"] == 1
    assert len(calls) == 1


def test_search_cancel_while_paused_keeps_partial_result(monkeypatch):
    """搜索校验暂停期间取消，应正常返回取消状态。"""
    started = threading.Event()
    stream_result = {}

    async def fake_search(source, keyword, timeout=30, max_retries=2):
        started.set()
        while True:
            await asyncio.sleep(0.05)

    monkeypatch.setattr(
        SearchValidatorService,
        "validate_search",
        staticmethod(fake_search),
    )

    control_client = TestClient(app)
    response = control_client.post(
        "/api/validate/search/start-data",
        json={
            "sources": [_search_source()],
            "keyword": "test",
            "validate_type": "search",
            "concurrency": 1,
            "timeout": 30,
            "validation_mode": "custom",
            "smart_enabled": True,
        },
    )
    session_id = response.json()["sessionId"]

    def consume_stream():
        stream_client = TestClient(app)
        event = _consume_search_stream(stream_client, session_id)
        if event:
            stream_result.update(event)

    stream_thread = threading.Thread(target=consume_stream, daemon=True)
    stream_thread.start()
    assert started.wait(timeout=3)

    control_client.post(
        "/api/validate/pause",
        data={"session_id": session_id},
    )
    time.sleep(0.5)
    control_client.post(
        "/api/validate/cancel",
        data={"session_id": session_id},
    )
    stream_thread.join(timeout=5)

    assert not stream_thread.is_alive()
    assert stream_result["status"] == "cancelled"
    assert stream_result["validCount"] == 0
