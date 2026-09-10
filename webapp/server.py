"""Loopback-only HTTP API and bundled frontend. Run: python -m webapp.server."""

from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .service import JobStore, catalog, company_logo, markdown, search_symbols, validate_request

STATIC = Path(__file__).parent / "static"


def make_server(port, store, catalog_fn=catalog):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Avoid writing report text or input data to the console.

        def respond(self, status, body, content_type="application/json; charset=utf-8", extra=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            for key, value in {
                "Content-Type": content_type,
                "Content-Length": str(len(body)),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'",
                **(extra or {}),
            }.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") in {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }

        def do_GET(self):
            if not self.valid_host():
                return self.respond(403, {"error": "Local host only"})
            path = urlsplit(self.path).path
            try:
                if path == "/api/bootstrap":
                    return self.respond(
                        200, {**catalog_fn(), "token": token, "preferences": store.preferences()}
                    )
                if path == "/api/symbols":
                    query = parse_qs(urlsplit(self.path).query).get("q", [""])[0].strip()
                    if not query or len(query) > 100 or any(ord(c) < 32 for c in query):
                        return self.respond(400, {"error": "종목명 또는 티커를 입력하세요."})
                    return self.respond(200, {"results": search_symbols(query)})
                if path == "/api/logo":
                    symbol = parse_qs(urlsplit(self.path).query).get("symbol", [""])[0].upper()
                    raw = company_logo(symbol)
                    if raw is None:
                        return self.respond(404, {"error": "로고 없음"}, extra={"Cache-Control": "private, max-age=3600"})
                    return self.respond(200, raw, "image/png", {"Cache-Control": "private, max-age=86400"})
                if path == "/api/jobs":
                    return self.respond(
                        200,
                        [
                            {k: v for k, v in j.items() if k not in {"reports", "events"}}
                            for j in store.list()
                        ],
                    )
                parts = path.strip("/").split("/")
                if len(parts) in (3, 4) and parts[:2] == ["api", "jobs"]:
                    job = store.get(parts[2])
                    if len(parts) == 3:
                        return self.respond(200, job)
                    if parts[3] == "report":
                        return self.respond(
                            200,
                            markdown(job),
                            "text/markdown; charset=utf-8",
                            {
                                "Content-Disposition": f'attachment; filename="research-{job["id"]}.md"'
                            },
                        )
                filename = "index.html" if path == "/" else path.removeprefix("/")
                # Explicit assets only: never serve workspace, .env, database, or paths.
                if filename not in {"index.html", "style.css", "apple.css", "live.css", "app.js"}:
                    return self.respond(404, {"error": "Not found"})
                file = STATIC / filename
                return self.respond(
                    200,
                    file.read_bytes(),
                    (mimetypes.guess_type(file.name)[0] or "text/plain") + "; charset=utf-8",
                )
            except KeyError:
                self.respond(404, {"error": "분석을 찾을 수 없습니다."})
            except Exception:
                self.respond(
                    503,
                    {
                        "error": "서버 설정을 읽을 수 없습니다. 의존성 설치와 환경 설정을 확인하세요."
                    },
                )

        def do_POST(self):
            # Consume a bounded request body before replying, including rejected
            # requests. Closing with unread bytes can reset the socket on Windows
            # and discard the intended HTTP error response.
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self.respond(400, {"error": "Invalid JSON request"})
            if not 0 < length <= 16384 or self.headers.get("Transfer-Encoding"):
                return self.respond(400, {"error": "Invalid JSON request"})
            self.connection.settimeout(10)
            try:
                raw_body = self.rfile.read(length)
            except TimeoutError:
                return self.respond(408, {"error": "Request body timed out"})
            origin = self.headers.get("Origin")
            allowed = {
                f"http://127.0.0.1:{self.server.server_port}",
                f"http://localhost:{self.server.server_port}",
            }
            if (
                not self.valid_host()
                or (origin and origin not in allowed)
                or not secrets.compare_digest(self.headers.get("X-Workspace-Token", ""), token)
            ):
                return self.respond(
                    403, {"error": "요청 인증에 실패했습니다. 화면을 새로고침하세요."}
                )
            try:
                if (
                    self.headers.get("Content-Type", "").split(";")[0] != "application/json"
                ):
                    return self.respond(400, {"error": "Invalid JSON request"})
                data = json.loads(raw_body)
                path = urlsplit(self.path).path
                if path in {"/api/jobs", "/api/preferences"}:
                    options = catalog_fn()
                    config = validate_request(data, {p["id"] for p in options["providers"]})
                    if path == "/api/preferences":
                        store.preferences(config)
                        return self.respond(200, config)
                    selected = next(
                        p for p in options["providers"] if p["id"] == config["provider"]
                    )
                    if selected.get("configured") is False:
                        raise ValueError(
                            "선택한 제공자의 서버 인증 설정이 없습니다. 모델 및 설정을 확인하세요."
                        )
                    return self.respond(201, store.submit(config))
                parts = path.strip("/").split("/")
                if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "cancel":
                    return self.respond(200, store.cancel(parts[2]))
                if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "delete":
                    try:
                        return self.respond(200, store.delete_report(parts[2]))
                    except ValueError:
                        return self.respond(400, {"error": "가져온 보고서 또는 중단·실패한 분석만 삭제할 수 있습니다. 실행 중인 분석은 먼저 중지하세요."})
                self.respond(404, {"error": "Not found"})
            except (ValueError, TypeError):
                self.respond(
                    400,
                    {
                        "error": "입력값 또는 실행 상태를 확인하세요. 종목, 날짜, 모델 ID와 서버 인증 설정이 필요합니다."
                    },
                )
            except KeyError:
                self.respond(404, {"error": "분석을 찾을 수 없습니다."})
            except Exception:
                self.respond(500, {"error": "요청을 처리할 수 없습니다."})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", type=Path, default=Path(".web-data"))
    args = parser.parse_args()
    store = JobStore(args.data_dir)
    server = make_server(args.port, store)
    print(f"TradingAgents web: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        for job in store.list():
            if job["status"] in {"queued", "running"}:
                store.cancel(job["id"])
        store.close()


if __name__ == "__main__":
    main()
