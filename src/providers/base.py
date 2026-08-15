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
