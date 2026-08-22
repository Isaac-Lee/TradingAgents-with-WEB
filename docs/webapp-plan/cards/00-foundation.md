# Card 00 — 기반 리팩터 (CLI 재사용 준비)

**Blocked by:** 없음. 제일 먼저 잡을 것.

## 배경

`cli/main.py`의 `update_research_team_status(status)`가 모듈 전역 `message_buffer`를
직접 참조한다. 웹앱은 런마다 자신만의 `MessageBuffer` 인스턴스를 만들어야 하므로
(동시에 여러 브라우저 탭에서 같은 전역을 공유하면 안 됨), 이 함수를 파라미터화해야
`webapp/runner.py`(Card 01)가 재사용할 수 있다.

리포트 히스토리 목록/뱃지에 BUY/SELL/HOLD를 보여주려면(`GET /api/history`,
`docs/webapp-plan/01-API-CONTRACT.md`) `final_trade_decision.md` 텍스트에서 결정을
뽑는 파서가 필요한데 지금 `tradingagents/reporting.py`에 없다.

## 작업

### 1. `cli/main.py`
`update_research_team_status`를 다음으로 바꾼다 (동작은 동일, 기본값으로 기존 호출부
전부 그대로 동작):

```python
def update_research_team_status(status, buffer=message_buffer):
    """Update status for research team members (not Trader)."""
    research_team = ["Bull Researcher", "Bear Researcher", "Research Manager"]
    for agent in research_team:
        buffer.update_agent_status(agent, status)
```
기존 호출부(`update_research_team_status(status)`)는 수정하지 않는다 — 기본 인자로
그대로 동작해야 한다.

### 2. `tradingagents/reporting.py`
파일 끝에 추가:

```python
import re

_DECISION_RE = re.compile(r"\b(BUY|SELL|HOLD)\b", re.IGNORECASE)


def parse_decision(text: str | None) -> str | None:
    """Extract BUY/SELL/HOLD from a final_trade_decision text, or None if absent."""
    if not text:
        return None
    match = _DECISION_RE.search(text)
    return match.group(1).upper() if match else None
```
등장하는 첫 번째 BUY/SELL/HOLD 토큰을 쓴다 — Portfolio Manager 리포트가 대체로
결론을 앞부분에 명시하는 스타일이라 이걸로 충분하다. 못 찾으면 `None`, 호출부(카드 05)
에서 `null`/"N/A"로 처리한다.

## Acceptance

- `tradingagents analyze` 실행 시 기존과 동일하게 동작 (회귀 없음).
- `parse_decision("...final decision: **BUY**...")` → `"BUY"`.
- `parse_decision("no clear signal")` → `None`.
- 최소 검증: `python -c` 한 줄로 위 두 케이스 확인하거나 `tests/`에 짧은 테스트 추가.
  기존 테스트 스위트(`pytest`)가 있다면 그것도 통과해야 함.
