# Card 07 — webapp/desktop.py (pywebview 진입점)

**Blocked by:** Card 03, 04, 05, 06 (앱 전체가 먼저 동작해야 함)

## 배경

보드 문서의 완료 조건 실행 경로: `python -m webapp.desktop`. 서버를 스레드로 띄우고
pywebview 창으로 연다.

## 작업 (`webapp/desktop.py`)

- `python -m webapp.desktop` 실행 시:
  1. uvicorn 서버를 백그라운드 스레드로 기동 (127.0.0.1, Card 02의 포트 상수 재사용).
  2. 서버 readiness 확인(예: `/api/options` 폴에 성공할 때까지, 타임아웃+에러 처리) 후
     pywebview 창 생성 → `http://127.0.0.1:<port>/`.
  3. 창 닫힘 시 서버 정리 후 종료.
- 포트 충돌 시 명확한 에러 메시지.
- pywebview는 `web` optional-deps에 이미 포함됨 (Card 02). core 의존성 불변 확인.

## Acceptance

- [ ] `python -m webapp.desktop`으로 창이 열리고 런 시작 → 상태 갱신 → 리포트 표시까지
  동작 (실제 LLM 키가 없으면 400 에러가 UI에 표시되는 것까지 확인).
- [ ] 창 닫으면 프로세스가 정상 종료 (잔여 스레드/포트 점유 없음).
- [ ] 포트 점유 상태에서 실행 → 사용자가 이해 가능한 에러.
- [ ] `pytest tests/` 통과.

## 금지

- 외부 바인딩. 브라우저 대신 webview를 쓰는 것 외의 동작 변경.
