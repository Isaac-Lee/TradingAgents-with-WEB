# Card 04 — 프론트엔드 코어 (index.html / styles.css / app.js)

**Blocked by:** Card 03 (호출할 API가 있어야 붙여볼 수 있음)

## 배경

다크 테마 고정 단일 페이지. 계약의 컬러 토큰을 `styles.css`의 CSS 커스텀
프로퍼티로 정의하고, 다른 파일에서는 변수만 참조한다. CDN 금지, 외부 JS 프레임워크
없이 바닐라로 만든다 (차트 라이브러리는 Card 06에서 vendor).

## 작업

### `webapp/static/styles.css`
- 계약 "컬러 토큰" 표의 12개 토큰을 `:root` 커스텀 프로퍼티로 정의. 값은 계약 표 그대로.
- 폼/카드/뱃지/탭/로그 영역 스타일. hex 하드코딩은 이 파일의 토큰 정의부에만 존재.

### `webapp/static/index.html`
- 상단: 런 설정 폼 — ticker, analysis_date, analysts(다중 선택), research_depth,
  llm_provider, backend_url(프로바이더 선택 시 default_url 자동 채움, 수정 가능),
  shallow/deep thinker (provider+mode에 따라 `/api/options/models`로 갱신),
  output_language. 시작/정지 버튼.
- 중단: 에이전트 상태 패널 (`status` 이벤트, pending/in_progress/completed 뱃지 —
  pending=--muted, in_progress=--border-strong 계열, completed=--fg-strong).
- 하단: 리포트 탭 (`report` 이벤트의 section 키로 탭 분기 —
  `MessageBuffer.REPORT_SECTIONS` 키 목록과 동일), 메시지/툴 로그, stats 표시줄.
- BUY=--success, SELL=--danger, HOLD=--muted-strong 뱃지.

### `webapp/static/app.js`
- 로드 시 `GET /api/options`로 폼 채움. provider 변경 시 모델 목록 갱신.
- 시작: `POST /api/runs` → 202면 `EventSource('/api/runs/{id}/events')` 구독,
  400/409는 폼 상단에 에러 표시.
- SSE 이벤트 타입별 렌더링 (status/message/tool/report/stats/done).
  `done.decision`을 뱃지로, `done.path`를 표시. markdown은 최소 렌더링(헤딩/볼드/
  리스트 정도의 자체 변환) — 외부 CDN 라이브러리 금지.
- 정지: `POST /api/runs/{id}/stop`.
- 히스토리/비교/차트 UI는 후속 카드 — 이 카드에서는 런 플로우만.

## Acceptance

- [ ] 서버 기동 후 브라우저에서 폼 표시 → 옵션 로딩 → (stub 또는 실제) 런 시작 →
  상태/로그/리포트 탭이 SSE대로 갱신 → done 뱃지까지 수동 확인. 스크린샷 또는
  확인 절차를 카드 코멘트에 기록.
- [ ] `styles.css` 외 파일에 hex 하드코딩 없음 (grep으로 확인).
- [ ] 외부 네트워크 참조(CDN/폰트) 없음 (index.html/app.js grep 확인).
- [ ] 라이트 테마/테마 토글 없음.

## 금지

- JS 프레임워크/빌드 도구 도입.
- 계약에 없는 엔드포인트 호출.
