# Mobile SSE Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent mobile long-running validation from returning to the pre-validation screen after a transient SSE disconnect.

**Architecture:** Store one background runner on each validation session and make SSE endpoints read-only subscribers after the first connection starts it. Retain terminal sessions for 30 minutes and let the frontend keep the active UI while native EventSource reconnects.

**Tech Stack:** Python 3.10+, FastAPI, asyncio, pytest, Vue 3 JavaScript, Node test runner, Vite

---

### Task 1: Add failing backend recovery tests

**Files:**
- Create: `backend/tests/test_session_recovery.py`
- Modify: `backend/tests/test_adaptive_validation_sse.py`

- [ ] Add an async test that calls the planned `SessionManager.ensure_runner()` twice and asserts the same task is returned and the runner starts once.
- [ ] Add a retention test that completes a session, ages `finished_at` beyond 1,800 seconds, and asserts `get_session()` removes it.
- [ ] Add an SSE replay integration test that consumes a completed result twice and asserts `ValidatorService.validate_source_access` runs once.
- [ ] Run `python -m pytest tests/test_session_recovery.py tests/test_adaptive_validation_sse.py -v` from `backend` and confirm the new tests fail because runner ownership and result retention are missing.

### Task 2: Implement backend runner ownership and retention

**Files:**
- Modify: `backend/app/services/session_manager.py`
- Modify: `backend/app/api/sources.py`

- [ ] Add `runner_task` and `finished_at` to `ValidationSession`.
- [ ] Add locked `ensure_runner()`, `fail_session()`, and expired-terminal-session cleanup to `SessionManager`.
- [ ] Replace both SSE endpoint `asyncio.create_task(run_validation())` calls with `ensure_runner()`.
- [ ] Remove immediate terminal-session deletion from both SSE generators.
- [ ] Run the targeted backend tests and confirm they pass.

### Task 3: Add failing frontend recovery tests

**Files:**
- Create: `frontend/tests/eventSourceRecovery.test.js`
- Modify: `frontend/package.json`

- [ ] Write Node tests with a fake EventSource proving disconnect does not call `close()`, duplicate errors do not duplicate warnings, and `open` reports recovery.
- [ ] Add `test` script using `node --test`.
- [ ] Run `npm test` from `frontend` and confirm failure because the helper module does not exist.

### Task 4: Implement mobile EventSource recovery UI

**Files:**
- Create: `frontend/src/utils/eventSourceRecovery.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/ValidationProgress.vue`

- [ ] Implement the tested recovery binder around native EventSource callbacks.
- [ ] Route every validation EventSource through the binder and remove immediate close/exit behavior from transient `onerror` handlers.
- [ ] Keep timer and validating state active during reconnect.
- [ ] Display reconnecting text in the progress card and restore the running label on `open`.
- [ ] Run `npm test` and `npm run build`.

### Task 5: Update deployment and session documentation

**Files:**
- Modify: `docs/部署指南.md`
- Create: `docs/sessions/SESSION_17_MOBILE_SSE_RECOVERY.md`

- [ ] Add Nginx `proxy_buffering off`, `proxy_cache off`, `proxy_read_timeout 3600s`, and `proxy_send_timeout 3600s` guidance.
- [ ] Document root cause, implementation, tests, mobile retest checklist, and the 30-minute in-memory retention limitation.

### Task 6: Final verification

**Files:**
- Verify all changed files.

- [ ] Run `python -m pytest tests/ -v` from `backend`.
- [ ] Run `python -m compileall app` from `backend`.
- [ ] Run `npm test` and `npm run build` from `frontend`.
- [ ] Run targeted flake8 on the new backend test and session manager, plus fatal checks on modified legacy Python files.
- [ ] Review `git diff --check` and `git status --short`, excluding untracked `AGENTS.md` from the commit.
