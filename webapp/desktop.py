"""Desktop entry point: python -m webapp.desktop

Starts the FastAPI server in a background thread, waits for readiness,
then opens a pywebview window pointing at the local server.
"""

from __future__ import annotations

import socket
import threading
import time
import urllib.request

import uvicorn

from webapp.server import _APP_HOST, _APP_PORT, app


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def _wait_for_server(url: str, *, timeout: float = 10.0, interval: float = 0.2) -> None:
    """Poll url until it returns HTTP 200 or timeout expires."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(interval)
    raise RuntimeError(f"Server did not become ready within {timeout}s")


def _run_server(host: str, port: int) -> None:
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main() -> None:
    host = _APP_HOST
    port = _APP_PORT

    if _is_port_in_use(host, port):
        print(f"Error: Port {port} is already in use on {host}.")
        print("Another instance of TradingAgents webapp may be running.")
        raise SystemExit(1)

    server_thread = threading.Thread(
        target=_run_server,
        args=(host, port),
        daemon=True,
    )
    server_thread.start()

    try:
        _wait_for_server(f"http://{host}:{port}/api/options")
    except RuntimeError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)

    try:
        import webview
    except ImportError:
        print("Error: pywebview is not installed. Install with: pip install pywebview")
        raise SystemExit(1)

    webview.create_window("TradingAgents", f"http://{host}:{port}/")
    webview.start()


if __name__ == "__main__":
    main()
