"""
LLM Provider Integrations.

This module provides a unified interface for interacting with different LLM backends:
- GeminiProvider: Google Gemini API (all three difficulty tiers)

The abstract BaseProvider class allows easy swapping and fallback behavior.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

from src.config import get_settings


@dataclass
class ProviderResponse:
    """
    Standard response from any LLM provider.
    
    Attributes:
        text: The generated text response
        model: The model that was used
        prompt_tokens: Number of tokens in the prompt (estimated)
        completion_tokens: Number of tokens in the response (estimated)
        latency_ms: Time taken for the request in milliseconds
        raw_response: The raw response from the provider (for debugging)
    """
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    raw_response: Optional[dict] = None


class ProviderError(Exception):
    """Base exception for provider errors."""
    def __init__(self, message: str, provider: str, retriable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.retriable = retriable


class ProviderTimeoutError(ProviderError):
    """Request timed out."""
    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded."""
    pass


class ProviderModelNotFoundError(ProviderError):
    """Model not available."""
    def __init__(self, message: str, provider: str):
        super().__init__(message, provider, retriable=False)


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement the `generate` method.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass
    
    @abstractmethod
    async def generate(self, prompt: str, model: str) -> ProviderResponse:
        """
        Generate a completion for the given prompt.
        
        Args:
            prompt: The user's prompt
            model: The specific model to use
            
        Returns:
            ProviderResponse with generated text and metadata
            
        Raises:
            ProviderError: If the request fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available.
        
        Returns:
            True if the provider is healthy, False otherwise
        """
        pass
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (~4 chars per token for English)."""
        return len(text) // 4


class OllamaProvider(BaseProvider):
    """
    Provider for local LLMs via Ollama (restored from upstream commit d406ce0).

    Adapted: per-call `options` (num_thread, num_gpu, num_predict, ...) and
    `keep_alive` (0 = unload after each call, gentle on a 16 GB laptop).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 120,
        keep_alive: "int | str" = 0,
        options: Optional[dict] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.options = options or {}
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def name(self) -> str:
        return "ollama"

    async def generate(self, prompt: str, model: str) -> ProviderResponse:
        """POST /api/generate (non-streaming)."""
        start_time = time.perf_counter()
        body = {"model": model, "prompt": prompt, "stream": False, "keep_alive": self.keep_alive}
        if self.options:
            body["options"] = self.options
        try:
            response = await self._client.post(f"{self.base_url}/api/generate", json=body)
            if response.status_code == 404:
                raise ProviderModelNotFoundError(
                    f"Model '{model}' not found in Ollama. Run: ollama pull {model}",
                    self.name,
                )
            response.raise_for_status()
            data = response.json()
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            text = data.get("response", "")
            return ProviderResponse(
                text=text,
                model=model,
                prompt_tokens=data.get("prompt_eval_count", self._estimate_tokens(prompt)),
                completion_tokens=data.get("eval_count", self._estimate_tokens(text)),
                latency_ms=latency_ms,
                raw_response=data,
            )
        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"Ollama request timed out after {self.timeout}s", self.name)
        except httpx.HTTPStatusError as e:
            raise ProviderError(f"Ollama HTTP error: {e.response.status_code}", self.name)
        except httpx.RequestError as e:
            raise ProviderError(f"Ollama connection error: {e}", self.name)

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
        except Exception:
            return []

    async def close(self):
        await self._client.aclose()
