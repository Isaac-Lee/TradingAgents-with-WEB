"""Local web boundary and job lifecycle tests. No paid model/data calls."""

import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from webapp.server import make_server
from webapp.service import JobStore, markdown, market_data, validate_request


def test_market_data_preserves_ohlc_and_excludes_future_bars(monkeypatch):
    from types import SimpleNamespace

    import pandas as pd
    import yfinance as yf

    frame = pd.DataFrame(
        {"Open": [10, float("nan"), 40], "High": [14, 15, 42],
         "Low": [9, 11, 38], "Close": [12, 13, 41], "Volume": [100, 200, 300]},
        index=pd.to_datetime(["2026-08-25", "2026-08-26", "2026-08-27"]),
    )
    def history(**kwargs):
        assert kwargs["start"] == "2025-08-25"
        assert kwargs["end"] == "2026-08-27"
        return frame

    monkeypatch.setattr(yf, "Ticker", lambda symbol: SimpleNamespace(
        history=history, history_metadata={"currency": "USD"}))
    data = market_data("ORCL", "2026-08-26")
    assert data["bars"] == [
        {"date": "2026-08-25", "open": 10, "high": 14, "low": 9, "close": 12, "volume": 100},
        {"date": "2026-08-26", "open": None, "high": 15, "low": 11, "close": 13, "volume": 200},
    ]
    assert data["currency"] == "USD"
    json.dumps(data, allow_nan=False)


def config(**changes):
    return dict(
        symbol="NVDA",
        date="2026-08-25",
        provider="codex",
        analysts=["market"],
        depth=1,
        quickModel="default",
        deepModel="default",
        **changes,
    )


def wait_done(store, job_id):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        job = store.get(job_id)
        if job["status"] not in {"queued", "running", "cancelling"}:
            return job
        time.sleep(0.01)
    pytest.fail("Worker did not reach terminal state")


@pytest.mark.parametrize(
    "field,value",
    [
        ("symbol", "../../.env"),
        ("symbol", "A/B"),
        ("symbol", "<script>"),
        ("date", "2099-01-01"),
        ("date", "invalid"),
        ("depth", True),
        ("depth", 2),
        ("analysts", []),
        ("analysts", ["market", "market"]),
        ("analysts", ["unknown"]),
        ("provider", "unknown"),
        ("quickModel", ""),
    ],
)
def test_validation(field, value):
    body = config()
    body[field] = value
    with pytest.raises(ValueError):
        validate_request(body, {"codex"})


def test_stream_persistence_and_export(tmp_path):
    def runner(cfg, root, progress):
        progress({"market_report": "First actual node output"})
        return {
            "market_report": "First actual node output",
            "final_trade_decision": "Rating: Hold",
        }, "Hold"

    store = JobStore(tmp_path, runner)
    job = store.submit(config())
    result = wait_done(store, job["id"])
    assert result["status"] == "completed"
    assert result["signal"] == "Hold"
    assert result["events"]
    assert "Rating: Hold" in markdown(result)
    store.preferences(config())
    store.close()
    reopened = JobStore(tmp_path, runner)
    assert reopened.get(job["id"])["reports"] == result["reports"]
    assert reopened.preferences()["provider"] == "codex"
    reopened.close()


def test_cancellation_single_run_and_partial_reports(tmp_path):
    reached, release = threading.Event(), threading.Event()

    def runner(cfg, root, progress):
        progress({"market_report": "Partial report"})
        reached.set()
        assert release.wait(5)
        progress({"final_trade_decision": "Should not be published"})
        return {}, "Buy"

    store = JobStore(tmp_path, runner)
    job = store.submit(config())
    assert reached.wait(5)
    try:
        with pytest.raises(ValueError):
            store.submit(config())
        store.cancel(job["id"])
    finally:
        release.set()
    result = wait_done(store, job["id"])
    assert result["status"] == "cancelled"
    assert result["signal"] is None
    assert result["reports"]["market_report"] == "Partial report"
    assert "final_trade_decision" not in result["reports"]
    store.close()


def test_failure_redacts_provider_exception_and_restart(tmp_path):
    def runner(*args):
        raise RuntimeError("https://provider.test?api_key=SECRET")

    store = JobStore(tmp_path, runner)
    result = wait_done(store, store.submit(config())["id"])
    assert result["status"] == "failed"
    assert "SECRET" not in json.dumps(result)
    store.save({"id": "interrupted", "status": "running", "config": config(), "reports": {}})
    store.close()
    store = JobStore(tmp_path, runner)
    assert store.get("interrupted")["status"] == "interrupted"
    store.close()


def test_http_origin_token_static_boundary(tmp_path):
    store = JobStore(tmp_path, lambda c, p, cb: ({"final_trade_decision": "Rating: Hold"}, "Hold"))
    server = make_server(0, store, lambda: {"providers": [{"id": "codex", "configured": True}]})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def request(path, data=None, headers=None):
        req = Request(
            base + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        return urlopen(req, timeout=5)

    try:
        with request("/api/bootstrap") as response:
            token = json.load(response)["token"]
        for path in ("/.env", "/../.web-data/workspace.sqlite3", "/api/jobs/missing"):
            with pytest.raises(HTTPError) as exc:
                request(path)
            assert exc.value.code == 404
        for headers in (
            {},
            {"X-Workspace-Token": token, "Origin": "https://evil.test"},
            {"X-Workspace-Token": token, "Host": "evil.test"},
        ):
            with pytest.raises(HTTPError) as exc:
                request("/api/jobs", config(), headers)
            assert exc.value.code == 403
        with request("/api/jobs", config(), {"X-Workspace-Token": token}) as response:
            job = json.load(response)
        assert wait_done(store, job["id"])["signal"] == "Hold"
        with request(f"/api/jobs/{job['id']}/report") as response:
            assert "attachment" in response.headers["Content-Disposition"]
            assert b"Rating: Hold" in response.read()
        with request("/") as response:
            assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
            assert b"live.css" in response.read()
        store.save({"id": "imported", "status": "imported", "config": config(), "reports": {}})
        with pytest.raises(HTTPError) as exc:
            request("/api/jobs/imported/delete", {})
        assert exc.value.code == 403
        with request("/api/jobs/imported/delete", {}, {"X-Workspace-Token": token}) as response:
            assert json.load(response) == {"id": "imported", "deleted": True}
        with pytest.raises(KeyError):
            store.get("imported")
        store.save({"id": "stopped", "status": "interrupted", "reports": {}})
        with request("/api/jobs/stopped/delete", {}, {"X-Workspace-Token": token}) as response:
            assert json.load(response)["deleted"] is True
        store.save({"id": "active", "status": "running", "reports": {}})
        with pytest.raises(HTTPError) as exc:
            request("/api/jobs/active/delete", {}, {"X-Workspace-Token": token})
        assert exc.value.code == 400
        assert "먼저 중지" in json.load(exc.value)["error"]
        assert store.get("active")["status"] == "running"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        store.close()


def test_propagate_stream_callback_preserves_finalization():
    from types import SimpleNamespace
    from unittest.mock import Mock

    from tradingagents.graph.trading_graph import TradingAgentsGraph

    graph = TradingAgentsGraph.__new__(TradingAgentsGraph)
    graph.memory_log = SimpleNamespace(
        get_past_context=Mock(return_value=""), store_decision=Mock()
    )
    graph.resolve_instrument_context = Mock(return_value="")
    graph.propagator = SimpleNamespace(
        create_initial_state=Mock(return_value={}),
        get_graph_args=Mock(return_value={"stream_mode": "values"}),
    )
    graph.graph = SimpleNamespace(
        stream=Mock(
            return_value=iter(
                [
                    {"market_report": "report"},
                    {"market_report": "report", "final_trade_decision": "Rating: Hold"},
                ]
            )
        )
    )
    graph.checkpoint_input = lambda state: state
    graph.stats_handler = SimpleNamespace(get_stats=Mock(return_value={}))
    graph._resuming = False
    graph._log_state = Mock()
    graph.clear_checkpoint_on_success = Mock()
    graph.process_signal = Mock(return_value="Hold")
    progress = Mock()
    state, signal = graph._run_graph("NVDA", "2026-08-25", progress_callback=progress)
    assert progress.call_count == 2
    assert state["market_report"] == "report" and signal == "Hold"
    graph.memory_log.store_decision.assert_called_once()
    graph.clear_checkpoint_on_success.assert_called_once()


@pytest.mark.parametrize('status', ['interrupted', 'cancelled', 'failed'])
def test_delete_stopped_analysis_preserves_report(tmp_path, status):
    store = JobStore(tmp_path)
    try:
        job = {'id': 'stopped', 'status': status, 'reports': {'market_report': 'Saved analysis'}}
        store.save(job)
        assert store.delete_report('stopped') == {'id': 'stopped', 'deleted': True}
        with pytest.raises(KeyError):
            store.get('stopped')
        archived = store.db.execute('SELECT body FROM trashed_jobs WHERE id=?', ('stopped',)).fetchone()
        assert json.loads(archived[0]) == job
    finally:
        store.close()


@pytest.mark.parametrize('status', ['queued', 'running', 'cancelling'])
def test_delete_rejects_active_analysis(tmp_path, status):
    store = JobStore(tmp_path)
    try:
        job = {'id': 'active', 'status': status}
        store.save(job)
        with pytest.raises(ValueError):
            store.delete_report('active')
        assert store.get('active') == job
    finally:
        store.close()
