"""FastAPI app for TradingAgents webapp.

Endpoints implemented here:
  GET /api/options
  GET /api/options/models

Runs/SSE/history/report/ohlcv endpoints are added by later cards.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from cli.utils import (
    ANALYST_ORDER,
    RESEARCH_DEPTH_OPTIONS,
    _llm_provider_table,
)
from tradingagents.llm_clients.model_catalog import get_model_options

_APP_PORT = 8765
_APP_HOST = "127.0.0.1"

app = FastAPI(title="TradingAgents Web")

# Mount static files if the directory exists (created by Card 04)
_static_dir = Path(__file__).with_suffix("").parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


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


def main() -> None:
    import uvicorn
    uvicorn.run("webapp.server:app", host=_APP_HOST, port=_APP_PORT, reload=False)


if __name__ == "__main__":
    main()
