# TradingAgents 웹앱 사용 가이드

CLI(`tradingagents analyze`)와 동일한 분석을 로컬 웹 UI / 데스크탑 창에서 실행한다.
기존 CLI의 그래프 스트리밍 루프와 `MessageBuffer`를 그대로 재사용하므로 분석 결과와
리포트 파일 구조는 CLI와 동일하다.

## 1. 설치

웹 관련 패키지는 선택 의존성이다. CLI만 쓰는 사용자에게 설치를 강요하지 않는다.

```bash
pip install -e ".[web]"
```

`fastapi`, `uvicorn`, `pywebview` 세 개가 설치된다. 브라우저에서만 쓸 거라면
`pywebview`는 없어도 되고, 데스크탑 창을 띄우려면 필요하다.

## 2. API 키 설정

**API 키는 웹 UI에서 입력하지 않는다.** 서버 프로세스의 환경변수에서만 읽는다.
저장소 루트의 `.env` 파일에 넣거나 셸에서 export 한다.

```bash
cp .env.example .env   # 파일이 있다면
```

`.env` 예시 (쓰는 프로바이더 것만 채우면 된다):

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

키가 없는 상태로 실행을 시작하면 서버가 400과 함께
`{"error": "OPENAI_API_KEY not set"}`를 돌려주고, UI 상단에 에러 배너가 뜬다.
Ollama나 로컬 OpenAI 호환 서버처럼 키가 필요 없는 프로바이더는 키 없이 진행된다.

## 3. 실행

**중요: 저장소 루트에서 실행해야 한다.** 현재 `webapp` 패키지는 설치 대상에 포함되어
있지 않아 (`pyproject.toml`의 `packages.find`), 다른 디렉토리에서는 임포트되지 않는다.

### 데스크탑 창으로 (권장)

```bash
python -m webapp.desktop
```

서버를 백그라운드 스레드로 띄우고 준비되면 네이티브 창을 연다. 포트 8765가 이미
사용 중이면 중복 실행으로 보고 종료한다.

### 브라우저로

```bash
python -m uvicorn webapp.server:app --host 127.0.0.1 --port 8765
```

띄운 뒤 http://127.0.0.1:8765 접속.

서버는 `127.0.0.1`에만 바인딩되고 인증이 없다. 로컬 전용이 전제이므로
`--host 0.0.0.0`으로 바꿔 외부에 노출하지 말 것.

## 4. 사용 흐름

1. **Ticker** — `AAPL`, `0700.HK`, `BTC-USD` 등. 크립토 접미사(`-USD`, `-USDT` 등)는
   자동으로 크립토 자산으로 판별된다.
2. **Analysis Date** — 분석 기준일. 이 날짜 이후 시세는 룩어헤드 방지를 위해 잘린다.
3. **Analysts** — Market / Sentiment / News / Fundamentals 중 최소 1개 선택.
   많이 고를수록 느리고 토큰을 더 쓴다.
4. **Research Depth** — 토론 라운드 수. Shallow가 가장 빠르고 싸다.
5. **LLM Provider / Backend URL** — 프로바이더를 고르면 기본 URL이 자동으로 채워진다.
6. **Shallow / Deep Thinker** — 프로바이더에 맞는 모델 목록이 자동으로 로드된다.
   Shallow는 툴 호출·요약용(싼 모델), Deep은 최종 판단용(비싼 모델).
7. **Output Language** — 리포트 출력 언어. `Korean`으로 바꾸면 한국어로 나온다.
8. **Start** — 실행 시작. 진행 상황이 실시간으로 흐른다.

실행 중 화면:

- **Agent Status** — 각 에이전트가 PENDING → IN PROGRESS → COMPLETED로 바뀐다.
- **리포트 탭** — 섹션이 완성되는 대로 해당 탭에 마크다운이 채워진다.
- **Messages & Tools** — LLM 추론 메시지와 툴 호출 로그.
- **하단 통계 바** — LLM 호출 수, 누적 토큰, 경과 시간.
- **Stop** — 다음 그래프 단계 경계에서 멈춘다. 즉시 멈추지 않고, 멈춘 런은
  리포트를 저장하지 않는다.

동시에 돌릴 수 있는 런은 1개다. 실행 중에 또 시작하면 409로 거절된다.

## 5. 결과 파일

CLI와 동일한 위치·구조로 저장된다. 기본 경로는 `results/`이고
`TRADINGAGENTS_RESULTS_DIR` 환경변수로 바꿀 수 있다.

```
results/AAPL/2026-08-22/
  1_analysts/    market.md  sentiment.md  news.md  fundamentals.md
  2_research/    bull.md  bear.md  manager.md
  3_trading/     trader.md
  4_risk/        aggressive.md  conservative.md  neutral.md
  5_portfolio/   decision.md
  complete_report.md
```

## 6. 차트

Chart 탭은 폼에 입력된 Ticker/Date 기준으로 5년치 일봉을 그린다. 데이터는 CLI가
쓰는 것과 같은 yfinance 캐시(`load_ohlcv`)를 재사용하므로 별도 API 키가 필요 없다.

런 완료 시 자동으로 그려지고, Chart 탭을 직접 클릭해도 즉시 로드된다.

## 7. 히스토리 / 비교

하단 **History** 카드에서 과거 런 목록을 본다. 각 행에 티커/날짜/결정 뱃지가 뜨고:

- **View** — 해당 런의 `complete_report.md`를 그 자리에서 펼쳐 본다.
- 체크박스로 2~4개 선택 후 **Compare Selected** — 선택한 런들의 리포트를 열별로
  나란히 띄운다.

새 런이 완료되면 목록이 자동 갱신된다. **Refresh**로 수동 갱신도 가능.

## 8. 알려진 제약

| 증상 | 영향 |
|---|---|
| 실행 중 브라우저 새로고침 | 진행 상황을 다시 받지 못한다 (이벤트 재생 버퍼 없음). 런 자체는 계속 진행되고 리포트는 정상 저장됨 |
| `pip install`은 반드시 저장소 루트에서 | `pyproject.toml`에 `webapp` 패키지가 포함되도록 고쳤으나, 개발 모드(`pip install -e .`)가 아니면 별도 검증 필요 |

## 9. 문제 해결

**포트가 이미 사용 중이라고 나올 때**

```bash
lsof -ti:8765 | xargs kill
```

**모델 목록이 비어 있을 때**
프로바이더를 다시 선택해 `/api/options/models` 호출을 재발생시킨다. OpenRouter는
모델 목록을 원격에서 가져오므로 네트워크가 필요하다.

**런이 즉시 에러로 끝날 때**
하단 배너의 에러 메시지를 확인한다. 대부분 API 키 누락, 잘못된 모델 ID,
백엔드 URL 오타다.

**CLI는 되는데 웹앱만 안 될 때**
CLI에만 있는 설정(추론 강도 `openai_reasoning_effort`, Google thinking level,
Anthropic effort)은 웹 UI에 노출되어 있지 않다. 필요하면 환경변수로 지정한다.

```
TRADINGAGENTS_OPENAI_REASONING_EFFORT=high
TRADINGAGENTS_GOOGLE_THINKING_LEVEL=high
TRADINGAGENTS_ANTHROPIC_EFFORT=high
```
