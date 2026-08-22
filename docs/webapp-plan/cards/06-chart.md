# Card 06 — OHLCV 차트 (API + vendored lightweight-charts)

**Blocked by:** Card 02 (server base), Card 04 (frontend core)

## 배경

리포트와 함께 가격 차트를 보여준다. TradingView lightweight-charts(Apache-2.0이
아니라 MIT — 원저장소 라이선스 확인 후 파일에 저작권 헤더 유지)를 **vendored**로
둔다. CDN 금지는 보드 공통 규칙.

## 작업

### 1. `GET /api/ohlcv?ticker=<T>&date=<YYYY-MM-DD>` (`webapp/server.py`에 추가)
- `tradingagents/dataflows/stockstats_utils.py`의 `load_ohlcv(symbol, curr_date)`
  그대로 호출. 반환 DataFrame을 계약 형태로 변환:
  ```json
  [{"date":"2026-08-01","open":1.0,"high":1.1,"low":0.9,"close":1.05,"volume":12345}]
  ```
- 데이터 소스 실패(네트워크 등) → 502 `{"error":...}`. 파라미터 누락/형식 오류 → 400.

### 2. `webapp/static/vendor/lightweight-charts.js`
- lightweight-charts standalone 빌드를 저장소에 vendor. 파일 상단에
  버전/출처/라이선스 주석. 업데이트는 수동.

### 3. 프론트 차트 탭 (`index.html`/`app.js`에 추가)
- 리포트 탭들 옆에 "Chart" 탭. 런 완료(`done`) 또는 히스토리에서 리포트 열 때
  해당 ticker+date로 `/api/ohlcv` 호출해 캔들스틱 차트 렌더.
- 차트 색상도 styles.css 토큰 참조 (상승=--success, 하락=--danger).

## Acceptance

- [ ] `curl '127.0.0.1:<port>/api/ohlcv?ticker=AAPL&date=<최근일>'` → 계약 스키마 배열
  (네트워크 가능 환경). 실패 주입 시 502.
- [ ] 브라우저에서 Chart 탭에 캔들 차트 표시 수동 확인 + 증적 기록.
- [ ] index.html/app.js에 CDN 참조 없음, vendor 파일에 라이선스 주석 있음.
- [ ] `pytest tests/` 통과.

## 금지

- CDN 로딩. 차트 데이터를 프론트에서 직접 외부 API 호출 (반드시 /api/ohlcv 경유).
