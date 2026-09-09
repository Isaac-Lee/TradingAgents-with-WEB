"""Persistent local research jobs. Only one graph runs at a time (global data config)."""

from __future__ import annotations

import copy
import json
import re
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

REPORT_FIELDS = (
    "market_report",
    "fundamentals_report",
    "news_report",
    "sentiment_report",
    "investment_plan",
    "trader_investment_plan",
    "final_trade_decision",
    "investment_debate_state",
    "risk_debate_state",
    "analysis_stats",
    "market_data",
    "original_report",
)
ACTIVE = {"queued", "running", "cancelling"}


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_request(data, providers):
    if not isinstance(data, dict):
        raise ValueError("설정은 JSON 객체여야 합니다.")
    symbol = str(data.get("symbol", "")).strip().upper()
    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9._=^-]{0,31}", symbol) or ".." in symbol:
        raise ValueError("올바른 종목 코드를 입력하세요. 예: NVDA, 005930.KS, BTC-USD")
    try:
        day = date.fromisoformat(data.get("date", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("분석 기준일을 확인하세요.") from exc
    if day > date.today():
        raise ValueError("미래 날짜는 분석할 수 없습니다.")
    provider = data.get("provider")
    if provider not in providers:
        raise ValueError("지원하지 않는 모델 제공자입니다.")
    analysts = data.get("analysts")
    if (
        not isinstance(analysts, list)
        or not analysts
        or any(a not in {"market", "fundamentals", "news", "sentiment"} for a in analysts)
        or len(set(analysts)) != len(analysts)
    ):
        raise ValueError("분석가를 한 명 이상 선택하세요. 중복은 허용되지 않습니다.")
    depth = data.get("depth", 1)
    if type(depth) is not int or depth not in (1, 3, 5):
        raise ValueError("토론 깊이는 1, 3, 5 중 하나여야 합니다.")
    if symbol.endswith(("-USD", "-USDT", "-USDC", "-BTC", "-ETH")) and "fundamentals" in analysts:
        raise ValueError("암호화폐에는 주식 재무제표 분석가를 선택할 수 없습니다.")
    result = {
        "symbol": symbol,
        "date": day.isoformat(),
        "provider": provider,
        "analysts": analysts,
        "depth": depth,
    }
    for key in ("quickModel", "deepModel"):
        model = data.get(key, "")
        if (
            not isinstance(model, str)
            or not re.fullmatch(r"[\w./:@+ -]{1,160}", model)
            or model == "custom"
        ):
            raise ValueError("빠른 분석 모델과 심층 추론 모델의 실제 ID를 입력하세요.")
        result[key] = model.strip()
        if not result[key]:
            raise ValueError("모델 이름을 입력하세요.")
    return result


def stage_for(state):
    if state.get("final_trade_decision"):
        return 4
    if state.get("risk_debate_state", {}).get("history"):
        return 3
    if state.get("trader_investment_plan"):
        return 3
    if state.get("investment_plan"):
        return 2
    if state.get("investment_debate_state", {}).get("history"):
        return 1
    return 0


class Cancelled(Exception):
    pass


class JobStore:
    def __init__(self, root, runner=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / "workspace.sqlite3", check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )
        self.db.commit()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="research")
        self.runner = runner or run_graph
        for job in self.list():
            if job["status"] in ACTIVE:
                self.update(
                    job["id"],
                    status="interrupted",
                    error="서버가 종료되어 중단되었습니다. 다시 실행할 수 있습니다.",
                    finished=now(),
                )

    def get(self, job_id):
        with self.lock:
            row = self.db.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise KeyError(job_id)
            return json.loads(row[0])

    def list(self):
        with self.lock:
            return [
                json.loads(row[0])
                for row in self.db.execute("SELECT body FROM jobs ORDER BY rowid DESC")
            ]

    def save(self, job):
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?, ?)",
                (job["id"], json.dumps(job, ensure_ascii=False)),
            )
            self.db.commit()
        return job

    def update(self, job_id, **changes):
        with self.lock:
            job = self.get(job_id)
            job.update(changes, updated=now())
            return self.save(job)

    def preferences(self, value=None):
        with self.lock:
            if value is not None:
                self.db.execute(
                    "INSERT OR REPLACE INTO preferences VALUES (1, ?)", (json.dumps(value),)
                )
                self.db.commit()
            row = self.db.execute("SELECT body FROM preferences WHERE id=1").fetchone()
            return json.loads(row[0]) if row else None

    def submit(self, config):
        with self.lock:
            if any(j["status"] in ACTIVE for j in self.list()):
                raise ValueError(
                    "현재 분석이 진행 중입니다. 완료하거나 중지한 후 새 분석을 시작하세요."
                )
            job = {
                "id": uuid.uuid4().hex,
                "config": config,
                "status": "queued",
                "stage": 0,
                "created": now(),
                "updated": now(),
                "reports": {},
                "signal": None,
                "error": None,
                "events": [],
                "source": None,
            }
            self.save(job)
            self.executor.submit(self._execute, job["id"])
            return job

    def cancel(self, job_id):
        with self.lock:
            job = self.get(job_id)
            if job["status"] not in ACTIVE:
                raise ValueError("진행 중인 분석만 중지할 수 있습니다.")
            return self.update(job_id, status="cancelling")

    def _execute(self, job_id):
        try:
            with self.lock:
                if self.get(job_id)["status"] == "cancelling":
                    raise Cancelled()
                self.update(job_id, status="running", started=now())

            def progress(state):
                with self.lock:
                    job = self.get(job_id)
                    if job["status"] == "cancelling":
                        raise Cancelled()
                    reports = {
                        **job["reports"],
                        **{k: copy.deepcopy(state[k]) for k in REPORT_FIELDS if k in state},
                    }
                    stage = stage_for(state)
                    events = job["events"]
                    changed = [k for k, v in reports.items() if v and v != job["reports"].get(k)]
                    if changed:
                        events.append({"time": now(), "stage": stage, "fields": changed})
                    self.update(job_id, stage=stage, reports=reports, events=events[-100:])

            state, signal = self.runner(self.get(job_id)["config"], self.root / job_id, progress)
            progress(state)
            with self.lock:
                if self.get(job_id)["status"] == "cancelling":
                    raise Cancelled()
                self.update(job_id, status="completed", stage=5, signal=signal, finished=now())
        except Cancelled:
            self.update(job_id, status="cancelled", finished=now())
        except Exception as exc:
            # Never return raw provider errors: SDK messages may embed credentials/URLs.
            message = "분석 실행에 실패했습니다. 서버의 제공자 인증, 모델 ID와 데이터 연결을 확인한 뒤 다시 실행하세요."
            if isinstance(exc, ImportError):
                message = (
                    "분석 의존성이 없습니다. 프로젝트 환경에서 pip install -e . 를 실행하세요."
                )
            self.update(
                job_id, status="failed", error=f"{message} ({type(exc).__name__})", finished=now()
            )

    def close(self):
        self.executor.shutdown(wait=True)
        self.db.close()


def run_graph(request, root, progress):
    from cli.utils import detect_asset_type, provider_default_url
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    progress({"market_data": market_data(request["symbol"], request["date"])})

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update(
        llm_provider=request["provider"],
        quick_think_llm=request["quickModel"],
        deep_think_llm=request["deepModel"],
        output_language="Korean",
        max_debate_rounds=request["depth"],
        max_risk_discuss_rounds=request["depth"],
        results_dir=str(root / "results"),
        data_cache_dir=str(root / "cache"),
        memory_log_path=str(root / "memory.md"),
        checkpoint_enabled=False,
    )
    config["backend_url"] = (
        DEFAULT_CONFIG.get("backend_url")
        if request["provider"] == DEFAULT_CONFIG["llm_provider"]
        else None
    ) or provider_default_url(request["provider"])
    analysts = ["social" if a == "sentiment" else a for a in request["analysts"]]
    graph = TradingAgentsGraph(selected_analysts=analysts, config=config)
    state, signal = graph.propagate(
        request["symbol"],
        request["date"],
        asset_type=detect_asset_type(request["symbol"]).value,
        progress_callback=progress,
    )
    graph.save_reports(state, request["symbol"], root / "reports")
    return state, signal


def market_data(symbol, day):
    """Only actual dated bars. Failure is missing data, never synthetic quotes."""
    import math
    from datetime import timedelta

    import yfinance as yf

    try:
        end = date.fromisoformat(day)
        ticker = yf.Ticker(symbol)
        frame = ticker.history(
            start=(end - timedelta(days=100)).isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            auto_adjust=False,
            timeout=15,
        )
        bars = []
        for stamp, row in frame.iterrows():
            close = float(row["Close"])
            if stamp.date() <= end and math.isfinite(close):
                bars.append(
                    {
                        "date": stamp.date().isoformat(),
                        "close": close,
                        "volume": int(row["Volume"])
                        if math.isfinite(float(row["Volume"]))
                        else None,
                    }
                )
        return {
            "bars": bars,
            "source": "Yahoo Finance",
            "currency": ticker.history_metadata.get("currency", ""),
        }
    except Exception:
        return {
            "bars": [],
            "source": "Yahoo Finance",
            "error": "가격 데이터를 가져오지 못했습니다.",
        }


def catalog():
    import os
    import shutil

    from cli.utils import _llm_provider_table
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.llm_clients.api_key_env import get_api_key_env
    from tradingagents.llm_clients.model_catalog import get_model_options

    providers = []
    for label, key, _url in _llm_provider_table():
        env = get_api_key_env(key)
        configured = bool(os.environ.get(env)) if env else None
        if key == "codex":
            configured = bool(shutil.which(DEFAULT_CONFIG.get("codex_command", "codex")))
        if key == "openai_compatible":
            configured = None  # Keys are optional for local compatible servers.
        try:
            quick, deep = get_model_options(key, "quick"), get_model_options(key, "deep")
        except KeyError:
            quick = deep = [("Custom model ID", "custom")]
        providers.append(
            {
                "id": key,
                "label": label,
                "configured": configured,
                "key_env": env,
                "quick": quick,
                "deep": deep,
            }
        )
    return {
        "providers": providers,
        "defaults": {
            "provider": DEFAULT_CONFIG["llm_provider"],
            "quickModel": DEFAULT_CONFIG["quick_think_llm"],
            "deepModel": DEFAULT_CONFIG["deep_think_llm"],
        },
        "today": date.today().isoformat(),
    }


def markdown(job):
    cfg = job["config"]
    lines = [
        f"# {cfg['symbol']} · {cfg['date']}",
        f"Status: {job['status']}",
        f"Provider: {cfg['provider']}",
        f"Signal: {job.get('signal') or 'Unavailable'}",
    ]
    if job.get("source"):
        lines.append(f"Source: {job['source']}")
    for key, value in job["reports"].items():
        if value:
            text = (
                value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
            )
            lines.append(f"## {key}\n\n{text}")
    return "\n\n".join(lines)
