"""
End-to-end setup verification (Phase 1 exit criteria).

Checks each layer in dependency order and stops at the first real failure, so
the output points at one thing to fix rather than a wall of cascading errors.

Run:
    .venv/Scripts/python.exe scripts/verify_setup.py
"""

import asyncio
import sys

# Total spend for a full run is roughly a tenth of a cent.
CHECKS_USING_API = 2


def ok(msg: str) -> None:
    print(f"  [ok]   {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


async def check_config() -> bool:
    print("\n[1/6] Configuration")
    from src.config import get_settings

    s = get_settings()
    ok(f"database    {s.database_url}")
    ok(f"tiers       {s.tier_simple_model} / {s.tier_medium_model} / {s.tier_complex_model}")
    ok(f"classifier  {s.classifier_model}")
    ok(f"embeddings  {s.embedding_model} ({s.embedding_dim}d)")

    if not s.google_api_key or s.google_api_key.startswith("your-"):
        fail("GOOGLE_API_KEY is not set in .env")
        print("\n       Get a key at https://aistudio.google.com/apikey")
        print("       then edit .env and set:  GOOGLE_API_KEY=<your key>")
        return False

    ok(f"api key     set ({len(s.google_api_key)} chars)")
    return True


async def check_database() -> bool:
    print("\n[2/6] Database")
    from sqlalchemy import text

    from src.db.session import engine, init_db

    await init_db()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = sorted(row[0] for row in result)

    expected = {"api_keys", "requests_log"}
    if not expected.issubset(tables):
        fail(f"missing tables: {expected - set(tables)}")
        return False

    ok(f"tables      {', '.join(tables)}")
    return True


async def check_embeddings() -> bool:
    print("\n[3/6] Embeddings (local, first run downloads ~80MB)")
    from src.services.embeddings import get_embeddings_service

    service = get_embeddings_service()
    vectors = service.embed_batch_sync(
        [
            "How do I reset my password?",
            "How can I reset my password?",
            "Design a distributed rate limiter for a multi-region API",
        ]
    )

    similarity = vectors @ vectors.T
    near_dup = float(similarity[0, 1])
    unrelated = float(similarity[0, 2])

    ok(f"dimension   {vectors.shape[1]}")
    ok(f"near-dup    {near_dup:.4f}  (paraphrase pair)")
    ok(f"unrelated   {unrelated:.4f}")

    if near_dup <= unrelated:
        fail("paraphrases are not closer than unrelated prompts")
        return False
    return True


async def check_classifier() -> bool:
    print("\n[4/6] Classification (1 API call)")
    from src.core.router import LLMRouter, RuleBasedRouter

    prompt = "Design a fault-tolerant job queue that survives regional outages."

    rule_decision = await RuleBasedRouter().classify(prompt)
    ok(f"rule-based  {rule_decision.tier.value}")

    llm_router = LLMRouter()
    llm_decision = await llm_router.classify(prompt)

    if llm_router.last_used_fallback:
        fail("LLM classifier errored and silently fell back to rules")
        print(f"         reason: {llm_decision.reason}")
        return False

    ok(f"llm-based   {llm_decision.tier.value} -> {llm_decision.model}")
    return True


async def check_generation() -> bool:
    print("\n[5/6] Generation + cost accounting (1 API call)")
    from src.core.router import DifficultyTier
    from src.providers.manager import get_provider_manager
    from src.services.cost import get_cost_calculator

    manager = get_provider_manager()
    response, tier_used = await manager.generate(
        prompt="Reply with exactly the word: pong",
        tier=DifficultyTier.SIMPLE,
    )

    ok(f"model       {response.model}")
    ok(f"response    {response.text.strip()[:60]!r}")
    ok(f"tokens      {response.prompt_tokens} in / {response.completion_tokens} out")
    ok(f"latency     {response.latency_ms} ms")

    if tier_used != DifficultyTier.SIMPLE:
        fail(f"escalated to {tier_used.value} -- the simple tier is failing")
        return False

    estimate = get_cost_calculator().estimate(
        response.model, response.prompt_tokens, response.completion_tokens
    )
    ok(f"cost        ${estimate.estimated_cost:.8f}")
    ok(f"baseline    ${estimate.baseline_cost:.8f} ({estimate.savings_percent:.1f}% saved)")
    return True


async def check_pricing_coverage() -> bool:
    print("\n[6/6] Pricing table covers every tier")
    from src.config import get_settings
    from src.services.cost import get_cost_calculator

    settings = get_settings()
    calculator = get_cost_calculator()

    models = [
        settings.tier_simple_model,
        settings.tier_medium_model,
        settings.tier_complex_model,
        settings.classifier_model,
    ]

    for model in sorted(set(models)):
        try:
            pricing = calculator.get_pricing(model)
        except KeyError:
            fail(f"no pricing entry for {model}")
            print("         Every cost number depends on this table.")
            print("         Add it to MODEL_PRICING in src/services/cost.py")
            return False
        ok(
            f"{model:<26} ${pricing.input_cost_per_million}/M in, "
            f"${pricing.output_cost_per_million}/M out"
        )
    return True


async def main() -> int:
    print("=" * 68)
    print("Smart LLM Router -- setup verification")
    print("=" * 68)

    checks = [
        check_config,
        check_database,
        check_embeddings,
        check_classifier,
        check_generation,
        check_pricing_coverage,
    ]

    for check in checks:
        try:
            if not await check():
                print("\n" + "=" * 68)
                print("VERIFICATION FAILED -- fix the above, then re-run.")
                print("=" * 68)
                return 1
        except Exception as exc:
            fail(f"{type(exc).__name__}: {exc}")
            print("\n" + "=" * 68)
            print("VERIFICATION FAILED -- fix the above, then re-run.")
            print("=" * 68)
            return 1

    print("\n" + "=" * 68)
    print("ALL CHECKS PASSED -- Phase 1 complete.")
    print(f"({CHECKS_USING_API} API calls used, well under a cent.)")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
