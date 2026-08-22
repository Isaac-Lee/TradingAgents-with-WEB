"""Headless stream runner: TradingAgentsGraph -> Queue events for SSE."""

from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from cli.main import (
    ANALYST_ORDER,
    ANALYST_REPORT_MAP,
    MessageBuffer,
    classify_message_type,
    update_analyst_statuses,
    update_research_team_status,
)
from cli.stats_handler import StatsCallbackHandler
from cli.utils import detect_asset_type
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.analyst_execution import (
    AnalystWallTimeTracker,
    build_analyst_execution_plan,
    get_initial_analyst_node,
    sync_analyst_tracker_from_chunk,
)
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reporting import parse_decision, write_report_tree


@dataclass
class RunRequest:
    """POST /api/runs body."""

    ticker: str
    analysis_date: str
    analysts: list[str]
    research_depth: int
    llm_provider: str
    backend_url: str
    shallow_thinker: str
    deep_thinker: str
    output_language: str = "English"


@dataclass
class RunHandle:
    run_id: str
    events: "queue.Queue[dict]"
    stop_event: threading.Event
    thread: threading.Thread


def _build_config(request: RunRequest) -> dict:
    """Assemble run config from request, honoring env precedence."""
    config = DEFAULT_CONFIG.copy()
    if not os.environ.get("TRADINGAGENTS_MAX_DEBATE_ROUNDS"):
        config["max_debate_rounds"] = request.research_depth
    if not os.environ.get("TRADINGAGENTS_MAX_RISK_ROUNDS"):
        config["max_risk_discuss_rounds"] = request.research_depth
    config["quick_think_llm"] = request.shallow_thinker
    config["deep_think_llm"] = request.deep_thinker
    config["backend_url"] = request.backend_url
    config["llm_provider"] = request.llm_provider.lower()
    config["output_language"] = request.output_language
    return config


def _emit_status_events(
    buf: MessageBuffer,
    prev_status: dict[str, str],
    events: queue.Queue[dict],
) -> dict[str, str]:
    """Compare current agent_status with previous and emit status events."""
    new_status = dict(buf.agent_status)
    for agent, state in new_status.items():
        if prev_status.get(agent) != state:
            events.put({"type": "status", "agent": agent, "state": state})
    return new_status


def _emit_report_events(
    buf: MessageBuffer,
    prev_reports: dict[str, str | None],
    events: queue.Queue[dict],
) -> dict[str, str | None]:
    """Compare current report_sections with previous and emit report events."""
    new_reports = dict(buf.report_sections)
    for section, content in new_reports.items():
        if content is not None and prev_reports.get(section) != content:
            events.put({"type": "report", "section": section, "content": content})
    return new_reports


def _run_worker(request: RunRequest, handle: RunHandle) -> None:
    """Worker thread body."""
    events = handle.events
    stop_event = handle.stop_event
    start_time = time.time()

    try:
        # 1. Config & graph setup
        config = _build_config(request)
        asset_type = detect_asset_type(request.ticker).value
        selected_analyst_keys = [a for a in ANALYST_ORDER if a in request.analysts]
        analyst_execution_plan = build_analyst_execution_plan(selected_analyst_keys)
        analyst_wall_time_tracker = AnalystWallTimeTracker(analyst_execution_plan)

        stats_handler = StatsCallbackHandler()
        graph = TradingAgentsGraph(
            selected_analyst_keys,
            config=config,
            debug=True,
            callbacks=[stats_handler],
        )

        # 2. Own MessageBuffer (not the module global)
        buf = MessageBuffer()
        buf.init_for_analysis(selected_analyst_keys)

        # 3. Initial state
        instrument_context = graph.resolve_instrument_context(request.ticker, asset_type)
        init_agent_state = graph.propagator.create_initial_state(
            request.ticker,
            request.analysis_date,
            asset_type=asset_type,
            instrument_context=instrument_context,
        )
        args = graph.propagator.get_graph_args(callbacks=[stats_handler])

        # 4. Initial status
        first_analyst = get_initial_analyst_node(analyst_execution_plan)
        buf.update_agent_status(first_analyst, "in_progress")
        analyst_wall_time_tracker.mark_started(selected_analyst_keys[0])

        prev_status: dict[str, str] = {}
        prev_reports: dict[str, str | None] = {}
        prev_status = _emit_status_events(buf, prev_status, events)

        # 5. Stream loop
        trace: list[dict] = []
        for chunk in graph.graph.stream(init_agent_state, **args):
            if stop_event.is_set():
                events.put({"type": "done", "status": "stopped"})
                return

            # Messages
            for message in chunk.get("messages", []):
                msg_id = getattr(message, "id", None)
                if msg_id is not None:
                    if msg_id in buf._processed_message_ids:
                        continue
                    buf._processed_message_ids.add(msg_id)

                msg_type, content = classify_message_type(message)
                if content and content.strip():
                    buf.add_message(msg_type, content)
                    events.put({"type": "message", "kind": msg_type, "text": content})

                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if isinstance(tool_call, dict):
                            events.put(
                                {
                                    "type": "tool",
                                    "name": tool_call["name"],
                                    "args": tool_call["args"],
                                }
                            )
                            buf.add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            events.put(
                                {
                                    "type": "tool",
                                    "name": tool_call.name,
                                    "args": tool_call.args,
                                }
                            )
                            buf.add_tool_call(tool_call.name, tool_call.args)

            # Analyst statuses
            update_analyst_statuses(
                buf,
                chunk,
                wall_time_tracker=analyst_wall_time_tracker,
            )

            # Research Team
            if chunk.get("investment_debate_state"):
                debate_state = chunk["investment_debate_state"]
                bull_hist = debate_state.get("bull_history", "").strip()
                bear_hist = debate_state.get("bear_history", "").strip()
                judge = debate_state.get("judge_decision", "").strip()

                if bull_hist or bear_hist:
                    update_research_team_status("in_progress", buffer=buf)
                if bull_hist:
                    buf.update_report_section(
                        "investment_plan", f"### Bull Researcher Analysis\n{bull_hist}"
                    )
                if bear_hist:
                    buf.update_report_section(
                        "investment_plan", f"### Bear Researcher Analysis\n{bear_hist}"
                    )
                if judge:
                    buf.update_report_section(
                        "investment_plan", f"### Research Manager Decision\n{judge}"
                    )
                    update_research_team_status("completed", buffer=buf)
                    buf.update_agent_status("Trader", "in_progress")

            # Trading Team
            if chunk.get("trader_investment_plan"):
                buf.update_report_section(
                    "trader_investment_plan", chunk["trader_investment_plan"]
                )
                if buf.agent_status.get("Trader") != "completed":
                    buf.update_agent_status("Trader", "completed")
                    buf.update_agent_status("Aggressive Analyst", "in_progress")

            # Risk Management Team
            if chunk.get("risk_debate_state"):
                risk_state = chunk["risk_debate_state"]
                agg_hist = risk_state.get("aggressive_history", "").strip()
                con_hist = risk_state.get("conservative_history", "").strip()
                neu_hist = risk_state.get("neutral_history", "").strip()
                judge = risk_state.get("judge_decision", "").strip()

                if agg_hist:
                    if buf.agent_status.get("Aggressive Analyst") != "completed":
                        buf.update_agent_status("Aggressive Analyst", "in_progress")
                    buf.update_report_section(
                        "final_trade_decision",
                        f"### Aggressive Analyst Analysis\n{agg_hist}",
                    )
                if con_hist:
                    if buf.agent_status.get("Conservative Analyst") != "completed":
                        buf.update_agent_status("Conservative Analyst", "in_progress")
                    buf.update_report_section(
                        "final_trade_decision",
                        f"### Conservative Analyst Analysis\n{con_hist}",
                    )
                if neu_hist:
                    if buf.agent_status.get("Neutral Analyst") != "completed":
                        buf.update_agent_status("Neutral Analyst", "in_progress")
                    buf.update_report_section(
                        "final_trade_decision",
                        f"### Neutral Analyst Analysis\n{neu_hist}",
                    )
                if judge and buf.agent_status.get("Portfolio Manager") != "completed":
                    buf.update_agent_status("Portfolio Manager", "in_progress")
                    buf.update_report_section(
                        "final_trade_decision",
                        f"### Portfolio Manager Decision\n{judge}",
                    )
                    buf.update_agent_status("Aggressive Analyst", "completed")
                    buf.update_agent_status("Conservative Analyst", "completed")
                    buf.update_agent_status("Neutral Analyst", "completed")
                    buf.update_agent_status("Portfolio Manager", "completed")

            # Emit diffs
            prev_status = _emit_status_events(buf, prev_status, events)
            prev_reports = _emit_report_events(buf, prev_reports, events)

            # Stats (once per chunk)
            stats = stats_handler.get_stats()
            events.put(
                {
                    "type": "stats",
                    "llm_calls": stats["llm_calls"],
                    "tokens": stats["tokens_in"] + stats["tokens_out"],
                    "elapsed_sec": round(time.time() - start_time, 1),
                }
            )

            trace.append(chunk)

        # 6. Merge final state
        final_state: dict = {}
        for chunk in trace:
            final_state.update(chunk)

        for agent in buf.agent_status:
            buf.update_agent_status(agent, "completed")
        prev_status = _emit_status_events(buf, prev_status, events)

        for section in buf.report_sections:
            if section in final_state:
                buf.update_report_section(section, final_state[section])
        prev_reports = _emit_report_events(buf, prev_reports, events)

        # 7. Save reports
        save_dir = Path(config["results_dir"]) / request.ticker / request.analysis_date
        write_report_tree(final_state, request.ticker, save_dir)

        decision_text = final_state.get("final_trade_decision", "")
        decision = parse_decision(decision_text)
        rel_path = f"{request.ticker}/{request.analysis_date}"

        events.put(
            {
                "type": "done",
                "status": "completed",
                "decision": decision,
                "path": rel_path,
            }
        )

    except Exception as exc:
        events.put({"type": "done", "status": "error", "message": str(exc)})


def start_run(request: RunRequest) -> RunHandle:
    """Start a headless analysis run in a background thread."""
    run_id = str(uuid.uuid4())
    events: queue.Queue[dict] = queue.Queue()
    stop_event = threading.Event()

    handle = RunHandle(
        run_id=run_id,
        events=events,
        stop_event=stop_event,
        thread=None,  # type: ignore[arg-type]
    )

    t = threading.Thread(target=_run_worker, args=(request, handle), daemon=True)
    handle.thread = t
    t.start()
    return handle
