"""LangChain adapter for the ChatGPT-authenticated Codex CLI.

Codex produces a JSON message; LangGraph remains responsible for executing
market-data tools. No subscription tokens are read or sent to an API endpoint.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

from .base_client import BaseLLMClient


class CodexChatModel(BaseChatModel):
    """One isolated, non-interactive Codex invocation per chat-model call.

    ``model='default'`` lets Codex select its default subscription model.
    LangChain's inherited structured-output parser uses our tool binding.
    """

    model: str = "default"
    executable: str = "codex"
    timeout: float = Field(default=300, gt=0)
    reasoning_effort: str | None = None

    @property
    def _llm_type(self) -> str:
        return "codex-subscription"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": self.model, "reasoning_effort": self.reasoning_effort}

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        converted = [convert_to_openai_tool(tool) for tool in tools]
        return self.bind(tools=converted, tool_choice=tool_choice, **kwargs)

    def _run(self, command, *, env, cwd, input=None, timeout=None):
        try:
            result = subprocess.run(
                command, input=input, text=True, capture_output=True,
                env=env, cwd=cwd, timeout=timeout or self.timeout, check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Codex CLI not found. Install @openai/codex and run codex login.") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Codex request timed out; increase codex_timeout in config.") from exc
        if result.returncode:
            # CLI diagnostics can contain prompts or credentials. Do not copy
            # them into saved analysis reports or LangChain callbacks.
            raise RuntimeError(
                f"Codex CLI exited with code {result.returncode}. Check codex login status, "
                "CLI version, model access, network and subscription usage limits."
            )
        return result

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        if stop:
            raise ValueError("Codex does not support stop sequences.")
        executable = shutil.which(self.executable)
        if not executable:
            raise RuntimeError("Codex CLI not found. Install @openai/codex and run codex login.")
        # An inherited API key must never turn subscription mode into paid API usage.
        env = {k: v for k, v in os.environ.items()
               if k not in {"OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"}}
        tools = kwargs.get("tools", [])
        choice = kwargs.get("tool_choice")
        names = {t["function"]["name"] for t in tools}
        if isinstance(choice, dict):
            choice = choice["function"]["name"]
        if choice == "none":
            tools = []
        elif isinstance(choice, str) and choice not in {"auto", "any", "required"}:
            if choice not in names:
                raise ValueError(f"Unknown tool_choice: {choice}")
            tools = [t for t in tools if t["function"]["name"] == choice]
        required = choice not in (None, False, "auto", "none")
        names = {t["function"]["name"] for t in tools}
        # Arguments are a JSON string because application tool schemas can use
        # optional/arbitrary objects not accepted by Codex's strict JSON Schema.
        properties = {"content": {"type": "string"}}
        if tools:
            properties["tool_calls"] = {
                "type": "array", "items": {
                    "type": "object", "properties": {
                        "name": {"type": "string", "enum": sorted(names)},
                        "arguments": {"type": "string"},
                    }, "required": ["name", "arguments"], "additionalProperties": False,
                },
            }
        schema = {"type": "object", "properties": properties,
                  "required": list(properties), "additionalProperties": False}
        history = []
        for message in messages:
            record = {"role": message.type, "content": message.content}
            if isinstance(message, AIMessage) and message.tool_calls:
                record["tool_calls"] = message.tool_calls
            if getattr(message, "tool_call_id", None):
                record["tool_call_id"] = message.tool_call_id
            history.append(record)
        prompt = (
            "Act as the assistant in the conversation below. Honor its system messages. "
            "Use only supplied evidence and declared application tools. Do not use your "
            "own tools, files, skills or web search. Return the next assistant message "
            "in the output schema. For application tool calls, put each arguments object "
            "in a JSON-encoded string; the host executes these calls and returns results. "
            "Return an empty tool_calls array when no tool is needed. "
            + ("You MUST call at least one declared tool. " if required else "")
            + "\nApplication tools:\n" + json.dumps(tools, ensure_ascii=False)
            + "\nConversation:\n" + json.dumps(history, ensure_ascii=False)
        )
        with tempfile.TemporaryDirectory(prefix="tradingagents-codex-") as directory:
            auth = self._run([executable, "login", "status"], env=env, cwd=directory, timeout=30)
            if "logged in using chatgpt" not in (auth.stdout + auth.stderr).lower():
                raise RuntimeError("Codex subscription mode requires ChatGPT login. Run codex login.")
            schema_path = Path(directory) / "schema.json"
            output_path = Path(directory) / "response.json"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            command = [
                executable, "exec", "--json", "--ignore-user-config", "--ephemeral",
                "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never",
                "-c", 'forced_login_method="chatgpt"', "-c", 'model_provider="openai"',
                "-c", 'approval_policy="never"', "-c", 'web_search="disabled"',
                "-c", "features.shell_tool=false", "-c", "features.unified_exec=false",
                "-c", "project_doc_max_bytes=0",
                "--output-schema", str(schema_path), "--output-last-message", str(output_path),
            ]
            if self.model != "default":
                command += ["--model", self.model]
            if self.reasoning_effort:
                command += ["-c", "model_reasoning_effort=" + json.dumps(self.reasoning_effort)]
            execution = self._run(command + ["-"], env=env, cwd=directory, input=prompt)
            usage = _parse_usage(execution.stdout)
            try:
                payload = json.loads(output_path.read_text(encoding="utf-8"))
                content = payload["content"]
                if not isinstance(content, str):
                    raise ValueError("content must be text")
                calls = []
                for call in payload.get("tool_calls", []):
                    args = json.loads(call["arguments"])
                    if call["name"] not in names or not isinstance(args, dict):
                        raise ValueError("invalid tool call")
                    calls.append({"name": call["name"], "args": args, "id": uuid4().hex})
                if required and not calls:
                    raise ValueError("required tool call missing")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise RuntimeError("Codex returned an invalid response or tool call.") from exc
        return ChatResult(generations=[ChatGeneration(message=AIMessage(
            content=content, tool_calls=calls, usage_metadata=usage,
        ))])


def _parse_usage(stdout: str) -> dict | None:
    """Cached tokens are a subset of input, not additional tokens."""
    total = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if not isinstance(usage, dict) or not all(
            type(usage.get(key)) is int and usage[key] >= 0
            for key in ("input_tokens", "output_tokens")
        ):
            continue
        if total is None:
            total = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                     "input_token_details": {"cache_read": 0}}
        total["input_tokens"] += usage["input_tokens"]
        total["output_tokens"] += usage["output_tokens"]
        total["total_tokens"] += usage["input_tokens"] + usage["output_tokens"]
        cached = usage.get("cached_input_tokens", 0)
        if type(cached) is int and cached >= 0:
            total["input_token_details"]["cache_read"] += cached
    return total


class CodexClient(BaseLLMClient):
    def validate_model(self) -> bool:
        return bool(self.model and self.model.strip())

    def get_llm(self) -> CodexChatModel:
        if self.base_url:
            raise ValueError("Codex subscription mode does not use backend_url; unset it.")
        if not self.validate_model():
            raise ValueError("Set a Codex model ID or use 'default'.")
        for key in ("temperature", "max_tokens", "max_retries"):
            if self.kwargs.get(key) is not None:
                warnings.warn(f"Codex CLI does not expose {key}; the setting is ignored.", RuntimeWarning, stacklevel=2)
        return CodexChatModel(
            model=self.model,
            executable=self.kwargs.get("codex_command", "codex"),
            timeout=self.kwargs.get("codex_timeout", 300),
            reasoning_effort=self.kwargs.get("reasoning_effort"),
            callbacks=self.kwargs.get("callbacks"),
        )
