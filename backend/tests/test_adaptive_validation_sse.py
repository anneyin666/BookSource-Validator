"""Integration tests for adaptive validation SSE scheduling."""

import json
import asyncio
import threading
import time

from fastapi.testclient import TestClient

from app.main import app
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
    assert stream_result["validSources"][0]["bookSourceName"] == "one"
