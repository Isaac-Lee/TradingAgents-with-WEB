# Card 05 — 히스토리/리포트 API

**Blocked by:** Card 02 (server base). Card 03/04와 병렬 가능.

## 배경

과거 런 결과를 조회하는 읽기 전용 엔드포인트 3개. `results_dir`은
`tradingagents/default_config.py`의 `DEFAULT_CONFIG["results_dir"]`
(`TRADINGAGENTS_RESULTS_DIR` env 오버라이드 포함)를 따른다. decision 추출에는
Card 00의 `parse_decision()`을 쓴다.

## 작업 (`webapp/server.py`에 추가)

### `GET /api/history`
- `results_dir` 하위를 `<TICKER>/<YYYY-MM-DD>/` 구조로 스캔.
- 각 항목: `{"ticker","date","path","decision"}`. `path`는 results_dir 기준
  상대경로(예: `results/AAPL/2026-08-22` — results_dir이 `results/`가 아니어도
  프론트가 그대로 `/api/report?path=`에 넘길 수 있는 형태면 됨. 계약 예시는
  `results/...`이나, 실제로는 results_dir 상대 경로 + 접두 일관성만 지킬 것.
  구현 후 확정한 형태를 01-API-CONTRACT.md에 반영할 것).
- `decision`: 해당 디렉토리의 `final_trade_decision.md`를 읽어 `parse_decision()`.
  파일 없거나 매칭 실패 → `null`.

### `GET /api/report?path=<상대경로>`
- `complete_report.md` 원문을 `{"content": "..."}`으로 반환.
- **path traversal 방어**: `Path(results_dir, path).resolve()`가
  `Path(results_dir).resolve()`의 하위인지 검증, 아니면 400 `{"error":...}`.
  파일 없으면 404.

### `GET /api/history/compare?paths=<콤마 구분 2~4개>`
- 각 경로에 대해 `{"ticker","date","decision","content"}` 리스트 반환.
- 경로 개수 위반(1개 또는 5개 이상) → 400. 각 경로는 `/api/report`와 동일한
  traversal 검증. 하나라도 불법 경로면 전체 거부.

## Acceptance

- [ ] 테스트 픽스처(results_dir 하위에 가짜 `<TICKER>/<DATE>/` + 리포트 파일)로
  3개 엔드포인트 응답이 계약 형태임을 확인 (테스트 또는 curl 증적).
- [ ] `path=../../etc/passwd`, `path=../outside` 등 traversal 시도 → 400.
- [ ] `final_trade_decision.md` 없는 런 → history에서 `decision: null`.
- [ ] compare에 1개/5개 경로 → 400.
- [ ] `pytest tests/` 통과.

## 금지

- results_dir 외부 파일 읽기 (심볼릭링크 포함 — resolve 기준 검증).
- 응답에 절대경로 노출 (상대경로만).
