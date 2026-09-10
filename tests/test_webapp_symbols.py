import json
from types import SimpleNamespace

import pytest

from webapp.service import (
    catalog,
    company_logo,
    display_name,
    markdown,
    search_symbols,
    validate_request,
)


def test_search_returns_name_ticker_and_exchange(monkeypatch):
    import yfinance as yf

    def search(query, **kwargs):
        assert query == "Nikkei 225"
        assert kwargs["news_count"] == 0
        return SimpleNamespace(quotes=[
            {"symbol": "^N225", "longname": "Nikkei 225", "exchDisp": "Osaka", "quoteType": "INDEX"},
            {"symbol": "../bad", "shortname": "Bad"},
        ])
    monkeypatch.setattr(yf, "Search", search)
    assert search_symbols("Nikkei 225") == [
        {"symbol": "^N225", "name": "Nikkei 225", "exchange": "Osaka", "type": "INDEX"}
    ]


def test_selected_name_survives_validation_and_report_export():
    config = validate_request({
        "symbol": "^N225", "symbolName": "Nikkei 225", "date": "2026-08-26",
        "provider": "codex", "analysts": ["market"], "depth": 1,
        "quickModel": "gpt-6-astra", "deepModel": "gpt-6-astra",
    }, {"codex"})
    job = {"config": json.loads(json.dumps(config)), "status": "completed", "reports": {}}
    assert markdown(job).startswith("# Nikkei 225 · 2026-08-26")
    config.pop("symbolName")
    job["config"] = config
    assert markdown(job).startswith("# 종목 · 2026-08-26")
    job["config"] = {**config, "symbol": "ORCL", "symbolName": "Oracle Corporation"}
    assert markdown(job).startswith("# Oracle · 2026-08-26")
    with pytest.raises(ValueError):
        validate_request({**config, "symbolName": "Injected\nheading"}, {"codex"})


def test_search_retains_share_class_without_ticker_in_name(monkeypatch):
    import yfinance as yf

    monkeypatch.setattr(yf, "Search", lambda *args, **kwargs: SimpleNamespace(quotes=[
        {"symbol": "005935.KS", "longname": "Samsung Electronics Co., Ltd.",
         "shortname": "SamsungElec(1P)", "quoteType": "EQUITY"},
    ]))
    result = search_symbols("Samsung")[0]
    assert result["name"] == "Samsung Electronics (1P)"
    assert result["symbol"] == "005935.KS"


@pytest.mark.parametrize("name,expected", [
    ("Samsung Electronics Co., Ltd.", "Samsung Electronics"),
    ("AbCellera Biologics Inc.", "AbCellera Biologics"),
    ("CoreWeave, Inc.", "CoreWeave"),
    ("Oracle Corporation", "Oracle"),
    ("Nikkei 225", "Nikkei 225"),
])
def test_display_names_remove_legal_suffixes(name, expected):
    assert display_name({"symbolName": name, "symbol": "INTERNAL"}) == expected


def test_web_defaults_to_codex():
    assert catalog()["defaults"] == {"provider": "codex", "quickModel": "default", "deepModel": "default"}


def test_logo_uses_fixed_host_and_rejects_non_png(monkeypatch):
    import requests

    calls = []
    raw = b"\x89PNG\r\n\x1a\nfixture"
    def get(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(raise_for_status=lambda: None, content=raw)
    monkeypatch.setattr(requests, "get", get)
    company_logo.cache_clear()
    try:
        assert company_logo("../secret") is None
        assert not calls
        assert company_logo("ABCL") == raw
        assert company_logo("ABCL") == raw
        assert calls == ["https://financialmodelingprep.com/image-stock/ABCL.png"]
        raw = b"<html>not a logo</html>"
        assert company_logo("ORCL") is None
    finally:
        company_logo.cache_clear()
