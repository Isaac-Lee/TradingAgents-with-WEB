# Card 01 — webapp/runner.py (헤드리스 스트림 루프)

**Blocked by:** Card 00 (Done)

## 배경

`cli/main.py`의 `analyze()` 남반부(≈1090~1255행)가 그래프 스트림 루프다: chunk를 받아
`MessageBuffer`에 반영하고 `update_display()`로 그린다. 웹앱은 `update_display()` 자리에
"이벤트 dict를 `queue.Queue`에 넣는 콜백"을 끼운다. 스트림 해석 로직(메시지 분류,
analyst 상태 전이, debate state 처리)은 CLI와 동일해야 한다.

`update_analyst_statuses(message_buffer, chunk, ...)`는 이미 버퍼를 첫 인자로 받고,
`update_research_team_status(status, buffer=...)`는 Card 00에서 파라미터화됐다.

## 작업

### `webapp/__init__.py`
빈 파일.

### `webapp/runner.py`
다음 인터페이스를 제공한다 (이름은 고정, 나머지 구현 방식은 자유):

```python
class RunHandle:
    run_id: str
    events: "queue.Queue[dict]"   # SSE 이벤트 dict (계약 "SSE 이벤트" 스키마)
    stop_event: threading.Event
    thread: threading.Thread

def start_run(request: RunRequest) -> RunHandle: ...
```

- `RunRequest` dataclass: `POST /api/runs` 바디와 1:1 대응
  (ticker, analysis_date, analysts, research_depth, llm_provider, backend_url,
  shallow_thinker, deep_thinker, output_language). asset_type은 analysts 선택으로
  결정되는 CLI 관행을 따륐 — 필요시 `asset_type` 필드 추가하되 그 경우 계약 문서에도
  추가할 것.
- 스레드 안에서:
  1. 자신만의 `MessageBuffer` 인스턴스 생성 (모듈 전역 공유 금지).
  2. `TradingAgentsGraph` 구성 (config 오버라이드: llm_provider, backend_url,
     quick/deep thinker, results_dir) 후 CLI와 같은 방식으로 초기 상태 생성
     (`resolve_instrument_context` → `create_initial_state` → `get_graph_args`).
  3. `graph.graph.stream(...)` 루프를 돌며 CLI 루프와 동일한 해석을 수행하되,
     `update_display()` 대신 버퍼 변화를 이벤트 dict로 환산해 `events`에 넣는다.
     - 새 메시지 → `{"type":"message",...}`, 새 tool call → `{"type":"tool",...}`,
       agent 상태 변화 → `{"type":"status",...}`, report section 갱신 →
       `{"type":"report",...}`. `report.section` 키는 `MessageBuffer.REPORT_SECTIONS`
       키와 동일해야 함 (프론트 탭 분기 기준).
     - 주기적으로(예: chunk마다 1회 이하) `{"type":"stats","llm_calls":N,"tokens":M,
       "elapsed_sec":S}`.
  4. 매 chunk 처리 전 `stop_event.is_set()` 검사 — set이면 루프 탈출 후
     `{"type":"done","status":"stopped"}` 방출.
  5. 정상 종료 시 `write_report_tree(final_state, ticker, save_path)`로 저장
     (CLI 공용 함수), `final_trade_decision` 섹션 텍스트에 `parse_decision()` 적용해
     `{"type":"done","status":"completed","decision":...,"path":"results/<T>/<D>"}`
     방출. `path`는 results_dir 기준 상대경로.
  6. 예외 시 `{"type":"done","status":"error"}` + `message` 필드로 사유 방출.
- **의존성 제한**: 이 파일은 fastapi/uvicorn을 import하지 않는다 (표준 라이브러리 +
  tradingagents/cli 모듈만). 서버 의존성이 runner로 새어들어가면 안 됨.

## Acceptance

- [ ] `webapp/runner.py` import가 fastapi 없는 환경에서 성공 (`python -c "import webapp.runner"`).
- [ ] 그래프를 stub/fake으로 주입한 단위 테스트 또는 `python -c` 수준 검증:
  fake stream이 chunk를 낼 때 계약 스키마의 이벤트 dict가 큐에 쌓이고,
  `stop_event.set()` 후 `done/stopped`가 방출됨.
- [ ] `pytest tests/` 기존 스위트 통과.
- [ ] CLI 동작 변경 없음 (`cli/main.py` diff 없음 — 필요한 재사용이 있으면 Card 00처럼
  기본 인자 추가만 허용, 그 경우 카드 코멘트에 명시).

## 금지

- fastapi/uvicorn/pywebview import.
- 모듈 전역 MessageBuffer 사용.
- 계약에 없는 이벤트 type 임의 추가 (필요하면 01-API-CONTRACT.md 먼저 수정 + 카드 코멘트).
