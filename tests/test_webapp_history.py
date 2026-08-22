"""Tests for webapp/server.py history/report/compare endpoints (Card 05)."""
import pytest
from fastapi.testclient import TestClient

from webapp.server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_results(monkeypatch, tmp_path):
    """Create fake results_dir with AAPL/2026-01-01 and MSFT/2026-01-02."""
    import webapp.server as srv
    # Patch _results_dir to return tmp_path
    monkeypatch.setattr(srv, "_results_dir", lambda: tmp_path)

    # AAPL run with decision
    aapl_dir = tmp_path / "AAPL" / "2026-01-01"
    aapl_dir.mkdir(parents=True)
    (aapl_dir / "complete_report.md").write_text("# AAPL Report\n\nBUY signal.", encoding="utf-8")
    (aapl_dir / "final_trade_decision.md").write_text("Final decision: **BUY**", encoding="utf-8")

    # MSFT run without decision file
    msft_dir = tmp_path / "MSFT" / "2026-01-02"
    msft_dir.mkdir(parents=True)
    (msft_dir / "complete_report.md").write_text("# MSFT Report\n\nHold.", encoding="utf-8")

    return tmp_path


def test_get_history(fake_results, client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    aapl = next(item for item in data if item["ticker"] == "AAPL")
    assert aapl["date"] == "2026-01-01"
    assert aapl["decision"] == "BUY"
    assert aapl["path"] == "AAPL/2026-01-01"

    msft = next(item for item in data if item["ticker"] == "MSFT")
    assert msft["date"] == "2026-01-02"
    assert msft["decision"] is None


def test_get_report(fake_results, client):
    resp = client.get("/api/report?path=AAPL/2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert "AAPL Report" in data["content"]


def test_get_report_not_found(fake_results, client):
    resp = client.get("/api/report?path=UNKNOWN/2026-01-01")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_get_report_traversal(fake_results, client):
    resp = client.get("/api/report?path=../outside")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_get_report_traversal_absolute(fake_results, client):
    resp = client.get("/api/report?path=/etc/passwd")
    assert resp.status_code == 400


def test_compare_history(fake_results, client):
    resp = client.get("/api/history/compare?paths=AAPL/2026-01-01,MSFT/2026-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["ticker"] == "AAPL"
    assert data[0]["decision"] == "BUY"
    assert "AAPL Report" in data[0]["content"]
    assert data[1]["ticker"] == "MSFT"
    assert data[1]["decision"] is None


def test_compare_history_too_few(fake_results, client):
    resp = client.get("/api/history/compare?paths=AAPL/2026-01-01")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_compare_history_too_many(fake_results, client):
    resp = client.get("/api/history/compare?paths=a,b,c,d,e")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_compare_history_traversal(fake_results, client):
    resp = client.get("/api/history/compare?paths=AAPL/2026-01-01,../outside")
    assert resp.status_code == 400
    assert "error" in resp.json()
