"""Offline stand-ins for the model client (tests, replay, dry runs). Same interface as router.models.LiveClient."""
from __future__ import annotations

import threading
from typing import Callable, Optional

from router.config import RouterConfig
from router.models import ModelReply, Prices, kind_of


class FakeClient:
    """handler(model, system, user, max_tokens, json_mode) -> str | ModelReply | Exception.
    A str becomes an ok reply with token counts ~ len/4 (so the cost maths is exercised); an Exception becomes an error reply."""

    def __init__(self, handler: Callable, prices: Optional[Prices] = None, latency_ms: int = 10):
        self.handler, self.latency_ms = handler, latency_ms
        self.prices = prices or Prices(RouterConfig().prices_path)
        self.calls = []
        self._lock = threading.Lock()

    def chat(self, model, system, user, max_tokens, timeout=None, json_mode=False) -> ModelReply:
        with self._lock:
            self.calls.append({"model": model, "system": system, "user": user, "max_tokens": max_tokens, "timeout": timeout, "json_mode": json_mode})
        try:
            out = self.handler(model, system, user, max_tokens, json_mode)
            if isinstance(out, Exception):
                raise out
        except Exception as e:  # noqa: BLE001
            return ModelReply(model, error=f"{type(e).__name__}: {e}", latency_ms=self.latency_ms)
        if isinstance(out, ModelReply):
            if out.cost_usd == 0.0 and out.error is None and kind_of(model) == "api":
                out.cost_usd = self.prices.cost(model, out.tokens_in, out.tokens_out)
            return out
        tin, tout = max(1, (len(system) + len(user)) // 4), max(1, len(out) // 4)
        return ModelReply(model, text=out, tokens_in=tin, tokens_out=tout, latency_ms=self.latency_ms, finish="stop",
                          cost_usd=self.prices.cost(model, tin, tout))

    def models_called(self) -> list:
        return [c["model"] for c in self.calls]
