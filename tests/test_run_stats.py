"""Measured usage must survive analysis, persistence and report rendering."""

import json
from contextlib import nullcontext
from unittest.mock import MagicMock
from uuid import uuid4

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.llm_clients.codex_client import _parse_usage
from tradingagents.reporting import format_analysis_stats, write_report_tree
from tradingagents.run_stats import StatsCallbackHandler


def response(usage=None, raw=None):
    return LLMResult(generations=[[ChatGeneration(message=AIMessage(
        content="OK", usage_metadata=usage,
    ))]], llm_output=raw)


def complete(stats, usage=None, raw=None, run_id=None):
    run_id = run_id or uuid4()
    stats.on_chat_model_start({}, [[]], run_id=run_id)
    stats.on_llm_end(response(usage, raw), run_id=run_id)


def test_sum_dedup_and_cache_subset(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("tradingagents.run_stats.time.monotonic", lambda: clock[0])
    stats = StatsCallbackHandler()
    usage = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
             "input_token_details": {"cache_read": 70}}
    run_id = uuid4()
    complete(stats, usage, run_id=run_id)
    complete(stats, usage, run_id=run_id)  # both model and graph bindings
    complete(stats, raw={"token_usage": {"prompt_tokens": 50, "completion_tokens": 5, "total_tokens": 55}})
    clock[0] += 65.25
    result = stats.get_stats()
    assert result["llm_calls"] == result["usage_calls"] == 2
    assert result["total_tokens"] == 175
    assert result["cached_input_tokens"] == 70
    assert result["elapsed_seconds"] == 65.25
    assert "1m 5.2s" in format_analysis_stats(result)
    stats.reset()
    assert stats.get_stats()["total_tokens"] == 0
    assert stats.get_stats()["elapsed_seconds"] == 0


def test_missing_usage_and_errors_are_not_zero():
    stats = StatsCallbackHandler()
    complete(stats)
    stats.on_chat_model_start({}, [[]], run_id=uuid4())  # failed call
    snapshot = stats.get_stats()
    assert snapshot["missing_usage_calls"] == 2
    assert "Unavailable" in format_analysis_stats(snapshot)
    complete(stats, {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7})
    assert "Recorded tokens (partial)" in format_analysis_stats(stats.get_stats())
    assert "not recorded" in format_analysis_stats(None)


def test_codex_event_parser():
    events = '\n'.join([
        'not JSON', '[]', '{"type":"turn.started"}',
        '{"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":60,"output_tokens":20}}',
        '{"type":"turn.completed","usage":{"input_tokens":30,"output_tokens":5}}',
        '{"type":"turn.completed","usage":{"input_tokens":null}}',
    ])
    assert _parse_usage(events) == {
        "input_tokens": 130, "output_tokens": 25, "total_tokens": 155,
        "input_token_details": {"cache_read": 60},
    }
    assert _parse_usage('{"type":"turn.failed"}') is None


def test_propagate_stats_saved_and_reset(tmp_path):
    # Exercise the real propagate/_run_graph/_log_state/report path with no network.
    graph = object.__new__(TradingAgentsGraph)
    graph.stats_handler = StatsCallbackHandler()
    graph.config = {"results_dir": str(tmp_path)}
    graph.log_states_dict = {}
    graph.debug = False
    graph._resuming = False
    graph.memory_log = MagicMock()
    graph._resolve_pending_entries = MagicMock()
    graph.resolve_instrument_context = MagicMock(return_value="TEST")
    graph.checkpoint_scope = lambda *a: nullcontext(None)
    graph.checkpoint_input = lambda state: state
    graph.clear_checkpoint_on_success = MagicMock()
    graph.propagator = MagicMock()
    graph.propagator.get_graph_args.return_value = {}
    state = {
        "company_of_interest": "TEST", "trade_date": "2026-09-09",
        "market_report": "Market", "sentiment_report": "", "news_report": "",
        "fundamentals_report": "", "trader_investment_plan": "Plan",
        "investment_plan": "Plan", "final_trade_decision": "**Rating**: Hold",
        "investment_debate_state": dict.fromkeys(
            ["bull_history", "bear_history", "history", "current_response", "judge_decision"], ""),
        "risk_debate_state": dict.fromkeys(
            ["aggressive_history", "conservative_history", "neutral_history", "history", "judge_decision"], ""),
    }

    def invoke(*a, **kw):
        complete(graph.stats_handler, {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200})
        return state.copy()

    graph.graph = MagicMock()
    graph.graph.invoke.side_effect = invoke
    graph.process_signal = lambda _: "Hold"
    for _ in range(2):
        final, signal = graph.propagate("TEST", "2026-09-09")
        assert final["analysis_stats"]["total_tokens"] == 1200
        assert final["analysis_stats"]["llm_calls"] == 1
    log = json.loads(next(tmp_path.rglob("full_states_log_*.json")).read_text())
    assert log["analysis_stats"] == final["analysis_stats"]
    report = graph.save_reports(final, "TEST", save_path=tmp_path / "report").read_text()
    assert "| Total tokens | 1,200 |" in report
    assert "| Elapsed time |" in report
    old_time = final["analysis_stats"]["elapsed_seconds"]
    complete(graph.stats_handler, {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2})
    assert graph.stats_handler.get_stats()["total_tokens"] == 1202
    assert final["analysis_stats"]["total_tokens"] == 1200
    assert final["analysis_stats"]["elapsed_seconds"] == old_time


def test_resumed_and_legacy_reports(tmp_path):
    stats = StatsCallbackHandler().get_stats()
    stats["resumed"] = True
    text = write_report_tree({"analysis_stats": stats}, "TEST", tmp_path).read_text()
    assert "earlier executions are NOT included" in text
    assert "| Total tokens | 0 |" in text
    assert "not recorded" in write_report_tree({}, "TEST", tmp_path).read_text()
