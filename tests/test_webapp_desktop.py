"""Tests for webapp/desktop.py (Card 07)."""
import socket
from unittest.mock import MagicMock, patch

import pytest

import webapp.desktop as desktop


def test_is_port_in_use():
    # Bind and listen on a temporary port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        _, port = s.getsockname()
        assert desktop._is_port_in_use("127.0.0.1", port) is True

    # Port is now free
    assert desktop._is_port_in_use("127.0.0.1", port) is False


def test_wait_for_server_success():
    with patch("webapp.desktop.urllib.request.urlopen") as mock_urlopen:
        resp = MagicMock()
        resp.status = 200
        resp.__enter__ = lambda self: self
        resp.__exit__ = lambda *args: None
        mock_urlopen.return_value = resp
        desktop._wait_for_server("http://127.0.0.1:8765/api/options", timeout=1.0)
        mock_urlopen.assert_called()


def test_wait_for_server_timeout():
    with patch("webapp.desktop.urllib.request.urlopen", side_effect=Exception("fail")):
        with pytest.raises(RuntimeError, match="did not become ready"):
            desktop._wait_for_server("http://127.0.0.1:8765/api/options", timeout=0.3, interval=0.05)


def test_main_port_in_use(monkeypatch, capsys):
    monkeypatch.setattr(desktop, "_is_port_in_use", lambda h, p: True)
    with pytest.raises(SystemExit) as exc:
        desktop.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "already in use" in captured.out


def test_main_pywebview_missing(monkeypatch, capsys):
    monkeypatch.setattr(desktop, "_is_port_in_use", lambda h, p: False)
    monkeypatch.setattr(desktop, "_wait_for_server", lambda url, **kw: None)

    with patch.dict("sys.modules", {"webview": None}):
        with pytest.raises(SystemExit) as exc:
            desktop.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "pywebview is not installed" in captured.out
