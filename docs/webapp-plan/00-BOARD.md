# Kanban 운영 가이드 — TradingAgents 웹앱

여러 Hermes Agent가 각자 별도 세션에서 카드를 하나씩 집어 작업한다. 서로의 대화 기록을
공유하지 않으므로, 모든 합의 사항은 이 디렉토리의 문서에 **글로 박아둔다**. 카드 설명이나
채팅으로만 전달된 결정은 다음 에이전트가 모른다고 가정할 것.

## 문서 구조

- `01-API-CONTRACT.md` — REST/SSE 스펙, 컬러 토큰. **모든 카드의 단일 진실 공급원.**
  카드 작업 중 이 계약을 바꿔야 하면, 코드보다 먼저 이 문서를 고치고 PR/커밋 메시지에
  "contract 변경" 명시. 다른 카드가 참조하는 값이므로 조용히 바꾸지 않는다.
- `cards/*.md` — 카드 1개 = 파일 1개. 파일명 앞 두 자리 숫자가 실행 순서/의존 순서.

## 컬럼

1. **Backlog** — 아직 아무도 안 잡음
2. **In Progress** — 담당 에이전트 배정됨
3. **Review** — 구현 끝, 인수 조건(Acceptance) 검증 대기
4. **Done** — 검증 통과, 머지됨

## 카드 집는 규칙

- 카드의 "Blocked by" 목록이 전부 Done이어야 In Progress로 옮긴다. 아니면 대기하거나
  다른 카드를 집는다.
- 카드 하나는 원칙적으로 **파일 1~3개** 범위. 이보다 커지면 카드가 잘못 쪼개진 것 —
  손대기 전에 사람에게 알린다.
- 구현 중 `01-API-CONTRACT.md`와 다르게 가야 할 이유를 발견하면, 임의로 다르게 짓지 말고
  카드를 Review에 "계약 변경 필요" 코멘트와 함께 올리고 사람 승인 기다린다. 특히 SSE
  이벤트 스키마, REST 엔드포인트 경로/응답 형태는 다른 카드들이 그대로 가정하고 있다.

## Review 통과 기준 (공통)

카드별 Acceptance Criteria 외에 공통으로:

- 새로 추가한 의존성은 `pyproject.toml`의 `[project.optional-dependencies] web`에만 넣는다.
  core 의존성에 섞지 않는다 (CLI 전용 사용자에게 fastapi/uvicorn/pywebview 강제 설치 금지).
- 서버는 `127.0.0.1` 바인딩 고정. 인증 없음 = 로컬 전용이 전제. 외부 바인딩으로 바꾸지 않는다.
- API 키를 요청 바디/쿼리로 받거나 프론트로 되돌려주는 코드를 작성하지 않는다. 서버 프로세스의
  환경변수/`.env`에서만 읽는다.
- `results_dir` 바깥 경로를 읽는 요청(예: `/api/report?path=`)은 반드시 거부한다 — path traversal.
- 기존 CLI(`tradingagents analyze`)가 이 작업으로 인해 동작이 바뀌면 안 된다. 바뀌었다면 회귀.

## 커밋 / 푸시 규칙

- 작업 브랜치: `feature/webapp`. main에 직접 커밋하지 않는다.
- **구현 에이전트(sw-developer)**: 카드 단위로 쪼개 커밋한다 — 최소 카드 1개 = 커밋 1개,
  카드 내에서도 논리 단위(리팩터/신규 모듈/테스트)로 나눌 수 있으면 나눈다.
  커밋 메시지 앞에 카드 번호를 붙인다 (예: `[card-01] add webapp runner skeleton`).
  push는 하지 않는다.
- **아키텍트(sw-architecture)**: 카드 리뷰 통과 시점에 브랜치를 origin으로 push한다.
  리뷰에서 반려된 변경은 push하지 않는다.

## 완료 후

모든 카드가 Done이면 `run` 스킬 또는 `python -m webapp.desktop`으로 전체 플로우
(런 시작 → 실시간 상태 → 리포트 → 히스토리 → 차트)를 한 번 수동으로 확인하고 이 문서에
결과를 남긴다.

---

## 완료 검증 기록

**검증일:** 2025-08-22
**검증자:** sw-developer
**환경:** macOS 14.7, Python 3.14.6, feature/webapp 브랜치
**서버 실행:** `python -m uvicorn webapp.server:app --host 127.0.0.1 --port 8765`

### 확인 항목

| 항목 | 결과 | 비고 |
|------|------|------|
| 서버 기동 | ✅ PASS | 127.0.0.1:8765, uvicorn 백그라운드 스레드 |
| `/api/options` | ✅ PASS | providers/analysts/research_depth/asset_types 반환 |
| `/api/options/models` | ✅ PASS | openai/quick → GPT-5.4 Mini 등 모델 목록 반환 |
| `/api/history` | ✅ PASS | 기존 results_dir 스캔 결과 2건 반환 (ABCL, FAKE) |
| `/api/report?path=` | ✅ PASS | complete_report.md 없는 항목 → 404 (예상 동작) |
| `/api/history/compare` | ✅ PASS | complete_report.md 없는 항목 → 404 (예상 동작) |
| `/api/ohlcv?ticker=AAPL&date=2025-01-01` | ✅ PASS | 2019-08~2025-01 OHLCV 배열 반환 |
| `/api/runs` (API 키 없음) | ✅ PASS | `{"error":"OPENAI_API_KEY not set"}` 400 반환 |
| `/` index.html | ✅ PASS | 다크 테마 SPA 렌더링, CSS/JS 로드 정상 |
| 런 시작 → SSE → 완료 | ⚠️ SKIP | 실제 LLM API 키 없어서 400 에러만 확인 |
| 정지 버튼 | ⚠️ SKIP | 실제 실행 없이 확인 불가 |
| 히스토리 리포트 열기 | ⚠️ SKIP | results_dir에 complete_report.md 없음 |
| 차트 탭 | ⚠️ SKIP | 실제 런 완료 후 loadChart() 호출 필요 |

### 발견 이슈

- **히스토리 없음:** results_dir에 완전한 런 결과(complete_report.md)가 없어 리포트 열기/비교 테스트는 불가. 이는 정상 동작이며 실제 런 후 확인 가능.
- **결정 파일 없음:** 일부 히스토리 항목에 `final_trade_decision.md`가 없어 decision이 null. 정상 동작.

### 회귀 테스트

```
pytest tests/ → 611 passed, 2 skipped
```
