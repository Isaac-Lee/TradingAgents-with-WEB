"""Thread-safe per-execution usage, shared by CLI and Python analyses."""

import threading
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class StatsCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.llm_calls = self.tool_calls = 0
            self.tokens_in = self.tokens_out = self.total_tokens = 0
            self.cached_input_tokens = self.usage_calls = 0
            self._started = set()
            self._ended = set()
            self._started_at = time.monotonic()

    def _count_start(self, run_id):
        with self._lock:
            if run_id is not None:
                if run_id in self._started:
                    return
                self._started.add(run_id)
            self.llm_calls += 1

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._count_start(kwargs.get("run_id"))

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self._count_start(kwargs.get("run_id"))

    def on_llm_end(self, response, **kwargs):
        try:
            generation = response.generations[0][0]
        except (IndexError, TypeError):
            return
        usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
        if not usage:
            raw = (response.llm_output or {}).get("token_usage") or (response.llm_output or {}).get("usage")
            if raw and (("prompt_tokens" in raw and "completion_tokens" in raw)
                        or ("input_tokens" in raw and "output_tokens" in raw)):
                usage = {
                    "input_tokens": raw.get("input_tokens", raw.get("prompt_tokens", 0)),
                    "output_tokens": raw.get("output_tokens", raw.get("completion_tokens", 0)),
                }
                usage["total_tokens"] = raw.get("total_tokens", sum(usage.values()))
        with self._lock:
            run_id = kwargs.get("run_id")
            # A handler may be bound to both a model and the graph config.
            if run_id is not None:
                if run_id in self._ended:
                    return
                self._ended.add(run_id)
            if usage:
                self.tokens_in += usage.get("input_tokens", 0)
                self.tokens_out += usage.get("output_tokens", 0)
                self.total_tokens += usage.get("total_tokens", usage.get("input_tokens", 0) + usage.get("output_tokens", 0))
                self.cached_input_tokens += (usage.get("input_token_details") or {}).get("cache_read", 0)
                self.usage_calls += 1

    def on_tool_start(self, serialized, input_str, **kwargs):
        with self._lock:
            self.tool_calls += 1

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "llm_calls": self.llm_calls,
                "tool_calls": self.tool_calls,
                "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out,
                "total_tokens": self.total_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "usage_calls": self.usage_calls,
                "missing_usage_calls": max(0, self.llm_calls - self.usage_calls),
                "elapsed_seconds": time.monotonic() - self._started_at,
                "scope": "current_execution",
            }
