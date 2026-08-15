"""
Cost Calculator Service.

Handles:
- Per-model pricing configuration
- Cost estimation from token counts
- Savings calculation vs baseline (always using Pro model)
- Request logging to database
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.router import DifficultyTier
from src.db import RequestLog
from src.providers.base import ProviderResponse


@dataclass
class ModelPricing:
    """
    Pricing information for a model.
    
    Costs are in USD per 1M tokens (standard industry unit).
    """
    model_name: str
    input_cost_per_million: float   # Cost per 1M input tokens
    output_cost_per_million: float  # Cost per 1M output tokens
    is_local: bool = False          # Local models have ~zero marginal cost


# ===================
# Model Pricing Table
# ===================
# Prices based on public API pricing (as of Dec 2024)
# Local models have electricity/GPU cost approximated

# IMPORTANT: these figures drive every savings number this project reports, so
# they are the one input worth re-checking by hand against
# https://ai.google.dev/gemini-api/docs/pricing before publishing results.
# Values below are paid-tier, per 1M tokens, prompts under the 200k context
# break point, checked Aug 2026. Verify before quoting these numbers anywhere --
# and note gemini-3.6-flash/3.7-flash carry promotional pricing through
# 2026-12-31 that roughly doubles on 2027-01-01.

MODEL_PRICING: dict[str, ModelPricing] = {
    # SIMPLE tier
    "gemini-3.1-flash-lite": ModelPricing(
        model_name="gemini-3.1-flash-lite",
        input_cost_per_million=0.25,
        output_cost_per_million=1.50,
        is_local=False,
    ),
    # MEDIUM tier (promotional pricing through 2026-12-31; ~2x after)
    "gemini-3.6-flash": ModelPricing(
        model_name="gemini-3.6-flash",
        input_cost_per_million=0.75,
        output_cost_per_million=3.75,
        is_local=False,
    ),
    # COMPLEX tier -- and the baseline every saving is measured against.
    # The only GA Pro-tier model. 404'd as deprecated-for-new-users through the
    # AI Studio API key on this project; works cleanly through Vertex AI with
    # a service account (settings.use_vertex_ai) -- confirmed with concurrent
    # bursts (10/10 succeeded, no throttling). If you're on the API-key path
    # and hit the same 404, gemini-3.5-flash is a working GA stand-in that
    # preserves the tier cost ordering (kept below for that fallback).
    "gemini-2.5-pro": ModelPricing(
        model_name="gemini-2.5-pro",
        input_cost_per_million=1.25,
        output_cost_per_million=10.00,
        is_local=False,
    ),
    # Fallback COMPLEX model if gemini-2.5-pro is unavailable on your account.
    "gemini-3.5-flash": ModelPricing(
        model_name="gemini-3.5-flash",
        input_cost_per_million=1.50,
        output_cost_per_million=9.00,
        is_local=False,
    ),
}

# Baseline model for savings calculation (most expensive option in active use).
# "Savings" throughout this project means: what this request cost, versus what
# it would have cost had every request gone to this model instead.
BASELINE_MODEL = "gemini-2.5-pro"


@dataclass
class CostEstimate:
    """
    Cost estimate for a request.
    
    Attributes:
        model: Model that was used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        estimated_cost: Cost in USD for this request
        baseline_cost: What it would have cost using baseline model
        savings: Difference between baseline and actual cost
        savings_percent: Percentage saved
    """
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    baseline_cost: float
    savings: float
    savings_percent: float


class CostCalculator:
    """
    Calculates costs and savings for LLM requests.
    """
    
    def __init__(self, pricing: Optional[dict[str, ModelPricing]] = None):
        """
        Initialize with pricing table.
        
        Args:
            pricing: Custom pricing table (defaults to MODEL_PRICING)
        """
        self.pricing = pricing or MODEL_PRICING
        self.baseline_model = BASELINE_MODEL
    
    def get_pricing(self, model: str) -> ModelPricing:
        """
        Get pricing for a model.

        Exact match only, then loud failure. Upstream this fell back to a
        prefix match and then silently to baseline pricing, which is unsafe
        for cost analysis in two distinct ways:

        1. Prefix matching is wrong here. "gemini-2.0-flash-lite" starts with
           "gemini-2.0-flash", so a lite request could be billed at the more
           expensive flash rate purely on dict ordering.
        2. Silently substituting baseline pricing for an unknown model makes a
           misconfigured model name look like zero savings rather than an
           error -- the failure hides inside a plausible-looking number.

        Since every reported savings figure depends on this table, an unknown
        model is a bug to surface, not a value to guess.
        """
        if model in self.pricing:
            return self.pricing[model]

        raise KeyError(
            f"No pricing entry for model {model!r}. Add it to MODEL_PRICING in "
            f"src/services/cost.py. Known models: {sorted(self.pricing)}"
        )
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate cost for a request.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        pricing = self.get_pricing(model)
        
        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_million
        
        return input_cost + output_cost
    
    def estimate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        """
        Calculate full cost estimate with savings.
        
        Args:
            model: Model that was used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            CostEstimate with actual cost and savings vs baseline
        """
        actual_cost = self.calculate_cost(model, input_tokens, output_tokens)
        baseline_cost = self.calculate_cost(self.baseline_model, input_tokens, output_tokens)
        
        savings = baseline_cost - actual_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0
        
        return CostEstimate(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=actual_cost,
            baseline_cost=baseline_cost,
            savings=savings,
            savings_percent=savings_percent,
        )


class RequestLogger:
    """
    Logs requests to the database for tracking and analytics.
    """
    
    def __init__(self, calculator: Optional[CostCalculator] = None):
        """Initialize with optional custom calculator."""
        self.calculator = calculator or CostCalculator()
    
    async def log_request(
        self,
        session: AsyncSession,
        api_key_id: Optional[UUID],
        prompt: str,
        response_text: str,
        provider_response: ProviderResponse,
        tier: DifficultyTier,
        cache_hit: bool = False,
    ) -> RequestLog:
        """
        Log a completed request to the database.
        
        Args:
            session: Database session
            api_key_id: ID of the API key used
            prompt: Original prompt
            response_text: Generated response
            provider_response: Response from the provider
            tier: Difficulty tier used
            cache_hit: Whether response was from cache
            
        Returns:
            The created RequestLog record
        """
        # Calculate costs
        cost_estimate = self.calculator.estimate(
            model=provider_response.model,
            input_tokens=provider_response.prompt_tokens,
            output_tokens=provider_response.completion_tokens,
        )
        
        # Create log entry (using correct field names from RequestLog model)
        log = RequestLog(
            api_key_id=api_key_id,
            prompt_hash=self._hash_prompt(prompt),
            prompt_length=len(prompt),
            model_used=provider_response.model,
            difficulty_tag=tier.value,
            input_tokens=provider_response.prompt_tokens,
            output_tokens=provider_response.completion_tokens,
            estimated_cost=cost_estimate.estimated_cost,
            baseline_cost=cost_estimate.baseline_cost,
            cost_saved=cost_estimate.savings,
            latency_ms=provider_response.latency_ms,
            cache_hit=cache_hit,
        )
        
        session.add(log)
        return log
    
    def _hash_prompt(self, prompt: str) -> str:
        """Create a hash of the prompt for cache lookup."""
        import hashlib
        return hashlib.sha256(prompt.encode()).hexdigest()


# Singleton instances
_calculator: Optional[CostCalculator] = None
_logger: Optional[RequestLogger] = None


def get_cost_calculator() -> CostCalculator:
    """Get the singleton cost calculator."""
    global _calculator
    if _calculator is None:
        _calculator = CostCalculator()
    return _calculator


def get_request_logger() -> RequestLogger:
    """Get the singleton request logger."""
    global _logger
    if _logger is None:
        _logger = RequestLogger()
    return _logger
