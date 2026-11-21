"""
Pytest configuration.

Tests must not touch the network or need cloud credentials, so every
GeminiProvider is replaced by an in-memory fake for the whole test session.
"""

import platform
import sys

import pytest

# Windows workaround: on this machine the WMI service can hang forever, and Python 3.13's
# platform.uname() (called by sqlalchemy & others at import time) blocks on it. Disable the WMI
# path so platform falls back to environment variables.
if sys.platform == "win32":
    platform._wmi = None

pytest_plugins = ['pytest_asyncio']


class FakeGeminiProvider:
    """Offline stand-in for GeminiProvider (no credentials, no network)."""

    name = "fake-gemini"

    def __init__(self, *args, **kwargs):
        pass

    async def generate(self, prompt: str, model: str):
        from src.providers.base import ProviderResponse

        # The LLM classifier expects "CATEGORY|reason"; ordinary completions
        # just get a canned answer.
        text = "SIMPLE|fake classification" if "prompt classifier" in prompt else "fake answer"
        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=max(1, len(prompt) // 4),
            completion_tokens=5,
            latency_ms=1,
        )

    async def generate_structured(self, *args, **kwargs):
        return {}, 10, 5, 1

    async def health_check(self) -> bool:
        return True

    async def close(self):
        pass


@pytest.fixture(autouse=True)
def fake_gemini(monkeypatch):
    import src.providers.gemini as gemini_mod
    import src.providers.manager as manager_mod

    monkeypatch.setattr(gemini_mod, "GeminiProvider", FakeGeminiProvider)
    monkeypatch.setattr(manager_mod, "GeminiProvider", FakeGeminiProvider)
    monkeypatch.setattr(manager_mod, "_manager", None)
    yield
