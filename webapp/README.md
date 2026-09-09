# TradingAgents local web workspace

The approved Apple-inspired interface is connected to the existing Python graph. The standalone `prototype/` remains available as a design reference. The real app is served from `webapp/static/`.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\start-web.ps1
```

Open http://127.0.0.1:8766. Alternatively run `.\.venv\Scripts\python.exe -m webapp.server --port 8766`. Start from this repository to load its `.env` files. Stop with Ctrl+C. The server binds exclusively to loopback and is intended for one local user; do not expose it through a reverse proxy or on a public network.

Choose a provider and real model IDs in **모델 및 설정** or the new-analysis form. Provider/model choices use the existing CLI table and model catalog. API credentials remain in server environment variables or `.env`; the browser receives only configuration-presence indicators, never key values. For Codex, use the existing `codex login` on the same OS account as the server and set both models to `default` or a model available to that account. Presence of the CLI is not proof of a valid subscription login. API-based providers require their corresponding environment variable listed in settings. Custom backend URLs remain server-side via `TRADINGAGENTS_LLM_BACKEND_URL` for the configured provider.

## Implemented behavior

- Validated symbol, non-future analysis date, selected analysts, provider, model IDs, and debate depth.
- Real `TradingAgentsGraph.propagate` execution, with completed-node state delivered through a new optional callback. Existing CLI callers retain their previous behavior.
- Two-second polling for reports, stage progress, status, and elapsed time. Reloading reconnects to the active job. No simulated prices or ratings in the live app.
- Real historical Yahoo Finance bars at or before the selected date; unavailable prices remain missing. Imported reports are displayed without inventing a time series.
- Persistent SQLite history and default model settings under `.web-data/` (gitignored). Each run has isolated data cache, memory and output/report directories. Runs do not share prior memory with CLI runs.
- Single active analysis avoids the engine's global data-provider configuration leaking across jobs.
- Cooperative cancellation: the current model/data call must finish before the next graph state callback can stop execution. Partial reports remain viewable. Server interruption is marked on restart. Retry starts a fresh job; checkpoint resume is not implemented in this web version.
- All five existing ratings (Buy, Overweight, Hold, Underweight, Sell), plus REVIEW for unparseable decisions. No invented confidence/risk score and no brokerage order execution.
- Safe report presentation using text DOM nodes (headings, emphasis and tables); raw HTML and links in generated reports are not executed. Original text remains in the download and source capture.
- Loopback Host validation, origin checks and per-server request token for mutations; explicit static asset allowlist; CSP. Provider exception strings are withheld because they may contain secrets.

## Import Alpha-Ledger reports

Use an authorized local checkout with `raw/agent-reports/`. Stop the web server before running the importer:

```powershell
.\.venv\Scripts\python.exe -m webapp.import_reports .web-data/alpha-ledger
```

The importer reads per-agent Markdown and `complete_report.md`. It copies original bytes into each imported record's `source/` directory and records SHA-256 values plus a Git-commit-pinned source URL in `provenance.json`. Reimporting the same commit/folder is idempotent. The displayed rating is parsed from the original portfolio decision. Imported content is attributed to Alpha-Ledger, not represented as a newly executed analysis or independently verified market facts. The import does not fetch data or make model calls.

This workspace was seeded with nine report sets from commit `2757c2476d87648d97764fc080128a5b2deb532c`. The private/local report captures and database are not distributed with the application code.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_webapp.py tests/test_cli_config_precedence.py tests/test_cli_symbol_handling.py -q
.\.venv\Scripts\python.exe -m ruff check webapp tests/test_webapp.py
node --check webapp/static/app.js
```

Tests use a controlled runner and never consume model usage. They cover callback finalization, input validation, job success/failure/cancellation, prevention of overlapping analyses, persistence/restart handling, export and the local HTTP security boundary. A user-authorized subscription-backed ORCL analysis completed on 2026-09-10 with Codex default models, the market analyst and one debate round. It persisted all selected-stage reports and a Hold signal. The first attempt exposed Windows subprocess decoding using cp949; Codex subprocess input/output now explicitly uses UTF-8, with a Unicode round-trip regression test.
