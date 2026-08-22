"""Tests for webapp/server.py OHLCV endpoint (Card 06)."""
import pytest
from fastapi.testclient import TestClient

from webapp.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_ohlcv_missing_params(client):
    resp = client.get("/api/ohlcv")
    assert resp.status_code == 422  # FastAPI missing required query params


def test_get_ohlcv_bad_date_format(client, monkeypatch):
    def fake_load(symbol, date):
        raise ValueError("bad date")

    monkeypatch.setattr("webapp.server.load_ohlcv", fake_load)
    resp = client.get("/api/ohlcv?ticker=AAPL&date=bad-date")
    assert resp.status_code == 502
    assert "error" in resp.json()
