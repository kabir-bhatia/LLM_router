"""
Configuration management using Pydantic Settings.

This module centralizes all configuration from environment variables
with type safety and validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===================
    # Database
    # ===================
    # SQLite keeps the project single-process and zero-setup. The async driver
    # is aiosqlite; the file lives at the repo root.
    database_url: str = "sqlite+aiosqlite:///./router.db"

    # ===================
    # Redis
    # ===================
    # Optional. The semantic cache needs the RediSearch module (Redis Stack),
    # not plain Redis. When unreachable the cache degrades to a no-op and the
    # router still serves requests.
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    enable_redis_cache: bool = False

    # ===================
    # Embeddings (local, no API key)
    # ===================
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # ===================
    # Google Gemini
    # ===================
    # Two auth modes to the same API:
    #
    # - Vertex AI (service account) -- default, recommended. Confirmed
    #   empirically to get full paid-tier throughput with zero rate limiting
    #   (20/20 and 10/10 concurrent bursts succeeded) and access to models
    #   that 404'd/429'd through the AI Studio API key on this project,
    #   including gemini-2.5-pro. Needs a service account JSON key file
    #   (GOOGLE_APPLICATION_CREDENTIALS) -- see .env.example.
    # - AI Studio API key -- simpler to set up, but on this project the
    #   newest Gemini model generation (3.x) was throttled to a 15 req/min
    #   free-tier limit even with the account's paid tier enabled, and
    #   gemini-2.5-pro returned 404 as deprecated for new users. Kept as a
    #   fallback path since it's the lower-setup-cost option for anyone
    #   re-running this project on their own key.
    use_vertex_ai: bool = True
    google_application_credentials: str = ""  # path to service account JSON key
    vertex_project_id: str = ""  # auto-derived from the key file if unset
    vertex_location: str = "global"  # "global" has full model coverage; some models are missing from region-pinned locations like us-central1

    google_api_key: str = ""  # only used when use_vertex_ai=False

    # Model per difficulty tier. All three are Gemini, so there is one
    # provider, one auth path, and a pricing spread of ~1.7x input / ~2.7x
    # output between the cheap and expensive ends -- which is what makes
    # routing worth doing. Pinned to GA (non-preview) models only: preview
    # models can be renamed or pulled without notice, which would silently
    # break a reproducible eval.
    tier_simple_model: str = "gemini-3.1-flash-lite"
    tier_medium_model: str = "gemini-3.6-flash"
    # The only GA Pro-tier model. 404'd as "no longer available to new users"
    # through the AI Studio API key on this project; works cleanly through
    # Vertex AI with the service account (see use_vertex_ai above).
    tier_complex_model: str = "gemini-2.5-pro"

    # Model used by the LLM classifier itself. Must be cheap: it runs on every
    # single request, so an expensive classifier would eat the routing savings.
    classifier_model: str = "gemini-3.1-flash-lite"

    # ===================
    # API Security
    # ===================
    api_key_header: str = "X-API-Key"

    # ===================
    # Routing Thresholds
    # ===================
    simple_token_threshold: int = 50   # Below this = simple (very short prompts)
    complex_token_threshold: int = 500  # Above this = complex (very long prompts)
    use_llm_router: bool = True  # Use LLM-based classification (vs rule-based)
    use_semantic_cache: bool = True  # Use semantic similarity cache (vs exact match)

    # Cosine similarity above which a stored prompt counts as a cache hit.
    # The upstream project hardcoded 0.92 with no validation behind it.
    # eval/threshold_sweep.py measures where this should actually sit.
    semantic_similarity_threshold: float = 0.92

    # ===================
    # Logging
    # ===================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once,
    improving performance and ensuring consistency.
    """
    return Settings()
