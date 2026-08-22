# Card 02 — webapp/server.py 기반 + 옵션 API

**Blocked by:** 없음 (Card 01과 병렬 가능)

## 배경

FastAPI 앱의 골격과 폼 채우기용 정적 옵션 엔드포인트 2개. runs/SSE는 Card 03이
같은 파일에 이어서 구현하므로, 이 카드는 앱 팩토리/정적 마운트/옵션 API만 만든다.

## 작업

### `pyproject.toml`
`[project.optional-dependencies]`에 `web = ["fastapi", "uvicorn", "pywebview"]` 추가.
**core `dependencies`에 넣지 않는다** (보드 공통 규칙).

### `webapp/server.py`
- FastAPI app 생성. `webapp/static/`을 정적 파일로 마운트 (`/` → index.html).
  static 파일 자체는 Card 04에서 만들므로, 없어도 서버 기동은 되어야 한다
  (디렉토리 없으면 마운트 생략하는 가드 허용).
- uvicorn 진입점 `def main()` + `if __name__ == "__main__"`: host=`127.0.0.1` 고정,
  포트는 상수(예: 8765). 외부 바인딩 인자를 받지 않는다.
- `GET /api/options` — 계약 형태:
  ```json
  {"providers": [{"name","key","default_url"}], "analysts": [{"key","label"}],
   "research_depth": [{"label","value"}], "asset_types": ["stock","crypto"]}
  ```
  데이터 출처: `cli/utils.py`의 `_llm_provider_table()`(providers),
  `ANALYST_ORDER`(analysts), `select_research_depth()`의 선택지 테이블(research_depth).
  인터랙티브 프롬프트 함수를 그대로 호출하지 말고 **데이터 테이블만** 재사용한다.
  테이블이 프롬프트 함수 안에 갇혀 있으면 테이블을 모듈 수준으로 빼는 소규모
  리팩터를 `cli/utils.py`에 합다 (프롬프트 동작 변경 금지).
- `GET /api/options/models?provider=<key>&mode=quick|deep` → `[{"label","value"}]`.
  `cli/utils.py`의 `select_shallow_thinking_agent`/`select_deep_thinking_agent`가
  쓰는 모델 옵션 테이블 재사용 (동일하게 테이블 추출 리팩터 허용).
  잘못된 provider/mode → 400 `{"error": ...}`.
- 모든 실패 응답은 `{"error": "message"}` + 4xx/5xx (계약 공통).

## Acceptance

- [ ] `pip install -e ".[web]"` 후 `python -m uvicorn webapp.server:app` (또는 제공하는
  진입점)으로 기동, `curl 127.0.0.1:<port>/api/options`가 계약 JSON 반환.
- [ ] `curl '127.0.0.1:<port>/api/options/models?provider=openai&mode=quick'` →
  `[{"label","value"}, ...]`; `provider=bogus` → 400 `{"error":...}`.
- [ ] core 의존성에 fastapi/uvicorn/pywebview 없음 (`pyproject.toml` diff 확인).
- [ ] `pytest tests/` 통과 (cli/utils.py를 건드렸다면 특히 CLI 관련 테스트).
- [ ] 외부 바인딩 옵션 없음, 인증 없음(로컬 전용 전제 그대로).

## 금지

- runs/SSE/history/ohlcv 엔드포인트 구현 (후속 카드 범위).
- API 키를 응답에 포함하거나 요청으로 받는 코드.
