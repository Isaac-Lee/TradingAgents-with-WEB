# API 계약 — TradingAgents 웹앱

이 문서에 없는 필드/엔드포인트는 카드가 임의로 만들지 않는다. 필요하면 여기 먼저 추가하고
작업한다. 모든 응답은 `application/json`, 실패 시 `{"error": "message"}` + 4xx/5xx.

## 배경 (왜 이렇게 짜여있는지)

기존 CLI(`cli/main.py`)는 `MessageBuffer`(순수 데이터, rich 비의존)가 상태를 들고 있고,
`update_display()`가 그걸 rich 화면으로 그린다. 웹앱은 `update_display()` 자리를
SSE로 갈아끼우는 것뿐, `MessageBuffer`/그래프 스트리밍 루프는 그대로 재사용한다.
`tradingagents/reporting.py`의 `write_report_tree()`도 CLI/웹 공용.

## REST 엔드포인트

### `GET /api/options`
프론트 폼 채우는 정적/준정적 목록. LLM 프로바이더 테이블, 프로바이더별 모델 옵션,
애널리스트 목록, 리서치 depth 옵션을 한 번에 반환.

```json
{
  "providers": [{"name": "OpenAI", "key": "openai", "default_url": "https://api.openai.com/v1"}],
  "analysts": [{"key": "market", "label": "Market Analyst"}],
  "research_depth": [{"label": "Shallow", "value": 1}],
  "asset_types": ["stock", "crypto"]
}
```
`providers`는 모델 목록을 포함하지 않는다 — 프로바이더 고를 때마다 모델 목록이
바뀌므로 별도 호출로 뺀다.

### `GET /api/options/models?provider=openai&mode=quick`
`mode`는 `quick`(shallow) 또는 `deep`. 응답: `[{"label": "...", "value": "..."}]`.

### `POST /api/runs`
바디:
```json
{
  "ticker": "AAPL",
  "analysis_date": "2026-08-22",
  "analysts": ["market", "news"],
  "research_depth": 1,
  "llm_provider": "openai",
  "backend_url": "https://api.openai.com/v1",
  "shallow_thinker": "gpt-4o-mini",
  "deep_thinker": "gpt-4o",
  "output_language": "English"
}
```
API 키는 절대 이 바디에 없다. 서버가 이미 가지고 있는 환경변수를 쓴다. 필요한 키가
비어있으면 202 대신 400 + `{"error": "OPENAI_API_KEY not set"}`.

응답 202: `{"run_id": "uuid"}`. 동시 실행 런은 1개로 제한 — 이미 실행 중이면 409.

### `GET /api/runs/{run_id}/events`
SSE (`text/event-stream`). 이벤트 스키마는 아래 "SSE 이벤트" 섹션. 연결이 끊기고
재연결하면 처음부터 다시 받는다(재생 버퍼 없음, 재개 기능은 범위 밖).

### `POST /api/runs/{run_id}/stop`
실행 중인 런에 정지 신호. 이후 SSE에 `{"type":"done","status":"stopped"}` 흘러야 함.
응답: `{"ok": true}`.

### `GET /api/history`
```json
[
  {
    "ticker": "AAPL",
    "date": "2026-08-22",
    "path": "AAPL/2026-08-22",
    "decision": "BUY"
  }
]
```
`results_dir`(설정값 — `TRADINGAGENTS_RESULTS_DIR` 또는 DEFAULT_CONFIG 기본) 하위를 스캔.
**`path`는 results_dir 기준 상대경로다** (`results/` 같은 접두사를 붙이지 않는다 —
results_dir이 `results/`가 아닐 수 있으므로). 프론트는 이 값을 `/api/report?path=`와
`/api/history/compare?paths=`에 그대로 넘긴다. `decision`은
`tradingagents/reporting.py`의 `parse_decision()`으로 `final_trade_decision.md`에서
뽑는다. 못 찾으면 `null`.

### `GET /api/report?path=AAPL/2026-08-22`
`complete_report.md` 원문을 `{"content": "...markdown..."}`으로 반환. `path`는 반드시
`results_dir`의 하위 경로인지 `Path.resolve()`로 검증 후 거부/허용 — path traversal 방지.

### `GET /api/history/compare?paths=AAPL/2026-08-22,AAPL/2026-08-15`
```json
[
  {"ticker": "AAPL", "date": "2026-08-22", "decision": "BUY", "content": "...complete_report.md..."}
]
```
2~4개 경로. 각 경로는 `/api/report`와 동일한 traversal 검증.

### `GET /api/ohlcv?ticker=AAPL&date=2026-08-22`
`tradingagents/dataflows/stockstats_utils.py`의 `load_ohlcv(symbol, curr_date)` 그대로 호출.
```json
[{"date": "2026-08-01", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.05, "volume": 12345}]
```

## SSE 이벤트

`data: <json>\n\n` 한 줄 JSON, 타입은 `type` 필드로 구분.

```json
{"type": "status", "agent": "Market Analyst", "state": "pending|in_progress|completed"}
{"type": "message", "kind": "Reasoning", "text": "..."}
{"type": "tool", "name": "get_YFin_data", "args": {"symbol": "AAPL"}}
{"type": "report", "section": "market_report", "content": "...markdown..."}
{"type": "stats", "llm_calls": 12, "tokens": 34567, "elapsed_sec": 91.2}
{"type": "done", "status": "completed|stopped|error", "decision": "BUY", "path": "AAPL/2026-08-22"}
```
`status.state`는 `MessageBuffer.agent_status`의 값을 그대로 옮긴 것. `report.section`은
`ANALYST_REPORT_MAP`/`REPORT_SECTIONS`(`cli/main.py`)에 있는 키와 동일해야 한다 — 프론트
탭 렌더링이 이 키로 분기한다. `done.path`도 results_dir 기준 상대경로 (`/api/history`의
`path`와 동일한 형태).

## 컬러 토큰 (다크 테마 고정)

`webapp/static/styles.css`에 CSS 커스텀 프로퍼티로 정의. 하드코딩된 hex를 다른 파일에
직접 쓰지 않고 전부 이 변수 참조.

| 토큰 | 값 | 용도 |
|---|---|---|
| `--bg` | `#212529` | 앱 배경 |
| `--surface` | `#343a40` | 카드/패널 |
| `--surface-raised` | `#495057` | 모달, hover 배경 |
| `--border` | `#495057` | 구분선 |
| `--border-strong` | `#6c757d` | 인풋 테두리, 포커스 |
| `--muted` | `#6c757d` | pending 상태, placeholder |
| `--muted-strong` | `#adb5bd` | 보조 텍스트, HOLD 뱃지 |
| `--fg-soft` | `#ced4da` | 서브 헤딩 |
| `--fg` | `#e9ecef` | 본문 텍스트 |
| `--fg-strong` | `#f8f9fa` | 헤딩, completed 상태 |
| `--danger` | `#ef233c` | SELL, 에러, 경고 |
| `--success` | `#2ec27e` | BUY |

라이트 테마 없음. 토글 UI도 만들지 않는다.

## 파일 배치

```
webapp/
  __init__.py
  runner.py        헤드리스 스트림 루프 (MessageBuffer -> Queue)
  server.py         FastAPI app, 위 엔드포인트
  desktop.py        pywebview 창 진입점
  static/
    index.html
    styles.css
    app.js
    vendor/lightweight-charts.js   TradingView 오픈소스, MIT, vendored (CDN 금지)
```
