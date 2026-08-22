"""Tests for webapp/static frontend files (Card 04)."""
import pytest
from fastapi.testclient import TestClient

from webapp.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_static_css_served(client):
    resp = client.get("/static/styles.css")
    assert resp.status_code == 200
    text = resp.text
    # All color tokens defined
    assert "--bg:" in text
    assert "--surface:" in text
    assert "--success:" in text
    assert "--danger:" in text


def test_static_js_served(client):
    resp = client.get("/static/app.js")
    assert resp.status_code == 200
    text = resp.text
    assert "EventSource" in text
    assert "fetch('/api/options')" in text


def test_static_html_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.text
    assert "styles.css" in text
    assert "app.js" in text
    assert 'id="ticker"' in text
    assert 'id="btn-start"' in text
    assert 'id="btn-stop"' in text
    assert 'id="agent-grid"' in text
    assert 'id="report-tabs"' in text
    assert 'id="log"' in text
