"""Tests for webapp/runner.py (Card 01)."""
import sys
import types

import pytest

# Ensure runner can be imported (catches fastapi leakage)
import webapp.runner as runner
from webapp.runner import RunRequest, start_run


def test_no_fastapi_import():
    assert "fastapi" not in sys.modules


class FakeGraph:
    class graph:
        @staticmethod
        def stream(initial_state, **kwargs):
            yield {
                "messages": [],
                "market_report": "Market looks good",
            }
            yield {
                "messages": [],
                "investment_debate_state": {
                    "bull_history": "Bull case",
                    "bear_history": "Bear case",
                    "judge_decision": "Buy",
                },
            }
            yield {
                "messages": [],
                "trader_investment_plan": "Plan",
            }
            yield {
                "messages": [],
                "risk_debate_state": {
                    "aggressive_history": "Agg",
                    "conservative_history": "Cons",
                    "neutral_history": "Neu",
                    "judge_decision": "Final BUY",
                },
            }


class FakeTradingAgentsGraph:
    def __init__(self, *a, **k):
        self.propagator = types.SimpleNamespace(
            create_initial_state=lambda *a, **k: {},
            get_graph_args=lambda *a, **k: {},
        )
        self.graph = FakeGraph.graph

    def resolve_instrument_context(self, *a, **k):
        return ""


@pytest.fixture(autouse=True)
def patch_graph_and_reporting(monkeypatch):
    monkeypatch.setattr(
        "tradingagents.graph.trading_graph.TradingAgentsGraph", FakeTradingAgentsGraph
    )
    monkeypatch.setattr(
        "webapp.runner.TradingAgentsGraph", FakeTradingAgentsGraph
    )
    monkeypatch.setattr(
        "tradingagents.reporting.write_report_tree", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "tradingagents.reporting.parse_decision", lambda text: "BUY"
    )
    monkeypatch.setattr(
        "webapp.runner.parse_decision", lambda text: "BUY"
    )


def _collect_events(handle, timeout=5):
    handle.thread.join(timeout=timeout)
    events = []
    while not handle.events.empty():
        events.append(handle.events.get_nowait())
    return events


def test_fake_stream_emits_contract_events():
    req = RunRequest(
        ticker="FAKE",
        analysis_date="2026-01-01",
        analysts=["market"],
        research_depth=1,
        llm_provider="openai",
        backend_url="https://api.openai.com/v1",
        shallow_thinker="gpt-4o-mini",
        deep_thinker="gpt-4o",
    )
    handle = start_run(req)
    events = _collect_events(handle)

    types_seen = {e["type"] for e in events}
    assert "status" in types_seen
    assert "report" in types_seen
    assert "stats" in types_seen

    done = [e for e in events if e["type"] == "done"]
    assert len(done) == 1
    assert done[0]["status"] == "completed"
    assert done[0]["decision"] == "BUY"
    assert done[0]["path"] == "results/FAKE/2026-01-01"


def test_stop_event_emits_stopped():
    class StoppingFakeGraph:
        class graph:
            @staticmethod
            def stream(initial_state, **kwargs):
                yield {"messages": []}
                import time
                time.sleep(0.1)
                yield {"messages": []}

    class StoppingFakeTAG:
        def __init__(self, *a, **k):
            self.propagator = types.SimpleNamespace(
                create_initial_state=lambda *a, **k: {},
                get_graph_args=lambda *a, **k: {},
            )
            self.graph = StoppingFakeGraph.graph

        def resolve_instrument_context(self, *a, **k):
            return ""

    # Patch runner's local reference directly
    original = runner.TradingAgentsGraph
    runner.TradingAgentsGraph = StoppingFakeTAG
    try:
        req = RunRequest(
            ticker="STOP",
            analysis_date="2026-01-01",
            analysts=["market"],
            research_depth=1,
            llm_provider="openai",
            backend_url="https://api.openai.com/v1",
            shallow_thinker="gpt-4o-mini",
            deep_thinker="gpt-4o",
        )
        handle = start_run(req)
        import time
        time.sleep(0.05)
        handle.stop_event.set()
        events = _collect_events(handle)

        done = [e for e in events if e["type"] == "done"]
        assert len(done) == 1
        assert done[0]["status"] == "stopped"
    finally:
        runner.TradingAgentsGraph = original
