"""
Phase 4 -- Cost/accuracy tradeoff eval.

Runs every labeled prompt through the ACTUAL production pipeline (classify ->
route -> generate), and separately through a real baseline generation on
gemini-2.5-pro for the same prompt, then computes real cost savings and flags
misroutes: cases where a prompt's true difficulty was COMPLEX but the router
sent it somewhere cheaper.

Why a real baseline generation instead of re-pricing the routed response's
token count under the baseline model (what CostCalculator.estimate() does for
live request logging): that approximation is the right tradeoff for a live
request -- you don't want to double an end user's latency and cost just to
report a savings number. This is offline analysis with no user waiting, so
paying for a second real generation per prompt (~$0.30-0.50 total for the
whole 108-prompt set) gets an actually-audited number instead of an estimated
one, which is the more defensible number for the CV claim this project exists
to produce.

Usage:
    .venv/Scripts/python.exe -m eval.eval_cost_tradeoff
    .venv/Scripts/python.exe -m eval.eval_cost_tradeoff --concurrency 8

Outputs (eval/results/):
    cost_tradeoff_predictions.json   -- one record per prompt
    cost_tradeoff_report.md          -- savings table, misroute cases, charts
    cost_by_tier.png
"""

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from src.core.router import DifficultyTier, LLMRouter
from src.providers.base import ProviderError
from src.providers.gemini import GeminiProvider
from src.providers.manager import get_provider_manager
from src.services.cost import BASELINE_MODEL, get_cost_calculator

LABELED_PATH = Path("eval/labeled_prompts.json")
RESULTS_DIR = Path("eval/results")
TIER_ORDER = {"simple": 0, "medium": 1, "complex": 2}


@dataclass
class TradeoffRecord:
    id: str
    domain: str
    prompt: str
    true_tier: str
    borderline: bool

    routed_tier: Optional[str]  # what LLMRouter.classify() decided
    classification_used_fallback: bool

    actual_model: Optional[str]  # model that actually generated the response
    actual_tier_used: Optional[str]  # may differ from routed_tier if ProviderManager escalated on failure
    actual_prompt_tokens: Optional[int]
    actual_completion_tokens: Optional[int]
    actual_cost: Optional[float]
    actual_latency_ms: Optional[int]
    generation_failed: bool

    baseline_model: Optional[str]
    baseline_prompt_tokens: Optional[int]
    baseline_completion_tokens: Optional[int]
    baseline_cost: Optional[float]
    baseline_latency_ms: Optional[int]
    baseline_failed: bool

    misroute: Optional[str]  # "under" | "over" | "match" | None if either side failed
    error: str = ""


def load_labeled_prompts() -> list[dict]:
    data = json.loads(LABELED_PATH.read_text(encoding="utf-8"))
    unlabeled = [d["id"] for d in data if not d.get("true_tier")]
    if unlabeled:
        raise SystemExit(f"{len(unlabeled)} prompts still unlabeled: {unlabeled[:5]}")
    return data


async def process_prompt(item: dict, baseline_provider: GeminiProvider) -> TradeoffRecord:
    calculator = get_cost_calculator()
    manager = get_provider_manager()

    record = TradeoffRecord(
        id=item["id"], domain=item["domain"], prompt=item["prompt"],
        true_tier=item["true_tier"], borderline=item.get("borderline", False),
        routed_tier=None, classification_used_fallback=False,
        actual_model=None, actual_tier_used=None, actual_prompt_tokens=None,
        actual_completion_tokens=None, actual_cost=None, actual_latency_ms=None,
        generation_failed=False,
        baseline_model=None, baseline_prompt_tokens=None, baseline_completion_tokens=None,
        baseline_cost=None, baseline_latency_ms=None, baseline_failed=False,
        misroute=None,
    )

    # 1. Classify (production default: LLMRouter, which falls back to rules internally)
    router = LLMRouter()  # fresh instance -- avoids state races under concurrency, same as Phase 3
    decision = await router.classify(item["prompt"])
    record.routed_tier = decision.tier.value
    record.classification_used_fallback = router.last_used_fallback

    # 2. Generate through the real routed/fallback-escalation path
    try:
        response, actual_tier = await manager.generate(
            prompt=item["prompt"], tier=decision.tier, max_retries=1,
        )
        record.actual_model = response.model
        record.actual_tier_used = actual_tier.value
        record.actual_prompt_tokens = response.prompt_tokens
        record.actual_completion_tokens = response.completion_tokens
        record.actual_latency_ms = response.latency_ms
        estimate = calculator.estimate(response.model, response.prompt_tokens, response.completion_tokens)
        record.actual_cost = estimate.estimated_cost
    except ProviderError as e:
        record.generation_failed = True
        record.error += f"generation: {e}; "

    # 3. Real baseline generation -- same prompt, always the baseline model.
    #    One retry: at concurrency=8, Vertex's own (much higher, but not
    #    infinite) quota can still throw an occasional transient 429.
    for attempt in range(2):
        try:
            baseline_response = await baseline_provider.generate(item["prompt"], BASELINE_MODEL)
            record.baseline_model = baseline_response.model
            record.baseline_prompt_tokens = baseline_response.prompt_tokens
            record.baseline_completion_tokens = baseline_response.completion_tokens
            record.baseline_latency_ms = baseline_response.latency_ms
            baseline_estimate = calculator.estimate(
                baseline_response.model, baseline_response.prompt_tokens, baseline_response.completion_tokens
            )
            record.baseline_cost = baseline_estimate.estimated_cost
            record.baseline_failed = False
            break
        except ProviderError as e:
            record.baseline_failed = True
            record.error += f"baseline attempt {attempt + 1}: {e}; "
            if attempt == 0:
                await asyncio.sleep(4.0)

    # 4. Misroute classification -- compare TRUE tier against what actually generated
    #    the response (not the initial routing decision), since that's what the
    #    user actually got. Escalation on failure counts as the system correcting
    #    itself, not a misroute.
    if record.actual_tier_used is not None:
        true_ord = TIER_ORDER[record.true_tier]
        actual_ord = TIER_ORDER[record.actual_tier_used]
        if actual_ord < true_ord:
            record.misroute = "under"
        elif actual_ord > true_ord:
            record.misroute = "over"
        else:
            record.misroute = "match"

    return record


async def run_eval(prompts: list[dict], concurrency: int) -> list[TradeoffRecord]:
    semaphore = asyncio.Semaphore(concurrency)
    baseline_provider = GeminiProvider()  # generate() is stateless per call -- safe to share across concurrent tasks
    order = {item["id"]: idx for idx, item in enumerate(prompts)}

    async def bound(item: dict) -> TradeoffRecord:
        async with semaphore:
            return await process_prompt(item, baseline_provider)

    tasks = [asyncio.create_task(bound(item)) for item in prompts]
    results = []
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        record = await coro
        results.append(record)
        status = "OK" if not (record.generation_failed or record.baseline_failed) else "FAIL"
        misroute_flag = f" [{record.misroute.upper()}-ROUTED]" if record.misroute in ("under", "over") else ""
        print(
            f"  [{i:>3}/{len(tasks)}] {record.id:<10} true={record.true_tier:<8} "
            f"routed={record.routed_tier or '?':<8} actual={record.actual_tier_used or '?':<8} "
            f"[{status}]{misroute_flag}"
        )

    results.sort(key=lambda r: order[r.id])
    return results


def build_report(results: list[TradeoffRecord]) -> str:
    ok = [r for r in results if r.actual_cost is not None and r.baseline_cost is not None]
    ok_ids = {r.id for r in ok}
    failed = [r for r in results if r.id not in ok_ids]

    total_actual = sum(r.actual_cost for r in ok)
    total_baseline = sum(r.baseline_cost for r in ok)
    savings = total_baseline - total_actual
    savings_pct = (savings / total_baseline * 100) if total_baseline > 0 else 0.0

    under = [r for r in ok if r.misroute == "under"]
    over = [r for r in ok if r.misroute == "over"]
    match = [r for r in ok if r.misroute == "match"]

    fallback_used = [r for r in results if r.classification_used_fallback]

    lines = ["# Phase 4 -- Cost/Accuracy Tradeoff Report", ""]
    lines.append(
        f"Ran all {len(results)} labeled prompts through the real production pipeline "
        f"(`LLMRouter.classify` -> `ProviderManager.generate`), plus a real separate "
        f"baseline generation on `{BASELINE_MODEL}` for every prompt (not a "
        f"token-count re-pricing of the routed response -- see script docstring)."
    )
    lines.append("")
    if failed:
        lines.append(f"**{len(failed)} prompt(s) excluded from cost totals** due to a generation "
                     f"or baseline failure: {', '.join(r.id for r in failed)}.")
        lines.append("")

    lines.append("## Aggregate cost")
    lines.append("")
    lines.append("| | total |")
    lines.append("|---|---|")
    lines.append(f"| Actual cost (routed) | ${total_actual:.6f} |")
    lines.append(f"| Baseline cost (always `{BASELINE_MODEL}`) | ${total_baseline:.6f} |")
    lines.append(f"| Savings | ${savings:.6f} ({savings_pct:.1f}%) |")
    lines.append(f"| n (excluding failures) | {len(ok)} / {len(results)} |")
    lines.append("")

    lines.append("## Cost by true difficulty tier")
    lines.append("")
    lines.append("| true tier | n | actual cost | baseline cost | savings % |")
    lines.append("|---|---|---|---|---|")
    for tier in ["simple", "medium", "complex"]:
        subset = [r for r in ok if r.true_tier == tier]
        if not subset:
            continue
        a = sum(r.actual_cost for r in subset)
        b = sum(r.baseline_cost for r in subset)
        pct = (b - a) / b * 100 if b > 0 else 0.0
        lines.append(f"| {tier} | {len(subset)} | ${a:.6f} | ${b:.6f} | {pct:.1f}% |")
    lines.append("")
    complex_subset = [r for r in ok if r.true_tier == "complex"]
    if complex_subset:
        lines.append(
            "**On the COMPLEX row possibly reading near-zero or negative:** that's expected, "
            f"not a bug. A correctly-routed COMPLEX prompt's \"actual\" model already IS "
            f"`{BASELINE_MODEL}` -- the same model as the baseline -- so actual and baseline "
            "cost for that row come from two *independent* generations of the identical model "
            "on the identical prompt (temperature 0.7), differing only by natural response-length "
            "variance between samples. A small swing either side of 0% here is sampling noise, not "
            "a routing failure; it would only be concerning if it were large and consistently negative."
        )
        lines.append("")

    lines.append("## Misroutes")
    lines.append("")
    lines.append(f"- **Under-routed** (sent cheaper than true difficulty warranted): "
                 f"{len(under)} / {len(ok)} ({len(under)/len(ok)*100:.1f}%)")
    lines.append(f"- **Over-routed** (sent pricier than necessary -- money left on the table, "
                 f"not a quality risk): {len(over)} / {len(ok)} ({len(over)/len(ok)*100:.1f}%)")
    lines.append(f"- **Matched** true difficulty exactly: {len(match)} / {len(ok)} ({len(match)/len(ok)*100:.1f}%)")
    lines.append("")
    lines.append(
        "Under-routing is the case that actually matters: a COMPLEX prompt answered by a "
        "SIMPLE-tier model is the cheapest possible wrong answer, and a wrong answer that "
        "reads as confident is worse than an expensive right one. Every under-routed prompt "
        "below is worth reading, not just counting."
    )
    lines.append("")

    if under:
        lines.append(f"### Under-routed prompts ({len(under)})")
        lines.append("")
        lines.append("| id | true | routed to | model | domain |")
        lines.append("|---|---|---|---|---|")
        for r in under:
            lines.append(f"| {r.id} | {r.true_tier} | {r.actual_tier_used} | {r.actual_model} | {r.domain} |")
        lines.append("")
        lines.append("Prompt text for each, so the risk is concrete rather than abstract:")
        lines.append("")
        for r in under:
            lines.append(f"- `{r.id}` (true **{r.true_tier}**, routed **{r.actual_tier_used}**): {r.prompt[:150]}")
        lines.append("")

    if over:
        lines.append(f"### Over-routed prompts ({len(over)}) -- wasted spend, not a quality risk")
        lines.append("")
        for r in over:
            lines.append(f"- `{r.id}` (true **{r.true_tier}**, routed **{r.actual_tier_used}**): {r.prompt[:100]}")
        lines.append("")

    if fallback_used:
        lines.append(
            f"## Classification fallback ({len(fallback_used)} prompts)\n\n"
            f"These prompts' LLM classification failed and fell back to the rule-based "
            f"classifier mid-pipeline -- real production behavior, not excluded from the "
            f"numbers above, but worth knowing which ones: "
            f"{', '.join(r.id for r in fallback_used)}."
        )
        lines.append("")

    return "\n".join(lines)


def save_cost_chart(results: list[TradeoffRecord], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ok = [r for r in results if r.actual_cost is not None and r.baseline_cost is not None]
    tiers = ["simple", "medium", "complex"]
    actual = []
    baseline = []
    for tier in tiers:
        subset = [r for r in ok if r.true_tier == tier]
        actual.append(sum(r.actual_cost for r in subset))
        baseline.append(sum(r.baseline_cost for r in subset))

    x = range(len(tiers))
    width = 0.35
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar([i - width / 2 for i in x], actual, width, label="Actual (routed)")
    ax.bar([i + width / 2 for i in x], baseline, width, label=f"Baseline (always {BASELINE_MODEL})")
    ax.set_xticks(list(x))
    ax.set_xticklabels(tiers)
    ax.set_ylabel("Total cost (USD)")
    ax.set_title("Cost by true difficulty tier: routed vs. baseline")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 cost/accuracy tradeoff eval")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrent prompt pipelines")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N prompts (for smoke-testing)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    prompts = load_labeled_prompts()
    if args.limit:
        prompts = prompts[: args.limit]
    print(f"Loaded {len(prompts)} labeled prompts. Running full pipeline + real baseline generation...\n")

    results = await run_eval(prompts, args.concurrency)

    (RESULTS_DIR / "cost_tradeoff_predictions.json").write_text(
        json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report = build_report(results)
    (RESULTS_DIR / "cost_tradeoff_report.md").write_text(report, encoding="utf-8")

    save_cost_chart(results, RESULTS_DIR / "cost_by_tier.png")

    ok = [r for r in results if r.actual_cost is not None and r.baseline_cost is not None]
    total_actual = sum(r.actual_cost for r in ok)
    total_baseline = sum(r.baseline_cost for r in ok)
    savings_pct = (total_baseline - total_actual) / total_baseline * 100 if total_baseline > 0 else 0.0
    under = sum(1 for r in ok if r.misroute == "under")

    print("\n" + "=" * 68)
    print(f"Actual cost:   ${total_actual:.6f}")
    print(f"Baseline cost: ${total_baseline:.6f}")
    print(f"Savings:       {savings_pct:.1f}%")
    print(f"Under-routed:  {under}/{len(ok)}")
    print(f"\nFull report: {RESULTS_DIR / 'cost_tradeoff_report.md'}")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(main())
