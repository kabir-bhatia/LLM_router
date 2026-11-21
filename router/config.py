"""Router settings (Phase 5). Everything tunable comes from environment variables (or the gitignored .env via src.config),
with the defaults the plan approved: 30 s local budget, semantic cache off, policy read from a path (never hard-coded cells)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Output budget INCLUDES reasoning tokens for the paid models. Same numbers as eval/run_api.py (Phase 3), so accuracy carries over.
MAX_TOKENS = {"math": 6000, "logic": 6000, "code_debug": 6000, "code_gen": 6000, "ner": 3000,
              "summarisation": 3000, "factual": 3000, "sentiment": 2000}
# Local output caps = the Phase 3 Kaggle runs (eval/results/phase3/raw_cpu/phase3_run.py NUM_PREDICT), so local accuracy carries over.
LOCAL_MAX_TOKENS = {"math": 768, "logic": 768, "sentiment": 256, "ner": 384, "code_debug": 1024,
                    "code_gen": 1024, "summarisation": 256, "factual": 320}


def _env(name, default=None):
    v = os.environ.get(name)
    return default if v is None or v == "" else v


def _secret(name_env: str, attr: str) -> str:
    """Env var first, then the gitignored .env via src.config. Never logged."""
    v = os.environ.get(name_env)
    if v:
        return v.strip()
    try:
        from src.config import get_settings
        return (getattr(get_settings(), attr, "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


@dataclass
class RouterConfig:
    policy_path: Path = field(default_factory=lambda: Path(_env("ROUTER_POLICY_PATH", ROOT / "eval" / "results" / "phase4" / "routing_policy.json")))
    prices_path: Path = field(default_factory=lambda: Path(_env("ROUTER_PRICES_PATH", ROOT / "eval" / "model_prices.json")))
    log_path: Path | None = field(default_factory=lambda: Path(p) if (p := _env("ROUTER_LOG_PATH")) else None)
    ollama_host: str = field(default_factory=lambda: _env("OLLAMA_HOST", _secret("OLLAMA_BASE_URL", "ollama_base_url") or "http://localhost:11434").rstrip("/"))
    local_budget_s: float = field(default_factory=lambda: float(_env("ROUTER_LOCAL_BUDGET_S", 30)))   # whole local layer per task
    api_timeout_s: float = field(default_factory=lambda: float(_env("ROUTER_API_TIMEOUT_S", 120)))
    api_retries: int = field(default_factory=lambda: int(_env("ROUTER_API_RETRIES", 3)))             # attempts per API call (transport/429/5xx)
    reasoning_effort: str = field(default_factory=lambda: _env("ROUTER_REASONING_EFFORT", "low"))     # D11
    max_tokens: dict = field(default_factory=lambda: dict(MAX_TOKENS))
    local_max_tokens: dict = field(default_factory=lambda: dict(LOCAL_MAX_TOKENS))
    gemini_min_interval_s: float = field(default_factory=lambda: float(_env("ROUTER_GEMINI_MIN_INTERVAL_S", 4.5)))
    local_threads: int = field(default_factory=lambda: int(_env("ROUTER_LOCAL_THREADS", 2)))      # CPU threads for Ollama (plan: 2)
    local_cpu_only: bool = field(default_factory=lambda: _env("ROUTER_LOCAL_CPU_ONLY", "1") == "1")
    use_solvers: bool = True               # the policy's own solvers_enabled flag can still turn them off
    use_translators: bool = True           # D13 LLM-assisted solvers
    translators: dict = field(default_factory=lambda: {"math": "phi3.5:3.8b", "logic": "gemma3:4b"})   # D13 choices (translator_report.md)
    semantic_cache: bool = False           # off by decision (plan section 5.4)

    # keys are resolved lazily so importing the config never touches the network or prints anything
    @property
    def fireworks_key(self) -> str:
        return _secret("FIREWORKS_API_KEY", "fireworks_api_key")

    @property
    def fireworks_url(self) -> str:
        return _env("FIREWORKS_BASE_URL", _secret("FIREWORKS_BASE_URL", "fireworks_base_url") or "https://api.fireworks.ai/inference/v1").rstrip("/")

    @property
    def hyde_key(self) -> str:
        return _secret("HYDE_API_KEY", "hyde_api_key")

    @property
    def hyde_url(self) -> str:
        return (_env("HYDE_BASE_URL") or _secret("HYDE_BASE_URL", "hyde_base_url")).strip().rstrip("/")

    @property
    def google_key(self) -> str:
        return _secret("GOOGLE_API_KEY", "google_api_key")

    def __repr__(self) -> str:  # never show secrets
        return f"RouterConfig(policy={self.policy_path.name}, local_budget_s={self.local_budget_s}, ollama={self.ollama_host})"
