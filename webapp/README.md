# TradingAgents local web workspace

The approved Apple-inspired interface is connected to the existing Python graph. The standalone `prototype/` remains available as a design reference. The real app is served from `webapp/static/`.

## Run

Use Python 3.10 or newer. Run the setup commands from the repository root.

### Linux / macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
./scripts/start-web.sh
```

To select another port, run `./scripts/start-web.sh --port 8767`. The launcher uses the repository's `.venv` and changes to the repository root, so it can also be invoked by absolute path from another directory. Server options such as `--data-dir` are forwarded unchanged; relative data paths are resolved from the repository root. Stop with Ctrl+C.

On Linux, if virtual environment creation reports that `ensurepip` is unavailable, install your distribution's Python venv package (for example, `python3-venv` on Debian/Ubuntu) and retry.

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\start-web.ps1
```

Open http://127.0.0.1:8766. Alternatively, activate the virtual environment (`. .venv/bin/activate` on Linux/macOS or `.\.venv\Scripts\Activate.ps1` on Windows) and run `python -m webapp.server --port 8766` or `tradingagents-web --port 8766`. Start these direct commands from this repository to load its `.env` files. Stop with Ctrl+C. The server binds exclusively to loopback and is intended for one local user; do not expose it through a reverse proxy or on a public network.

Choose a provider and real model IDs in **모델 및 설정** or the new-analysis form. Provider/model choices use the existing CLI table and model catalog. API credentials remain in server environment variables or `.env`; the browser receives only configuration-presence indicators, never key values. For Codex, use the existing `codex login` on the same OS account as the server and set both models to `default` or a model available to that account. Presence of the CLI is not proof of a valid subscription login. API-based providers require their corresponding environment variable listed in settings. Custom backend URLs remain server-side via `TRADINGAGENTS_LLM_BACKEND_URL` for the configured provider.

## Implemented behavior

- The web workspace defaults to Codex with CLI-default models; saved preferences remain available.
- Imported reports and interrupted, cancelled, or failed analyses can be removed from their detail view after confirmation. The record is moved into the local database's `trashed_jobs` table; original source files remain intact. Queued or running analyses cannot be deleted through this action.
- Glass surfaces and custom keyboard-accessible provider, model and depth menus. Model IDs remain editable. Codex mirrors the OpenAI model menu (including GPT-6 Astra), with an additional CLI-default choice; actual model access is determined by the selected provider/account.
- Yahoo Finance instrument search by name or ticker. Selecting a result saves its name and ticker together. Instrument labels in history, search and report headings show company/index names without tickers or trailing legal suffixes such as `Co., Ltd.` and `Inc.`. Tickers remain the internal identifier. Select a Yahoo result before submitting. Existing raw report captures stay unchanged.
- Company logos are loaded through the local server from Financial Modeling Prep, with initials when unavailable. Recognized country indices use flags; unrecognized indices use a globe.
- Candlestick charts are the default with a line-chart toggle and 1W/1M/3M/1Y ranges. New price records preserve a year of OHLC data. Hover shows a crosshair and a two-column price/volume tooltip with prices rounded to two decimals. Focus the chart and use arrow keys or Home/End to inspect bars; Escape dismisses the tooltip. Older close-only records show a labeled line-chart fallback; imported records without prices stay empty.
- The browser tab uses an embedded SVG chart favicon matching the app identity.
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

Local report folders with the same stage layout can also be imported. Stop the web server first, activate the virtual environment, then run:

```sh
python -m webapp.import_reports --local reports/ABCL_20260909_233053 reports/CRWV_20260826 reports/ORCL_20260826
```

Restart the server and open the history list. These records are labeled `Local reports`. Original Markdown bytes (including any usage metrics in the complete report) and SHA-256 hashes are preserved under each record's `source/` directory. Importing unchanged contents from the same path again adds no duplicate; changed contents create a separate record. No model or market-data calls are made.

Use an authorized local checkout with `raw/agent-reports/`. Stop the web server before running the importer:

With the virtual environment activated on any supported OS:

```sh
python -m webapp.import_reports .web-data/alpha-ledger
```

The importer reads per-agent Markdown and `complete_report.md`. It copies original bytes into each imported record's `source/` directory and records SHA-256 values plus a Git-commit-pinned source URL in `provenance.json`. Reimporting the same commit/folder is idempotent. The displayed rating is parsed from the original portfolio decision. Imported content is attributed to Alpha-Ledger, not represented as a newly executed analysis or independently verified market facts. The import does not fetch data or make model calls.

This workspace was seeded with nine report sets from commit `2757c2476d87648d97764fc080128a5b2deb532c`. The private/local report captures and database are not distributed with the application code.

## Verification

With the virtual environment activated:

```sh
python -m pytest tests/test_webapp.py tests/test_webapp_symbols.py tests/test_import_reports.py tests/test_codex_provider.py tests/test_cli_config_precedence.py tests/test_cli_symbol_handling.py -q
python -m ruff check webapp tests/test_webapp.py
node --check webapp/static/app.js
```

Tests use a controlled runner and never consume model usage. They cover callback finalization, input validation, job success/failure/cancellation, prevention of overlapping analyses, persistence/restart handling, export and the local HTTP security boundary. A user-authorized subscription-backed ORCL analysis completed on 2026-09-10 with Codex default models, the market analyst and one debate round. It persisted all selected-stage reports and a Hold signal. The first attempt exposed Windows subprocess decoding using cp949; Codex subprocess input/output now explicitly uses UTF-8, with a Unicode round-trip regression test.
