"""One client for every model the router can call.

  local   Ollama /api/chat                      (name contains ':' e.g. gemma3:4b)  -> $0 marginal cost
  api     Fireworks / Hyde (OpenAI-compatible)  and Gemini (AI Studio)
Every call returns a ModelReply and NEVER raises: failures are in `error` (the pipeline treats them as "escalate").
Cost is always the list price in eval/model_prices.json (whoever served the call), as in the Phase 3 analysis.
Settings match eval/run_api.py (temperature 0, reasoning_effort low, same output budgets, reasoning tokens logged).
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from typing import Optional, Protocol

from router.config import RouterConfig

FW = "accounts/fireworks/models/"
# name -> (provider, api model id). The 8 paid models of D1.
API_MODELS = {
    "nemotron-lightning-3p5-30b-a3b": ("fireworks", FW + "nemotron-lightning-3p5-30b-a3b"),
    "gpt-oss-120b": ("fireworks", FW + "gpt-oss-120b"),
    "minimax-m3p1-flash": ("fireworks", FW + "minimax-m3p1-flash"),
    "deepseek-v4p1-flash": ("fireworks", FW + "deepseek-v4p1-flash"),
    "glm-5p3": ("fireworks", FW + "glm-5p3"),
    "kimi-k3p1-pro": ("fireworks", FW + "kimi-k3p1-pro"),
    "hyde/glm-5.3-flash": ("hyde", "hyde/glm-5.3-flash"),
    "gemini-3.1-flash-lite": ("gemini", "gemini-3.1-flash-lite"),
}


def kind_of(model: str) -> str:
    """Same rule as eval/phase4/io_phase3.py: an Ollama tag contains ':'."""
    return "local" if ":" in model else "api"


def is_known(model: str) -> bool:
    return kind_of(model) == "local" or model in API_MODELS


@dataclass
class ModelReply:
    model: str
    text: str = ""
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    tokens_reasoning: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_usd: float = 0.0
    finish: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 1

    @property
    def ok(self) -> bool:
        return self.error is None and bool((self.text or "").strip())

    def to_dict(self, with_text: bool = False) -> dict:
        d = asdict(self)
        if not with_text:
            d.pop("text")
        return d


class ModelClient(Protocol):
    def chat(self, model: str, system: str, user: str, max_tokens: int, timeout: Optional[float] = None, json_mode: bool = False) -> ModelReply: ...


class Prices:
    """List prices (USD per 1M tokens) from eval/model_prices.json. Local models cost $0 (marginal, D5)."""

    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)

    def per_million(self, model: str):
        if model in API_MODELS:
            prov, api_id = API_MODELS[model]
            p = self.data.get(prov, {}).get(api_id)
            if p:
                return p["input"], p["output"]
        raise KeyError(f"no list price for {model}")

    def cost(self, model: str, tin, tout) -> float:
        if kind_of(model) == "local":
            return 0.0
        pi, po = self.per_million(model)
        return ((tin or 0) * pi + (tout or 0) * po) / 1e6


class _Fail(Exception):
    def __init__(self, msg, retriable=True, rate_limited=False):
        super().__init__(msg)
        self.retriable, self.rate_limited = retriable, rate_limited


def _retriable_status(code: int) -> bool:
    return code in (408, 429) or code >= 500


class LiveClient:
    """Real network client (httpx for Ollama/Fireworks/Hyde, google-genai for Gemini). Thread-safe."""

    def __init__(self, cfg: Optional[RouterConfig] = None, sleep=time.sleep):
        self.cfg = cfg or RouterConfig()
        self.prices = Prices(self.cfg.prices_path)
        self._sleep = sleep
        self._gem_lock = threading.Lock()
        self._gem_last = 0.0
        self._gem = None

    # -------------------------------------------------- public
    def chat(self, model: str, system: str, user: str, max_tokens: int, timeout: Optional[float] = None, json_mode: bool = False) -> ModelReply:
        t0 = time.perf_counter()
        try:
            if kind_of(model) == "local":
                r = self._ollama(model, system, user, max_tokens, timeout or self.cfg.local_budget_s, json_mode)
            elif model in API_MODELS:
                fn = self._gemini if API_MODELS[model][0] == "gemini" else self._openai
                r = self._with_retries(model, lambda: fn(model, system, user, max_tokens, timeout or self.cfg.api_timeout_s))
            else:
                r = ModelReply(model, error=f"unknown model {model}")
        except Exception as e:  # noqa: BLE001 - never raise
            r = ModelReply(model, error=f"{type(e).__name__}: {str(e)[:200]}")
        if r.latency_ms is None:
            r.latency_ms = int((time.perf_counter() - t0) * 1000)
        if r.error is None:
            try:
                r.cost_usd = self.prices.cost(model, r.tokens_in, r.tokens_out)
            except KeyError as e:
                r.error = str(e)
        return r

    # -------------------------------------------------- retries (API only; a local call gets one attempt: it has a time budget)
    def _with_retries(self, model, fn) -> ModelReply:
        last, n = None, max(1, self.cfg.api_retries)
        for k in range(n):
            try:
                r = fn()
                r.attempts = k + 1
                return r
            except _Fail as e:
                last = e
                if not e.retriable or k == n - 1:
                    break
                self._sleep(min(30.0, (20.0 if e.rate_limited else 2.0) * 2 ** k))
        return ModelReply(model, error=str(last)[:240], attempts=k + 1)

    # -------------------------------------------------- Ollama
    def _ollama(self, model, system, user, max_tokens, timeout, json_mode=False) -> ModelReply:
        import httpx
        opts = {"temperature": 0, "num_predict": max_tokens, "num_ctx": 4096}
        if self.cfg.local_cpu_only:
            opts.update(num_gpu=0, num_thread=self.cfg.local_threads)
        payload = {"model": model, "stream": False, "keep_alive": "10m", "options": opts,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            payload["format"] = "json"      # D13 logic translator (same as the Kaggle translation run)
        if model.startswith("qwen3"):
            payload["think"] = False
        try:
            resp = httpx.post(self.cfg.ollama_host + "/api/chat", json=payload, timeout=timeout)
        except httpx.TimeoutException:
            return ModelReply(model, error=f"timeout after {timeout:.0f}s")
        except httpx.HTTPError as e:
            return ModelReply(model, error=f"{type(e).__name__}: {str(e)[:120]}")
        if resp.status_code >= 400:
            return ModelReply(model, error=f"HTTP {resp.status_code}: {resp.text[:120]}")
        d = resp.json()
        return ModelReply(model, text=(d.get("message") or {}).get("content") or "", tokens_in=d.get("prompt_eval_count"),
                          tokens_out=d.get("eval_count"), finish=d.get("done_reason"))

    # -------------------------------------------------- Fireworks / Hyde
    def _openai(self, model, system, user, max_tokens, timeout) -> ModelReply:
        import httpx
        prov, api_id = API_MODELS[model]
        base, key = (self.cfg.hyde_url, self.cfg.hyde_key) if prov == "hyde" else (self.cfg.fireworks_url, self.cfg.fireworks_key)
        if not base or not key:
            raise _Fail(f"{prov} is not configured (missing key or URL)", retriable=False)
        payload = {"model": api_id, "temperature": 0, "max_tokens": max_tokens, "reasoning_effort": self.cfg.reasoning_effort,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        try:
            r = httpx.post(base + "/chat/completions", json=payload, timeout=timeout, headers={"Authorization": f"Bearer {key}"})
        except httpx.HTTPError as e:
            raise _Fail(f"{type(e).__name__}: {str(e)[:120]}", retriable=True)
        if r.status_code >= 400:
            raise _Fail(f"HTTP {r.status_code}: {r.text[:160]}", retriable=_retriable_status(r.status_code), rate_limited=r.status_code == 429)
        d = r.json()
        ch = (d.get("choices") or [{}])[0]
        u = d.get("usage") or {}
        return ModelReply(model, text=(ch.get("message") or {}).get("content") or "", tokens_in=u.get("prompt_tokens"),
                          tokens_out=u.get("completion_tokens"),
                          tokens_reasoning=(u.get("completion_tokens_details") or {}).get("reasoning_tokens"), finish=ch.get("finish_reason"))

    # -------------------------------------------------- Gemini (AI Studio; free tier ~15 req/min, so calls are spaced out)
    def _gemini(self, model, system, user, max_tokens, timeout) -> ModelReply:
        if not self.cfg.google_key:
            raise _Fail("gemini is not configured (missing key)", retriable=False)
        try:
            with self._gem_lock:
                wait = self.cfg.gemini_min_interval_s - (time.monotonic() - self._gem_last)
                if wait > 0:
                    self._sleep(wait)
                self._gem_last = time.monotonic()
            from google import genai
            from google.genai import types as t
            if self._gem is None:
                self._gem = genai.Client(api_key=self.cfg.google_key)
            cfg = t.GenerateContentConfig(system_instruction=system, temperature=0, max_output_tokens=max_tokens,
                                          thinking_config=t.ThinkingConfig(thinking_level=self.cfg.reasoning_effort.upper()))
            r = self._gem.models.generate_content(model=API_MODELS[model][1], contents=user, config=cfg)
        except _Fail:
            raise
        except Exception as e:  # noqa: BLE001
            s = f"{type(e).__name__} {e}"
            raise _Fail(s[:160], retriable=not ("404" in s or "NOT_FOUND" in s or "API key" in s),
                        rate_limited="429" in s or "RESOURCE_EXHAUSTED" in s)
        text, finish = "", None
        for c in r.candidates or []:
            finish = str(c.finish_reason).split(".")[-1] if c.finish_reason is not None else None
            for p in (c.content.parts if c.content and c.content.parts else []):
                if getattr(p, "text", None) and not getattr(p, "thought", False):
                    text += p.text
        u = r.usage_metadata
        thoughts = (u.thoughts_token_count or 0) if u else 0
        cand = (u.candidates_token_count or 0) if u else 0
        return ModelReply(model, text=text, tokens_in=u.prompt_token_count if u else None, tokens_out=cand + thoughts,
                          tokens_reasoning=thoughts, finish=finish)
