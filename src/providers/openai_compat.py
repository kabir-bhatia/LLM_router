"""
OpenAI-compatible provider (Fireworks, Hyde AI gateway).

Plain httpx against `{base_url}/chat/completions`, so any OpenAI-style server works
and the exact `usage` block (incl. reasoning tokens when reported) is kept.
"""

import time
from typing import Optional

import httpx

from src.config import get_settings
from src.providers.base import (
    BaseProvider,
    ProviderError,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderTimeoutError,
)


class OpenAICompatProvider(BaseProvider):
    def __init__(self, provider_name: str, base_url: str, api_key: str, timeout: int = 120):
        self._name = provider_name
        self.base_url = base_url.strip().rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key.strip()}"},
        )

    @classmethod
    def fireworks(cls, **kw) -> "OpenAICompatProvider":
        s = get_settings()
        return cls("fireworks", s.fireworks_base_url, s.fireworks_api_key, **kw)

    @classmethod
    def hyde(cls, **kw) -> "OpenAICompatProvider":
        s = get_settings()
        if not s.hyde_base_url.strip():
            raise ProviderError("HYDE_BASE_URL is not set", "hyde", retriable=False)
        return cls("hyde", s.hyde_base_url, s.hyde_api_key, **kw)

    @property
    def name(self) -> str:
        return self._name

    def _raise_for(self, r: httpx.Response, model: str) -> None:
        if r.status_code == 404:
            raise ProviderModelNotFoundError(f"{model}: {r.text[:300]}", self.name)
        if r.status_code == 429:
            raise ProviderRateLimitError(r.text[:300], self.name)
        if r.status_code >= 400:
            raise ProviderError(
                f"HTTP {r.status_code}: {r.text[:300]}",
                self.name,
                retriable=r.status_code >= 500,
            )

    async def chat(self, payload: dict) -> tuple[dict, int]:
        """POST a raw chat-completions payload; returns (json, latency_ms)."""
        t0 = time.perf_counter()
        try:
            r = await self._client.post(f"{self.base_url}/chat/completions", json=payload)
        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"timed out after {self.timeout}s", self.name)
        except httpx.RequestError as e:
            raise ProviderError(f"connection error: {e}", self.name)
        self._raise_for(r, payload.get("model", ""))
        return r.json(), int((time.perf_counter() - t0) * 1000)

    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: Optional[int] = 256,
        temperature: float = 0.0,
        system: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> ProviderResponse:
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        payload = {"model": model, "messages": messages, "temperature": temperature}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        payload.update(extra or {})
        data, ms = await self.chat(payload)
        msg = (data.get("choices") or [{}])[0].get("message", {})
        usage = data.get("usage") or {}
        return ProviderResponse(
            text=msg.get("content") or "",
            model=model,
            prompt_tokens=usage.get("prompt_tokens", self._estimate_tokens(prompt)),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=ms,
            raw_response=data,
        )

    async def embed(self, model: str, texts: list[str]) -> tuple[dict, int]:
        t0 = time.perf_counter()
        try:
            r = await self._client.post(
                f"{self.base_url}/embeddings", json={"model": model, "input": texts}
            )
        except httpx.RequestError as e:
            raise ProviderError(f"connection error: {e}", self.name)
        self._raise_for(r, model)
        return r.json(), int((time.perf_counter() - t0) * 1000)

    async def list_models(self) -> list[dict]:
        r = await self._client.get(f"{self.base_url}/models")
        self._raise_for(r, "")
        return r.json().get("data", [])

    async def health_check(self) -> bool:
        try:
            await self.list_models()
            return True
        except Exception:
            return False

    async def close(self):
        await self._client.aclose()
