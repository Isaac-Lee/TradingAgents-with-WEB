<p align="center">
  <img src="assets/TauricResearch.png" style="width: 60%; height: auto;">
</p>

<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2412.20138" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv"/></a>
  <a href="https://discord.com/invite/hk9PGKShPK" target="_blank"><img alt="Discord" src="https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da"/></a>
  <a href="https://x.com/TauricResearch" target="_blank"><img alt="X Follow" src="https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white"/></a>
  <a href="https://github.com/TauricResearch/" target="_blank"><img alt="Community" src="https://img.shields.io/badge/GitHub_Community-TauricResearch-14C290?logo=discourse"/></a>
</div>
<br>
<div align="center">
  <a href="https://github.com/TauricResearch" target="_blank"><img alt="TradingAgents #1 Repository of the Day" src="https://trendshift.io/api/badge/repositories/16192" width="250" height="55"/></a>
</div>
<br>
<div align="center">
  <!-- Keep these links. Translations will automatically update with the README. -->
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=de">Deutsch</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=es">Español</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=fr">français</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ja">日本語</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ko">한국어</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=pt">Português</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ru">Русский</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=zh">中文</a>
</div>

---

# TradingAgents: Multi-Agents LLM Financial Trading Framework

## News
- [2026-08] **TradingAgents v0.4.0** released with look-ahead / point-in-time fixes across FRED macro, social sentiment, and the decision-log memory; clearer decision signals; working CLI checkpoint resume; Trader price grounding; and the GPT-5.6 and GLM-5.3 models. See [CHANGELOG.md](CHANGELOG.md) for the full list.
- [2026-07] **TradingAgents v0.3.1** released with correctness and stability fixes: Alpha Vantage look-ahead filtering, graph-router crash-safety, graph-shape-aware checkpoint resume, working crypto sentiment sources, a configurable LLM retry budget, Bedrock API-key auth, and Claude Sonnet 5 / Fable 5 support.
- [2026-06] **TradingAgents v0.3.0** released with a verified data-access contract, an expanded provider registry (NVIDIA, Kimi, Groq, Mistral, Bedrock, and any OpenAI-compatible endpoint), FRED and Polymarket data vendors, a current-generation model catalog, and a CI gate.
- [2026-05] **TradingAgents v0.2.5** released with the grounded Sentiment Analyst, GPT-5.5 etc. model coverage, Qwen/GLM/MiniMax dual-region support, `TRADINGAGENTS_*` env-var configurability with API-key auto-detection, remote Ollama support, non-US alpha benchmarks, and ticker path-traversal hardening.
- [2026-04] **TradingAgents v0.2.4** released with structured-output agents (Research Manager, Trader, Portfolio Manager), LangGraph checkpoint resume, persistent decision log, DeepSeek/Qwen/GLM/Azure provider support, Docker, and a Windows UTF-8 encoding fix.
- [2026-03] **TradingAgents v0.2.3** released with multi-language support, GPT-5.4 family models, unified model catalog, backtesting date fidelity, and proxy support.
- [2026-03] **TradingAgents v0.2.2** released with GPT-5.4/Gemini 3.1/Claude 4.6 model coverage, five-tier rating scale, OpenAI Responses API, Anthropic effort control, and cross-platform stability.
- [2026-02] **TradingAgents v0.2.0** released with multi-provider LLM support (GPT-5.x, Gemini 3.x, Claude 4.x, Grok 4.x) and improved system architecture.
- [2026-01] **Trading-R1** [Technical Report](https://arxiv.org/abs/2509.11420) released, with [Terminal](https://github.com/TauricResearch/Trading-R1) expected to land soon.

<div align="center">

🚀 [TradingAgents](#tradingagents-framework) | ⚡ [Installation & CLI](#installation-and-cli) | 🎬 [Demo](https://www.youtube.com/watch?v=90gr5lwjIho) | 📦 [Package Usage](#tradingagents-package) | 🤝 [Contributing](#contributing) | 📄 [Citation](#citation)

</div>

> 🎉 **TradingAgents** officially released! We have received numerous inquiries about the work, and we would like to express our thanks for the enthusiasm in our community.
>
> So we decided to fully open-source the framework. Looking forward to building impactful projects with you!

## TradingAgents Framework

TradingAgents is a multi-agent trading framework that mirrors the dynamics of real-world trading firms. By deploying specialized LLM-powered agents: from fundamental analysts, sentiment experts, and technical analysts, to trader, risk management team, the platform collaboratively evaluates market conditions and informs trading decisions. Moreover, these agents engage in dynamic discussions to pinpoint the optimal strategy.

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>

> TradingAgents framework is designed for research purposes. Trading performance may vary based on many factors, including the chosen backbone language models, model temperature, trading periods, the quality of data, and other non-deterministic factors. [It is not intended as financial, investment, or trading advice.](https://tauric.ai/disclaimer/)

Our framework decomposes complex trading tasks into specialized roles.

### Analyst Team
- Fundamentals Analyst: Evaluates company financials and performance metrics, identifying intrinsic values and potential red flags.
- Sentiment Analyst: Aggregates news headlines, StockTwits, and Reddit chatter into a single sentiment read to gauge short-term market mood.
- News Analyst: Monitors global news and macroeconomic indicators, interpreting the impact of events on market conditions.
- Technical Analyst: Utilizes technical indicators (like MACD and RSI) to detect trading patterns and forecast price movements.

<p align="center">
  <img src="assets/analyst.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

### Researcher Team
- Comprises both bullish and bearish researchers who critically assess the insights provided by the Analyst Team. Through structured debates, they balance potential gains against inherent risks.

<p align="center">
  <img src="assets/researcher.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Trader Agent
- Composes reports from the analysts and researchers to make informed trading decisions, determining the timing and magnitude of trades.

<p align="center">
  <img src="assets/trader.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Risk Management and Portfolio Manager
- Continuously evaluates portfolio risk by assessing market volatility, liquidity, and other risk factors. The risk management team evaluates and adjusts trading strategies, providing assessment reports to the Portfolio Manager for final decision.
- The Portfolio Manager approves/rejects the transaction proposal. If approved, the order will be sent to the simulated exchange and executed.

<p align="center">
  <img src="assets/risk.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

## Installation and CLI

### Local web interface · 웹 사용 매뉴얼

웹 화면에서 기존 Python 분석 엔진을 실행하고, 단계별 보고서와 분석 기록을 확인할 수 있습니다. 아래는 Windows PowerShell 기준입니다. 웹은 리서치 보고서를 생성하며 실제 매매 주문을 실행하지 않습니다.

#### 1. 설치와 서버 실행

처음 설치하는 경우 Python 3.12 환경에서 다음 명령을 실행합니다. 이미 저장소가 있다면 해당 폴더에서 가상환경 설치 단계부터 진행하세요.

```powershell
git clone https://github.com/Isaac-Lee/TradingAgents-with-WEB.git
cd TradingAgents-with-WEB
git checkout codex/web-interface
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\scripts\start-web.ps1
```

브라우저에서 [웹 열기](http://127.0.0.1:8766)를 선택합니다. 이후에는 저장소 폴더에서 `.\scripts\start-web.ps1`만 실행하면 됩니다. PowerShell 스크립트 실행이 제한된 환경에서는 다음 명령을 사용하세요.

```powershell
.\.venv\Scripts\python.exe -m webapp.server --port 8766
```

다른 운영체제에서는 가상환경을 활성화하고 `python -m pip install -e .`, `python -m webapp.server --port 8766`을 실행합니다. 포트가 이미 사용 중이면 `--port 8767`로 변경하고 브라우저에서도 같은 포트로 접속합니다. 서버는 로컬 컴퓨터 전용으로, 실행한 터미널을 유지해야 합니다. 종료는 터미널에서 `Ctrl+C`를 누릅니다.

#### 2. 제공자와 모델 설정

**모델 및 설정**에서 LLM 제공자, 빠른 분석 모델, 심층 추론 모델을 선택하고 **설정 적용**을 누르면 새 분석의 기본값으로 저장됩니다.

- **Codex 구독 로그인 사용:** 서버를 실행하는 동일한 OS 계정에서 Codex CLI를 설치하고 `codex login`을 완료합니다. `codex login status`로 ChatGPT 로그인을 확인한 다음 웹에서 **Codex (ChatGPT subscription)**을 선택합니다. 두 모델을 `default`로 두면 Codex 기본 모델을 사용합니다. CLI 감지 표시는 로그인 성공을 보장하지 않습니다.
- **API 제공자 사용:** 설정 화면에 안내되는 환경변수 이름에 맞춰 API 키를 서버 환경변수 또는 저장소의 `.env`에 설정하고 서버를 재시작합니다. 예를 들어 OpenAI는 `OPENAI_API_KEY`를 사용합니다. 모델에는 해당 계정에서 사용 가능한 실제 모델 ID를 입력합니다. API 키는 웹 입력창에 넣지 않습니다.

분석 실행과 재실행에는 선택한 제공자의 API 또는 구독 사용량이 발생합니다. 데이터 제공자 설정과 사용자 지정 엔드포인트는 [웹 설정 상세 문서](webapp/README.md) 및 아래 CLI 설정을 참고하세요.

#### 3. 새 분석 시작 — ORCL 예시

1. **새 분석 시작**을 누릅니다.
2. **종목**에 `ORCL`을 입력하고 **분석 기준일**을 선택합니다. 미래 날짜는 사용할 수 없습니다.
3. 제공자를 **Codex (ChatGPT subscription)**, 빠른 분석·심층 추론 모델을 각각 `default`로 설정합니다.
4. **참여 분석가**에서 **시장 분석**만 선택하고, **리서치 깊이**를 **빠르게 · 토론 1 라운드**로 선택합니다.
5. **분석 시작 →**을 누릅니다. 한 번에 하나의 분석을 실행할 수 있습니다.

필요에 따라 펀더멘털·뉴스·시장 심리 분석가를 추가하고 토론 깊이를 3 또는 5라운드로 높일 수 있습니다. 선택한 분석가 다음에 찬반 토론, 투자 계획, 트레이더 판단, 위험 검토와 최종 판단이 이어집니다. 분석가 수와 깊이에 따라 실행 시간과 사용량이 달라집니다. 암호화폐 분석에서는 펀더멘털 분석가를 제외합니다.

#### 4. 진행 확인과 보고서 활용

**리서치 스튜디오**에서 진행 단계와 실행 상태를 확인합니다. 화면은 약 2초마다 갱신되며, 단계가 끝날 때마다 보고서가 추가됩니다. 분석가 탭과 토론·상세 보고서를 열어 각 판단의 근거를 읽을 수 있습니다. 최종 판단은 `Buy`, `Overweight`, `Hold`, `Underweight`, `Sell`로 표시되며, 판단을 해석할 수 없는 경우 `REVIEW`로 표시됩니다.

- **보고서 다운로드:** 현재 분석의 보고서를 Markdown 파일로 내려받습니다.
- **분석 기록:** 저장된 실행을 선택해 과거 결과를 다시 엽니다. 브라우저를 닫아도 서버가 실행 중이면 분석은 계속되며, 다시 접속하면 진행 중인 분석을 확인할 수 있습니다.
- **분석 중지:** 현재 모델·데이터 호출이 끝나는 다음 단계에서 중지됩니다. 이미 생성된 보고서는 유지됩니다.
- **같은 설정으로 다시 분석:** 기존 설정이 채워진 입력창을 엽니다. 내용을 확인하고 실행하면 새 분석으로 시작되며, 이전 중단 지점에서 재개하는 기능은 아닙니다.

가격 차트는 실제로 가져온 과거 데이터만 표시합니다. 데이터를 가져오지 못하면 비어 있을 수 있습니다. **가져온 보고서**는 기존 Alpha-Ledger 자료이며, 새 실행 결과나 현재 시세가 아닙니다. 해당 기록의 **원본 출처 보기**로 출처를 확인할 수 있습니다.

#### 5. 기록 보관과 문제 해결

실행 기록과 모델 기본값은 `.web-data/workspace.sqlite3`, 개별 분석의 보고서·캐시·메모리는 `.web-data/<분석 ID>/`에 저장됩니다. 이 폴더와 `.env`는 Git에 포함되지 않으므로 새로 복제한 저장소에는 개인 분석 기록이나 인증 정보가 없습니다. 기록을 백업할 때는 분석 완료 후 서버를 종료하고 `.web-data/` 전체를 복사하세요.

| 증상 | 확인 방법 |
| --- | --- |
| 웹에 접속할 수 없음 | 터미널의 서버 실행 여부와 브라우저 포트를 확인합니다. |
| 제공자 설정 필요 또는 실행 실패 | 동일 계정의 Codex 로그인, API 환경변수, 모델 접근 권한, 네트워크 연결을 확인하고 다시 실행합니다. |
| 서버 재시작 후 요청 오류 | 브라우저를 새로고침한 뒤 다시 시도합니다. |
| 중지 버튼을 눌러도 바로 끝나지 않음 | 현재 외부 호출이 완료될 때까지 기다립니다. |
| 서버 종료 후 분석이 중단됨 | 기록에서 부분 결과를 확인하고 같은 설정으로 새 분석을 시작합니다. |

Alpha-Ledger 보고서 가져오기와 개발 검증 명령은 [웹 상세 README](webapp/README.md)에 있습니다. `prototype/`은 디자인 확인용이며 실제 분석에는 위의 웹 서버를 사용합니다.

### Installation

Clone TradingAgents:
```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

Create a virtual environment in any of your favorite environment managers:
```bash
conda create -n tradingagents python=3.12
conda activate tradingagents
```

Install the package and its dependencies:
```bash
pip install .
```

### Docker

Alternatively, run with Docker:
```bash
cp .env.example .env  # add your API keys
docker compose run --rm tradingagents
```

For local models with Ollama:
```bash
docker compose --profile ollama run --rm tradingagents-ollama
```

### Codex / ChatGPT subscription (no LLM API key)

Choose **Codex (ChatGPT subscription)** in the provider menu to use your saved
Codex CLI login. The existing API providers remain available. This integration
uses the official [`codex exec`](https://developers.openai.com/codex/noninteractive)
command, including JSON output, and
[ChatGPT authentication](https://developers.openai.com/codex/auth).

Install a current Codex CLI (tested with 0.153.4; requires `--ignore-user-config`,
`--ephemeral`, and `--output-schema`), then sign in with your ChatGPT account:

```bash
npm install -g @openai/codex
codex login
codex login status  # should say Logged in using ChatGPT
```

For environment-based configuration, set **both** model values:

```bash
export TRADINGAGENTS_LLM_PROVIDER=codex
export TRADINGAGENTS_QUICK_THINK_LLM=default
export TRADINGAGENTS_DEEP_THINK_LLM=default
unset TRADINGAGENTS_LLM_BACKEND_URL
python -m cli.main
```

`default` lets Codex select its default subscription model. You can instead set
a model ID available to your Codex account. For Python usage:

```python
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = DEFAULT_CONFIG.copy()
config.update(llm_provider="codex", quick_think_llm="default",
              deep_think_llm="default", backend_url=None)
graph = TradingAgentsGraph(config=config)
state, decision = graph.propagate("AAPL", "2026-09-08")
```

The adapter launches one isolated CLI process per model turn. Conversation
history and tool results are passed through stdin; application tools execute
in TradingAgents, and typed decisions use LangChain's structured-output parser.
Codex runs in a temporary directory with a read-only sandbox, shell and web search
disabled, without loading your user config or project instructions. Authentication
still uses the CLI's credential store / `CODEX_HOME`. API-key authentication is
rejected, and inherited OpenAI API keys are removed from the child environment.

Subscription usage limits still apply; this is not unlimited inference. Data
vendors such as Alpha Vantage or FRED may still need their own keys. Full analysis
can take longer than API mode because it starts a CLI process for every turn.
Set `TRADINGAGENTS_CODEX_TIMEOUT` (seconds, default `300`) or
`TRADINGAGENTS_CODEX_COMMAND` (executable path) as needed. Python config uses
`codex_timeout` and `codex_command`. `openai_reasoning_effort` is supported;
`temperature`, `max_tokens`, and `llm_max_retries` are ignored with a warning.
CLI errors do not fall back to an API provider.

Run isolated tests with `python -m pytest tests/test_codex_provider.py`. To opt
into the live tool/structured-output smoke test (two subscription requests, using
synthetic data), run:

```bash
TRADINGAGENTS_CODEX_LIVE_TEST=1 python -m pytest tests/test_codex_provider.py -k live_codex -q
```

The adapter returns complete messages rather than token-by-token output. It reads
actual token usage from Codex JSON events, including cached input tokens (already
included in the input count).

Saved `complete_report.md` files include an **Analysis Usage** section with total,
input, output and cached input tokens, LLM call count, and elapsed minutes/seconds.
Both CLI and Python `propagate()` runs collect these metrics automatically;
Python results and saved state JSON retain them in `analysis_stats`. Timing uses a
monotonic clock from analysis start through model/data processing, excluding user
selection and report-saving prompts. Missing usage is labeled unavailable or
partial, never estimated as zero. On checkpoint resume, metrics cover only the
current execution, explicitly excluding prior attempts.

### Required APIs

TradingAgents supports multiple LLM providers. Set the API key for your chosen provider:

```bash
export OPENAI_API_KEY=...          # OpenAI (GPT)
export GOOGLE_API_KEY=...          # Google (Gemini)
export ANTHROPIC_API_KEY=...       # Anthropic (Claude)
export XAI_API_KEY=...             # xAI (Grok)
export DEEPSEEK_API_KEY=...        # DeepSeek
export DASHSCOPE_API_KEY=...       # Qwen — International (dashscope-intl.aliyuncs.com)
export DASHSCOPE_CN_API_KEY=...    # Qwen — China (dashscope.aliyuncs.com)
export ZHIPU_API_KEY=...           # GLM via Z.AI (international)
export ZHIPU_CN_API_KEY=...        # GLM via BigModel (China, open.bigmodel.cn)
export MINIMAX_API_KEY=...         # MiniMax — Global (api.minimax.io)
export MINIMAX_CN_API_KEY=...      # MiniMax — China (api.minimaxi.com)
export OPENROUTER_API_KEY=...      # OpenRouter
export ALPHA_VANTAGE_API_KEY=...   # Alpha Vantage
```

For Azure OpenAI, copy `.env.enterprise.example` to `.env.enterprise` and fill in your credentials.

For AWS Bedrock, install the extra with `pip install ".[bedrock]"`, set `llm_provider: "bedrock"`, configure AWS credentials (environment variables, `~/.aws/credentials`, or an IAM role) and `AWS_DEFAULT_REGION`, and use a Bedrock model ID, e.g. `us.anthropic.claude-opus-4-8-v1:0`.

For local models, configure Ollama with `llm_provider: "ollama"`. The default endpoint is `http://localhost:11434/v1`; set `OLLAMA_BASE_URL` to point at a remote `ollama-serve`. Pull models with `ollama pull <name>`, and pick "Custom model ID" in the CLI for any model not listed by default.

For any other OpenAI-compatible server (vLLM, LM Studio, llama.cpp, or a custom relay), use `llm_provider: "openai_compatible"` and set the endpoint via `backend_url` (or `TRADINGAGENTS_LLM_BACKEND_URL`), e.g. `http://localhost:8000/v1` for vLLM or `http://localhost:1234/v1` for LM Studio. The model is whatever your server serves. No key is needed for local servers; set `OPENAI_COMPATIBLE_API_KEY` when the endpoint requires one.

Alternatively, copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### CLI Usage

Launch the interactive CLI:
```bash
tradingagents          # installed command
python -m cli.main     # alternative: run directly from source
```
You will see a screen where you can select your desired tickers, analysis date, LLM provider, research depth, and more.

### Markets and tickers

TradingAgents works with any market Yahoo Finance covers, using the exchange-suffixed ticker. Company identity and the alpha benchmark resolve automatically per market.

- US: `AAPL`, `SPY`
- Hong Kong: `0700.HK` · Tokyo: `7203.T` · London: `AZN.L`
- India: `RELIANCE.NS`, `.BO` · Canada: `.TO` · Australia: `.AX`
- China A-shares: Shanghai `.SS`, Shenzhen `.SZ` (e.g. `600519.SS` for Kweichow Moutai)
- Crypto: `BTC-USD`, `ETH-USD`

<p align="center">
  <img src="assets/cli/cli_init.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

An interface will appear showing results as they load, letting you track the agent's progress as it runs.

<p align="center">
  <img src="assets/cli/cli_news.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

<p align="center">
  <img src="assets/cli/cli_transaction.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

## TradingAgents Package

### Implementation Details

We built TradingAgents with LangGraph to ensure flexibility and modularity. The framework supports multiple LLM providers: OpenAI, Google, Anthropic, xAI, DeepSeek, Qwen (Alibaba DashScope, international and China endpoints), GLM (Zhipu), MiniMax (global + China), OpenRouter, Ollama for local models, and Azure OpenAI for enterprise.

### Python Usage

To use TradingAgents inside your code, you can import the `tradingagents` module and initialize a `TradingAgentsGraph()` object. The `.propagate()` function will return a decision. You can run `main.py`, here's also a quick example:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())

# forward propagate
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

You can also adjust the default configuration to set your own choice of LLMs, debate rounds, etc.

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"        # e.g. openai, google, anthropic, deepseek, groq, ollama; openai_compatible covers any OpenAI-compatible endpoint (vLLM, LM Studio, llama.cpp, ...)
config["deep_think_llm"] = "gpt-5.6"      # Model for complex reasoning
config["quick_think_llm"] = "gpt-5.6-luna" # Model for quick tasks
config["max_debate_rounds"] = 2

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

See `tradingagents/default_config.py` for all configuration options.

## Persistence and Recovery

TradingAgents persists two kinds of state across runs.

### Decision log

The decision log is always on. Each completed run appends its decision to `~/.tradingagents/memory/trading_memory.md`. On the next run for the same ticker, TradingAgents fetches the realised return (raw and alpha vs SPY), generates a one-paragraph reflection, and injects the most recent same-ticker decisions plus recent cross-ticker lessons into the Portfolio Manager prompt, so each analysis carries forward what worked and what didn't.

Override the path with `TRADINGAGENTS_MEMORY_LOG_PATH`.

### Checkpoint resume

Checkpoint resume is opt-in via `--checkpoint`. When enabled, LangGraph saves state after each node so a crashed or interrupted run resumes from the last successful step instead of starting over. On a resume run you will see `Resuming from step N for <TICKER> on <date>` in the logs; on a new run you will see `Starting fresh`. Checkpoints are cleared automatically on successful completion.

Per-ticker SQLite databases live at `~/.tradingagents/cache/checkpoints/<TICKER>.db` (override the base with `TRADINGAGENTS_CACHE_DIR`). Use `--clear-checkpoints` to reset all of them before a run.

```bash
tradingagents analyze --checkpoint           # enable for this run
tradingagents analyze --clear-checkpoints    # reset before running
```

```python
config = DEFAULT_CONFIG.copy()
config["checkpoint_enabled"] = True
ta = TradingAgentsGraph(config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
```

## Reproducibility

TradingAgents is LLM-driven, so two runs of the same ticker and date can differ. This is expected for a research tool built on language models, not a defect. The variation comes from a few distinct sources, and it helps to separate them.

Language model sampling is non-deterministic. Even at a fixed temperature, providers do not guarantee byte-identical output across calls, and reasoning models (the default GPT-5.x family, and any thinking-mode model) vary the most because their internal reasoning is itself sampled.

Live data moves. News, StockTwits, and Reddit return different content as time passes, so a run today sees different inputs than a run last week even for the same historical trade date. Pin the analysis date to hold the price and indicator window fixed, but the social and news sources still reflect "now".

To reduce variation you can lower the sampling temperature. Set `temperature` in your config (or `TRADINGAGENTS_TEMPERATURE` in `.env`); lower values make models that honor it more repeatable. The current curated models are reasoning-first and largely ignore temperature, so for tighter reproducibility use a non-reasoning model, which you can set explicitly via the Custom model ID option.

```python
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["temperature"] = 0.0
# Reasoning models ignore temperature. For tighter reproducibility, set a
# non-reasoning deep/quick model explicitly (e.g. via the Custom model ID option).
```

What does not vary anymore: the analyzed company identity is resolved deterministically from the ticker before any agent runs, and the market analyst grounds exact price and indicator claims in a verified data snapshot. Earlier reports of "different companies" or fabricated price levels across runs are addressed by these two mechanisms.

Backtest results are not guaranteed to match any published figure. Returns depend on the model, the temperature, the date range, data quality, and the sampling above. Treat the framework as a research scaffold for studying multi-agent analysis, not as a strategy with a fixed, replicable return.

## Contributing

Contributions are welcome: bug fixes, documentation, and feature ideas; past contributions are credited per release in [`CHANGELOG.md`](CHANGELOG.md).

## Citation

Please reference our work if you find *TradingAgents* provides you with some help :)

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
```
