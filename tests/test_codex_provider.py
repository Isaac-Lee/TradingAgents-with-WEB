"""Codex subprocess contract, LangChain tool loop, and subscription isolation."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from tradingagents.llm_clients.codex_client import CodexChatModel
from tradingagents.llm_clients.factory import create_llm_client


def test_subprocess_unicode_round_trip(tmp_path):
    result = CodexChatModel()._run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.stderr.buffer.write('시장 분석'.encode('utf-8'))"],
        env=os.environ.copy(), cwd=tmp_path, input="ORCL 한글 분석 📊",
    )
    assert result.stdout == "ORCL 한글 분석 📊"
    assert result.stderr == "시장 분석"


@tool
def quote(symbol: str) -> str:
    """Return a deterministic test quote."""
    return f"{symbol}: 100"


@pytest.fixture
def cli(monkeypatch):
    calls = []
    responses = []
    monkeypatch.setattr("shutil.which", lambda _: "/bin/codex")

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1:3] == ["login", "status"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="Logged in using ChatGPT")
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(response))
        usage_event = {"type": "turn.completed", "usage": {
            "input_tokens": 100, "output_tokens": 20, "cached_input_tokens": 60,
        }}
        return SimpleNamespace(returncode=0, stdout=json.dumps(usage_event), stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    return calls, responses


def test_factory_and_plain_prompt_isolation(cli, monkeypatch):
    calls, responses = cli
    monkeypatch.setenv("CODEX_API_KEY", "do-not-forward")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://unused.invalid")
    responses.append({"content": "hello"})
    model = create_llm_client("Codex", "default").get_llm()
    chain = ChatPromptTemplate.from_messages([("system", "Be concise"), ("human", "{text}")]) | model
    result = chain.invoke({"text": "Hello"})
    assert result.content == "hello"
    assert result.usage_metadata["total_tokens"] == 120
    assert result.usage_metadata["input_token_details"]["cache_read"] == 60
    command, kwargs = calls[-1]
    assert "--model" not in command
    assert "--ignore-user-config" in command
    assert "--json" in command
    assert 'forced_login_method="chatgpt"' in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "features.shell_tool=false" in command
    assert "features.unified_exec=false" in command
    assert 'web_search="disabled"' in command
    assert not {"OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"} & kwargs["env"].keys()
    assert "Be concise" in kwargs["input"]
    assert not Path(kwargs["cwd"]).exists()


def test_langgraph_tool_round_trip(cli):
    calls, responses = cli
    responses.extend([
        {"content": "", "tool_calls": [{"name": "quote", "arguments": '{"symbol":"TEST"}'}]},
        {"content": "TEST is 100", "tool_calls": []},
    ])
    model = CodexChatModel().bind_tools([quote])
    first = model.invoke([HumanMessage("Look up TEST")])
    assert isinstance(first, AIMessage)
    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode([quote]))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    result = graph.compile().invoke({"messages": [first]})["messages"][-1]
    assert isinstance(result, ToolMessage)
    assert result.content == "TEST: 100"
    assert model.invoke([HumanMessage("Look up TEST"), first, result]).content == "TEST is 100"
    assert first.tool_calls[0]["id"] in calls[-1][1]["input"]


def test_pydantic_structured_output(cli):
    _, responses = cli

    class Decision(BaseModel):
        action: str
        confidence: float

    responses.append({"content": "", "tool_calls": [{
        "name": "Decision", "arguments": '{"action":"HOLD","confidence":0.8}',
    }]})
    result = CodexChatModel().with_structured_output(Decision).invoke("Decide")
    assert isinstance(result, Decision)
    assert result.confidence == 0.8


@pytest.mark.parametrize("payload", [
    {"content": 123},
    {"content": "", "tool_calls": [{"name": "unknown", "arguments": "{}"}]},
    {"content": "", "tool_calls": [{"name": "quote", "arguments": "bad json"}]},
    {"content": "", "tool_calls": [{"name": "quote", "arguments": "[]"}]},
    {"content": "", "tool_calls": []},
])
def test_invalid_or_missing_required_tool_rejected(cli, payload):
    cli[1].append(payload)
    with pytest.raises(RuntimeError, match="invalid response"):
        CodexChatModel().bind_tools([quote], tool_choice="required").invoke("Test")


def test_timeout(cli):
    cli[1].append(subprocess.TimeoutExpired("codex", 1))
    with pytest.raises(RuntimeError, match="timed out"):
        CodexChatModel(timeout=1).invoke("Test")


def test_callback_forwarding(cli):
    completed = []

    class Handler(BaseCallbackHandler):
        def on_llm_end(self, response, **kwargs):
            completed.append(response)

    cli[1].append({"content": "OK"})
    model = create_llm_client("codex", "default", callbacks=[Handler()]).get_llm()
    model.invoke("Test")
    assert len(completed) == 1


def test_cli_error_does_not_expose_diagnostics(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/bin/codex")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=1, stdout="", stderr="sensitive diagnostic",
    ))
    with pytest.raises(RuntimeError, match="exited with code 1") as error:
        CodexChatModel().invoke("Test")
    assert "sensitive" not in str(error.value)


def test_explicit_model_and_effort(cli):
    cli[1].append({"content": "OK"})
    CodexChatModel(model="test-model", reasoning_effort="low").invoke("Test")
    assert "test-model" in cli[0][-1][0]
    assert 'model_reasoning_effort="low"' in cli[0][-1][0]


def test_missing_cli(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="CLI not found"):
        CodexChatModel().invoke("Test")


def test_api_login_rejected(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/bin/codex")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="Logged in using an API key")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(RuntimeError, match="requires ChatGPT login"):
        CodexChatModel().invoke("Test")
    assert len(calls) == 1


def test_config_cli_registration():
    from cli.utils import ensure_api_key, provider_default_url
    from tradingagents.default_config import DEFAULT_CONFIG, _apply_env_overrides
    from tradingagents.llm_clients.model_catalog import get_model_options

    assert ensure_api_key("codex") is None
    assert provider_default_url("codex") is None
    assert get_model_options("codex", "quick")[0][1] == "default"
    assert _apply_env_overrides(DEFAULT_CONFIG.copy())["codex_timeout"] > 0


def test_backend_url_rejected():
    with pytest.raises(ValueError, match="backend_url"):
        create_llm_client("codex", "default", base_url="https://unused.invalid").get_llm()


def test_graph_config_and_env_forwarding(monkeypatch):
    from tradingagents.default_config import DEFAULT_CONFIG, _apply_env_overrides
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    monkeypatch.setenv("TRADINGAGENTS_CODEX_TIMEOUT", "42.5")
    monkeypatch.setenv("TRADINGAGENTS_CODEX_COMMAND", "/custom/codex")
    config = _apply_env_overrides(DEFAULT_CONFIG.copy())
    config.update(llm_provider="codex", openai_reasoning_effort="low")
    graph = object.__new__(TradingAgentsGraph)
    graph.config = config
    kwargs = graph._get_provider_kwargs()
    assert kwargs["codex_timeout"] == 42.5
    assert kwargs["codex_command"] == "/custom/codex"
    assert kwargs["reasoning_effort"] == "low"


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("TRADINGAGENTS_CODEX_LIVE_TEST") != "1", reason="Consumes Codex subscription usage")
def test_live_codex_tool_and_structured_output():
    """Opt in with TRADINGAGENTS_CODEX_LIVE_TEST=1; no market-data requests."""
    from tradingagents.run_stats import StatsCallbackHandler

    stats = StatsCallbackHandler()
    model = CodexChatModel(timeout=120, callbacks=[stats])
    first = model.bind_tools([quote], tool_choice="quote").invoke("Get the quote for TEST.")
    assert first.tool_calls[0]["name"] == "quote"
    assert first.tool_calls[0]["args"] == {"symbol": "TEST"}
    assert first.usage_metadata["total_tokens"] > 0
    graph = StateGraph(MessagesState)
    graph.add_node("tools", ToolNode([quote]))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    result = graph.compile().invoke({"messages": [first]})["messages"][-1]

    class QuoteSummary(BaseModel):
        symbol: str
        price: int

    summary = model.with_structured_output(QuoteSummary).invoke([
        HumanMessage("Get TEST's quote and summarize its symbol and price."), first, result,
    ])
    assert summary == QuoteSummary(symbol="TEST", price=100)
    usage = stats.get_stats()
    assert usage["usage_calls"] == usage["llm_calls"] == 2
    assert usage["total_tokens"] > first.usage_metadata["total_tokens"]
    assert usage["missing_usage_calls"] == 0
    assert usage["elapsed_seconds"] > 0
