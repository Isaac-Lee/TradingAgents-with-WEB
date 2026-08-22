"""Tests for webapp/server.py runs endpoints (Card 03)."""
import json
import queue
import threading

import pytest
from fastapi.testclient import TestClient

from webapp.server import app


@pytest.fixture
def client():
    return TestClient(app)


class FakeHandle:
    def __init__(self, run_id):
        self.run_id = run_id
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = FakeThread(alive=True)


class FakeThread:
    def __init__(self, alive=True):
        self._alive = alive

    def is_alive(self):
        return self._alive


def _inject_events(handle, event_list):
    for e in event_list:
        handle.events.put(e)


# Reset global state between tests
@pytest.fixture(autouse=True)
def reset_runs(monkeypatch):
    import webapp.server as srv
    srv._runs.clear()
    srv._active_run_id = None


def test_create_run_success(client, monkeypatch):
    fake = FakeHandle("run-123")
    monkeypatch.setattr("webapp.server.start_run", lambda req: fake)
    monkeypatch.setattr("webapp.server._api_key_error", lambda p: None)

    resp = client.post("/api/runs", json={
        "ticker": "AAPL",
        "analysis_date": "2026-01-01",
        "analysts": ["market"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "shallow_thinker": "gpt-4o-mini",
        "deep_thinker": "gpt-4o",
    })
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data


def test_create_run_missing_fields(client):
    resp = client.post("/api/runs", json={"ticker": "AAPL"})
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_create_run_missing_api_key(client, monkeypatch):
    monkeypatch.setattr("webapp.server._api_key_error", lambda p: "OPENAI_API_KEY not set")

    resp = client.post("/api/runs", json={
        "ticker": "AAPL",
        "analysis_date": "2026-01-01",
        "analysts": ["market"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "shallow_thinker": "gpt-4o-mini",
        "deep_thinker": "gpt-4o",
    })
    assert resp.status_code == 400
    assert resp.json()["error"] == "OPENAI_API_KEY not set"


def test_create_run_concurrent(client, monkeypatch):
    fake = FakeHandle("run-123")
    monkeypatch.setattr("webapp.server.start_run", lambda req: fake)
    monkeypatch.setattr("webapp.server._api_key_error", lambda p: None)

    resp1 = client.post("/api/runs", json={
        "ticker": "AAPL",
        "analysis_date": "2026-01-01",
        "analysts": ["market"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "shallow_thinker": "gpt-4o-mini",
        "deep_thinker": "gpt-4o",
    })
    assert resp1.status_code == 202

    resp2 = client.post("/api/runs", json={
        "ticker": "MSFT",
        "analysis_date": "2026-01-02",
        "analysts": ["market"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "shallow_thinker": "gpt-4o-mini",
        "deep_thinker": "gpt-4o",
    })
    assert resp2.status_code == 409
    assert "already in progress" in resp2.json()["error"]


def test_get_events_sse(client, monkeypatch):
    fake = FakeHandle("run-456")
    _inject_events(fake, [
        {"type": "status", "agent": "Market Analyst", "state": "in_progress"},
        {"type": "done", "status": "completed", "decision": "BUY", "path": "results/AAPL/2026-01-01"},
    ])
    fake.thread = FakeThread(alive=False)
    monkeypatch.setattr("webapp.server.start_run", lambda req: fake)
    monkeypatch.setattr("webapp.server._api_key_error", lambda p: None)

    resp = client.post("/api/runs", json={
        "ticker": "AAPL",
        "analysis_date": "2026-01-01",
        "analysts": ["market"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "shallow_thinker": "gpt-4o-mini",
        "deep_thinker": "gpt-4o",
    })
    run_id = resp.json()["run_id"]

    resp_events = client.get(f"/api/runs/{run_id}/events")
    assert resp_events.status_code == 200
    assert resp_events.headers["content-type"].startswith("text/event-stream")

    body = resp_events.text
    lines = [l for l in body.split("\n") if l.startswith("data:")]
    assert len(lines) == 2
    assert json.loads(lines[0].replace("data: ", ""))["type"] == "status"
    assert json.loads(lines[1].replace("data: ", ""))["type"] == "done"


def test_stop_run(client, monkeypatch):
    fake = FakeHandle("run-789")
    _inject_events(fake, [
        {"type": "done", "status": "stopped"},
    ])
    fake.thread = FakeThread(alive=False)
    monkeypatch.setattr("webapp.server.start_run", lambda req: fake)
    monkeypatch.setattr("webapp.server._api_key_error", lambda p: None)

    resp = client.post("/api/runs", json={
        "ticker": "AAPL",
        "analysis_date": "2026-01-01",
        "analysts": ["market"],
        "research_depth": 1,
        "llm_provider": "openai",
        "backend_url": "https://api.openai.com/v1",
        "shallow_thinker": "gpt-4o-mini",
        "deep_thinker": "gpt-4o",
    })
    run_id = resp.json()["run_id"]

    resp_stop = client.post(f"/api/runs/{run_id}/stop")
    assert resp_stop.status_code == 200
    assert resp_stop.json()["ok"] is True


def test_events_run_not_found(client):
    resp = client.get("/api/runs/nonexistent/events")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_stop_run_not_found(client):
    resp = client.post("/api/runs/nonexistent/stop")
    assert resp.status_code == 404
    assert "error" in resp.json()
