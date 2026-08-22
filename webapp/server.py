"""FastAPI app for TradingAgents webapp.

Endpoints implemented here:
  GET /api/options
  GET /api/options/models
  POST /api/runs
  GET /api/runs/{run_id}/events
  POST /api/runs/{run_id}/stop

History/report/ohlcv endpoints are added by later cards.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from cli.utils import (
    ANALYST_ORDER,
    RESEARCH_DEPTH_OPTIONS,
    _llm_provider_table,
)
from tradingagents.llm_clients.api_key_env import get_api_key_env
from tradingagents.llm_clients.model_catalog import get_model_options
from webapp.runner import RunHandle, RunRequest, start_run

_APP_PORT = 8765
_APP_HOST = "127.0.0.1"

app = FastAPI(title="TradingAgents Web")

# Mount static files if the directory exists (created by Card 04)
_static_dir = Path(__file__).with_suffix("").parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")

# Run storage: at most one active run at a time
_runs: dict[str, RunHandle] = {}
_active_run_id: str | None = None


def _api_key_error(provider: str) -> str | None:
    """Return error message if API key is missing for provider, else None."""
    env_var = get_api_key_env(provider)
    if env_var is None:
        return None  # provider doesn't need a key
    if os.environ.get(env_var):
        return None  # key is set

    # Key-optional providers (e.g. ollama, openai_compatible local servers)
    # are allowed to proceed without a key.
    from tradingagents.llm_clients.openai_client import OPENAI_COMPATIBLE_PROVIDERS
    spec = OPENAI_COMPATIBLE_PROVIDERS.get(provider.lower())
    if spec is not None and spec.key_optional:
        return None

    return f"{env_var} not set"


@app.exception_handler(StarletteHTTPException)
def _http_exception_handler(_request, exc):
    """HTTPException -> JSON {error: ...}."""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
def _generic_exception_handler(_request, exc):
    """All unhandled failures -> JSON {error: ...}."""
    status = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", str(exc))
    return JSONResponse(status_code=status, content={"error": detail})


@app.get("/api/options")
def get_options():
    """Return static option lists for the frontend form."""
    providers = [
        {"name": name, "key": key, "default_url": url}
        for name, key, url in _llm_provider_table()
    ]
    analysts = [
        {"key": atype.value, "label": label}
        for label, atype in ANALYST_ORDER
    ]
    research_depth = [
        {"label": label, "value": value}
        for label, value in RESEARCH_DEPTH_OPTIONS
    ]
    return {
        "providers": providers,
        "analysts": analysts,
        "research_depth": research_depth,
        "asset_types": ["stock", "crypto"],
    }


@app.get("/api/options/models")
def get_model_options_endpoint(
    provider: str = Query(...),
    mode: str = Query(...),
):
    """Return model dropdown options for a provider + mode (quick/deep)."""
    mode = mode.lower()
    if mode not in ("quick", "deep"):
        raise HTTPException(status_code=400, detail="mode must be 'quick' or 'deep'")

    try:
        options = get_model_options(provider, mode)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"unknown provider: {provider}")

    return [{"label": label, "value": value} for label, value in options]


@app.post("/api/runs")
async def create_run(request: Request):
    """Start a new analysis run."""
    global _active_run_id

    body = await request.json()

    # Validate required fields
    required = [
        "ticker", "analysis_date", "analysts", "research_depth",
        "llm_provider", "backend_url", "shallow_thinker", "deep_thinker",
    ]
    missing = [f for f in required if f not in body]
    if missing:
        raise HTTPException(status_code=400, detail=f"missing fields: {', '.join(missing)}")

    provider = body["llm_provider"]

    # API key check
    key_err = _api_key_error(provider)
    if key_err:
        raise HTTPException(status_code=400, detail=key_err)

    # Concurrent run limit
    if _active_run_id is not None and _active_run_id in _runs:
        handle = _runs[_active_run_id]
        if handle.thread.is_alive():
            raise HTTPException(status_code=409, detail="run already in progress")

    req = RunRequest(
        ticker=body["ticker"],
        analysis_date=body["analysis_date"],
        analysts=body["analysts"],
        research_depth=body["research_depth"],
        llm_provider=provider,
        backend_url=body["backend_url"],
        shallow_thinker=body["shallow_thinker"],
        deep_thinker=body["deep_thinker"],
        output_language=body.get("output_language", "English"),
    )

    handle = start_run(req)
    _runs[handle.run_id] = handle
    _active_run_id = handle.run_id

    return JSONResponse(status_code=202, content={"run_id": handle.run_id})


def _event_stream(handle: RunHandle):
    """Generator that yields SSE formatted events from the run's queue."""
    while True:
        try:
            event = handle.events.get(timeout=1.0)
        except Exception:
            # Timeout or queue empty — check if thread is still alive
            if not handle.thread.is_alive() and handle.events.empty():
                break
            continue

        import json
        yield f"data: {json.dumps(event)}\n\n"

        if event.get("type") == "done":
            break


@app.get("/api/runs/{run_id}/events")
def get_run_events(run_id: str):
    """SSE stream of run events."""
    handle = _runs.get(run_id)
    if handle is None:
        raise HTTPException(status_code=404, detail="run not found")

    return StreamingResponse(
        _event_stream(handle),
        media_type="text/event-stream",
    )


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str):
    """Signal a running run to stop."""
    handle = _runs.get(run_id)
    if handle is None:
        raise HTTPException(status_code=404, detail="run not found")

    handle.stop_event.set()
    return {"ok": True}


def main() -> None:
    import uvicorn
    uvicorn.run("webapp.server:app", host=_APP_HOST, port=_APP_PORT, reload=False)


if __name__ == "__main__":
    main()
