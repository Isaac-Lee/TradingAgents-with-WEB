# Card 03 — runs 제어 + SSE 엔드포인트

**Blocked by:** Card 01 (runner), Card 02 (server base)

## 배경

`webapp/server.py`에 런 생명주기 엔드포인트 3개를 추가한다. Card 01의
`start_run()`/`RunHandle`을 서버가 보유하고, 동시 실행은 1개로 제한한다.

## 작업 (`webapp/server.py`에 추가)

### `POST /api/runs`
- 바디는 계약의 9개 필드. 유효성 검증 실패 → 400 `{"error":...}`.
- 필수 API 키 검사: `cli/utils.py`의 `ensure_api_key()`가 쓰는 provider→환경변수
  매핑을 **비인터랙티브하게** 재사용 (프롬프트 금지 — 서버에서는 검사만).
  키가 없으면 400 `{"error": "<KEY_NAME> not set"}`. 로컬 프로바이더(ollama 등
  키 불필요)는 통과.
- 이미 실행 중인 런이 있으면 409 `{"error": "run already in progress"}`.
- 성공 시 `start_run()`으로 스레드 시작, 202 `{"run_id": "..."}`.

### `GET /api/runs/{run_id}/events`
- `text/event-stream`. `RunHandle.events` 큐에서 꺼내 `data: <json>\n\n`로 흘려볼낸다.
- `done` 이벤트 방출 후 스트림 종료. 재연결 시 처음부터 다시 받는다(재생 버퍼 없음
  — 계약 명시 사항, 버퍼링 구현 불요).
- 존재하지 않는 run_id → 404 `{"error":...}`.

### `POST /api/runs/{run_id}/stop`
- `stop_event.set()` 후 `{"ok": true}`. 이후 SSE에 `done/stopped`가 흐르는 것은
  runner 책임(Card 01 계약). 존재하지 않는 run_id → 404.

### 런 상태 보관
- 현재 런 핸들은 앱 상태에 1개만. 완료(done 방출)된 런은 새 런 시작을 막지 않는다.

## Acceptance

- [ ] stub runner(또는 fake 그래프)를 얹은 상태에서:
  - `POST /api/runs` → 202 + run_id, `GET .../events` → SSE로 계약 스키마 이벤트 수신,
    `done` 후 스트림 종료.
  - 실행 중 두 번째 `POST /api/runs` → 409.
  - 키 환경변수를 지운 상태로 실행 → 400 `{"error": "<KEY> not set"}`.
  - `POST .../stop` → `{"ok": true}` + SSE에 `done/stopped`.
- [ ] 실패 응답 전부 `{"error":...}` 형태.
- [ ] `pytest tests/` 통과.

## 금지

- API 키를 요청 바디/쿼리로 받거나 응답/로그에 노출.
- 재생(resume) 버퍼 구현 — 범위 밖.
