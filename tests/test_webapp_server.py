"""Tests for webapp/server.py (Card 02)."""
import pytest
from fastapi.testclient import TestClient

from webapp.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_options(client):
    resp = client.get("/api/options")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert "analysts" in data
    assert "research_depth" in data
    assert "asset_types" in data
    assert data["asset_types"] == ["stock", "crypto"]
    # analysts should have key+label
    assert all("key" in a and "label" in a for a in data["analysts"])
    # providers should have name+key+default_url
    assert all("name" in p and "key" in p and "default_url" in p for p in data["providers"])
    # research_depth should have label+value
    assert all("label" in d and "value" in d for d in data["research_depth"])


def test_get_models_quick(client):
    resp = client.get("/api/options/models?provider=openai&mode=quick")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("label" in m and "value" in m for m in data)


def test_get_models_deep(client):
    resp = client.get("/api/options/models?provider=openai&mode=deep")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_models_bad_provider(client):
    resp = client.get("/api/options/models?provider=bogus&mode=quick")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_get_models_bad_mode(client):
    resp = client.get("/api/options/models?provider=openai&mode=bad")
    assert resp.status_code == 400
    assert "error" in resp.json()
