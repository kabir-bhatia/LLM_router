"""
Phase 3 -- Classification accuracy eval.

Runs eval/labeled_prompts.json through the classification step ONLY (no
generation) for both routers, and reports accuracy, confusion matrices, and
where rule-based and LLM-based classification diverge.

Usage:
    .venv/Scripts/python.exe -m eval.eval_classification
    .venv/Scripts/python.exe -m eval.eval_classification --rule-only   # no API calls
    .venv/Scripts/python.exe -m eval.eval_classification --concurrency 8

Outputs (eval/results/):
    classification_predictions.json  -- one record per prompt
    classification_report.md         -- human-readable metrics + confusion
                                         matrices + misclassification examples
    confusion_matrix_rule.png
    confusion_matrix_llm.png
"""

import argparse
import asyncio
import collections
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

from src.core.router import LLMRouter, RuleBasedRouter
from src.providers.base import ProviderRateLimitError
from src.services.cost import get_cost_calculator

TIERS = ["simple", "medium", "complex"]
LABELED_PATH = Path("eval/labeled_prompts.json")
RESULTS_DIR = Path("eval/results")


@dataclass
class PredictionRecord:
    id: str
    domain: str
    prompt: str
    true_tier: str
    borderline: bool
    rule_pred: str
    llm_pred: Optional[str]
    llm_failed: bool
    llm_cost: float


def load_labeled_prompts() -> list[dict]:
    data = json.loads(LABELED_PATH.read_text(encoding="utf-8"))
    unlabeled = [d["id"] for d in data if not d.get("true_tier")]
    if unlabeled:
        raise SystemExit(
            f"{len(unlabeled)} prompts still have true_tier=null (e.g. {unlabeled[:5]}). "
            "Finish labeling before running the eval."
        )
    return data


class RateLimiter:
    """
    Caps calls to a rolling per-minute rate.

    The first full run of this eval used a plain concurrency semaphore
    (5 concurrent calls) with no awareness of the API's actual quota, and
    burst straight through Gemini's free-tier limit of 15 requests/minute for
    gemini-3.1-flash-lite (confirmed by the 429 body: 'limit: 15... FreeTier')
    -- despite this project's paid tier being enabled, so newer 3.x models
    evidently aren't covered by it yet. 48% of the 108-prompt eval failed as a
    result. A semaphore bounds concurrency, not throughput, so it can't
    prevent this; this limiter bounds actual call rate against a wall clock.
    """

    def __init__(self, rpm: int):
        self.rpm = rpm
        self._timestamps: collections.deque[float] = collections.deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] > 60:
                    self._timestamps.popleft()
                if len(self._timestamps) < self.rpm:
                    self._timestamps.append(now)
                    return
                wait = 60 - (now - self._timestamps[0]) + 0.1
                await asyncio.sleep(wait)


async def classify_rule_based(prompt: str) -> str:
    decision = await RuleBasedRouter().classify(prompt)
    return decision.tier.value


async def classify_llm(
    prompt: str, max_retries: int, limiter: RateLimiter
) -> tuple[Optional[str], bool, float]:
    """
    Classify with the LLM router, retrying on transient failure.

    A fresh LLMRouter is created on every attempt (and by the caller, per
    prompt) rather than reused, because LLMRouter.last_used_fallback and
    .last_response are per-instance mutable state set during classify() --
    sharing one instance across concurrent classify() calls would let them
    race and silently attribute one prompt's result to another.

    Returns (predicted_tier_or_None, failed, classification_cost_usd).
    A `None` prediction (llm_failed=True) means every attempt fell back to
    rules; the eval EXCLUDES these from LLM accuracy rather than silently
    scoring a rule-based answer as the LLM's.
    """
    calculator = get_cost_calculator()
    for attempt in range(max_retries + 1):
        await limiter.acquire()
        router = LLMRouter()
        decision = await router.classify(prompt)
        if not router.last_used_fallback:
            cost = 0.0
            if router.last_response is not None:
                estimate = calculator.estimate(
                    router.last_response.model,
                    router.last_response.prompt_tokens,
                    router.last_response.completion_tokens,
                )
                cost = estimate.estimated_cost
            return decision.tier.value, False, cost
        if attempt < max_retries:
            # A rate-limit failure needs a real backoff (Gemini's own 429
            # bodies quoted ~20s retry delays); anything else is likely a
            # one-off and a short backoff is enough.
            was_rate_limited = isinstance(router.last_error, ProviderRateLimitError)
            await asyncio.sleep(25.0 if was_rate_limited else 2.0 * (attempt + 1))
    return None, True, 0.0


async def run_eval(
    prompts: list[dict], rpm: int, max_retries: int, rule_only: bool
) -> list[PredictionRecord]:
    limiter = RateLimiter(rpm)
    order = {item["id"]: idx for idx, item in enumerate(prompts)}

    async def process(item: dict) -> PredictionRecord:
        rule_tier = await classify_rule_based(item["prompt"])

        if rule_only:
            llm_tier, llm_failed, llm_cost = None, True, 0.0
        else:
            llm_tier, llm_failed, llm_cost = await classify_llm(item["prompt"], max_retries, limiter)

        return PredictionRecord(
            id=item["id"],
            domain=item["domain"],
            prompt=item["prompt"],
            true_tier=item["true_tier"],
            borderline=item.get("borderline", False),
            rule_pred=rule_tier,
            llm_pred=llm_tier,
            llm_failed=llm_failed,
            llm_cost=llm_cost,
        )

    tasks = [asyncio.create_task(process(item)) for item in prompts]
    results = []
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        record = await coro
        results.append(record)
        llm_display = record.llm_pred or ("SKIPPED" if rule_only else "FAILED")
        marker = " " if record.rule_pred == record.true_tier else "x"
        print(
            f"  [{i:>3}/{len(tasks)}] {record.id:<10} true={record.true_tier:<8} "
            f"rule={record.rule_pred:<8}{marker}  llm={llm_display}"
        )

    results.sort(key=lambda r: order[r.id])
    return results


def compute_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    report = classification_report(
        y_true, y_pred, labels=TIERS, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=TIERS)
    return {
        "n": len(y_true),
        "accuracy": report["accuracy"],
        "macro_avg_recall": report["macro avg"]["recall"],
        "macro_avg_f1": report["macro avg"]["f1-score"],
        "confusion_matrix": cm.tolist(),
        "per_class": {t: report[t] for t in TIERS},
    }


def save_confusion_matrix_png(cm: list[list[int]], title: str, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")  # headless: we only ever save to file, never show a window
    import matplotlib.pyplot as plt

    arr = np.array(cm)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(arr, cmap="Blues")
    ax.set_xticks(range(len(TIERS)))
    ax.set_yticks(range(len(TIERS)))
    ax.set_xticklabels(TIERS)
    ax.set_yticklabels(TIERS)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    vmax = arr.max() if arr.max() > 0 else 1
    for i in range(len(TIERS)):
        for j in range(len(TIERS)):
            ax.text(
                j, i, str(arr[i, j]), ha="center", va="center",
                color="white" if arr[i, j] > vmax / 2 else "black",
            )
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def find_divergence(results: list[PredictionRecord]) -> list[dict]:
    """Prompts where rule-based and LLM-based classification disagreed."""
    diverged = []
    for r in results:
        if r.llm_pred is None or r.llm_pred == r.rule_pred:
            continue
        diverged.append(
            {
                "id": r.id,
                "true_tier": r.true_tier,
                "rule_pred": r.rule_pred,
                "rule_correct": r.rule_pred == r.true_tier,
                "llm_pred": r.llm_pred,
                "llm_correct": r.llm_pred == r.true_tier,
                "prompt_preview": r.prompt[:100],
            }
        )
    return diverged


def confusion_row_md(cm: list[list[int]]) -> str:
    header = "| true \\ pred | " + " | ".join(TIERS) + " |"
    sep = "|---" * (len(TIERS) + 1) + "|"
    rows = [header, sep]
    for i, tier in enumerate(TIERS):
        row = f"| **{tier}** | " + " | ".join(str(cm[i][j]) for j in range(len(TIERS))) + " |"
        rows.append(row)
    return "\n".join(rows)


def per_class_table_md(per_class: dict) -> str:
    header = "| tier | precision | recall | f1 | support |"
    sep = "|---|---|---|---|---|"
    rows = [header, sep]
    for tier in TIERS:
        c = per_class[tier]
        rows.append(
            f"| {tier} | {c['precision']:.2f} | {c['recall']:.2f} | "
            f"{c['f1-score']:.2f} | {int(c['support'])} |"
        )
    return "\n".join(rows)


def build_report(
    results: list[PredictionRecord],
    rule_all: dict,
    rule_clean: dict,
    llm_all: Optional[dict],
    llm_clean: Optional[dict],
    divergence: list[dict],
    llm_failures: list[str],
    total_llm_cost: float,
    domain_accuracy: dict,
) -> str:
    lines = ["# Phase 3 -- Classification Accuracy Report", ""]
    lines.append(f"`eval/labeled_prompts.json`, {len(results)} prompts, "
                 f"{sum(1 for r in results if r.borderline)} flagged borderline.")
    lines.append("")

    lines.append("## Headline numbers")
    lines.append("")
    lines.append("| classifier | n | accuracy | macro-avg recall |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Rule-based (all) | {rule_all['n']} | {rule_all['accuracy']:.1%} | {rule_all['macro_avg_recall']:.1%} |")
    lines.append(f"| Rule-based (excl. borderline) | {rule_clean['n']} | {rule_clean['accuracy']:.1%} | {rule_clean['macro_avg_recall']:.1%} |")
    if llm_all:
        lines.append(f"| LLM-based (all) | {llm_all['n']} | {llm_all['accuracy']:.1%} | {llm_all['macro_avg_recall']:.1%} |")
        lines.append(f"| LLM-based (excl. borderline) | {llm_clean['n']} | {llm_clean['accuracy']:.1%} | {llm_clean['macro_avg_recall']:.1%} |")
    else:
        lines.append("| LLM-based | -- | not run (--rule-only) | -- |")
    lines.append("")
    lines.append(
        "**Accuracy** is the naive score. **Macro-avg recall** averages per-class "
        "recall instead of pooling all prompts, so it isn't inflated by whichever "
        "tier happens to be the majority class in this dataset (SIMPLE, at 55%) -- "
        "treat macro-avg recall as the more honest number here."
    )
    lines.append("")

    if llm_all is not None and llm_failures:
        lines.append(
            f"**{len(llm_failures)} prompt(s) excluded from LLM accuracy** after exhausting "
            f"retries (all attempts fell back to rules): {', '.join(llm_failures)}. "
            "These are NOT scored as LLM predictions -- doing so would silently "
            "attribute a rule-based answer to the LLM classifier."
        )
        lines.append("")

    if llm_all:
        lines.append(f"LLM classification cost for this full eval run: **${total_llm_cost:.6f}** "
                     f"({rule_all['n'] - len(llm_failures)} successful calls).")
        lines.append("")

    lines.append("## Confusion matrices (all prompts, including borderline)")
    lines.append("")
    lines.append("### Rule-based")
    lines.append("")
    lines.append(confusion_row_md(rule_all["confusion_matrix"]))
    lines.append("")
    lines.append(per_class_table_md(rule_all["per_class"]))
    lines.append("")
    if llm_all:
        lines.append("### LLM-based")
        lines.append("")
        lines.append(confusion_row_md(llm_all["confusion_matrix"]))
        lines.append("")
        lines.append(per_class_table_md(llm_all["per_class"]))
        lines.append("")

    lines.append("## Accuracy by domain (rule-based)")
    lines.append("")
    lines.append("| domain | n | accuracy |")
    lines.append("|---|---|---|")
    for domain, (correct, total) in sorted(domain_accuracy.get("rule", {}).items()):
        lines.append(f"| {domain} | {total} | {correct/total:.1%} |")
    lines.append("")
    if llm_all:
        lines.append("## Accuracy by domain (LLM-based)")
        lines.append("")
        lines.append("| domain | n | accuracy |")
        lines.append("|---|---|---|")
        for domain, (correct, total) in sorted(domain_accuracy.get("llm", {}).items()):
            lines.append(f"| {domain} | {total} | {correct/total:.1%} |")
        lines.append("")

    if divergence:
        lines.append(f"## Where the two classifiers disagree ({len(divergence)} prompts)")
        lines.append("")
        lines.append(
            "By definition rule_pred != llm_pred here, so exactly one of them can "
            "match true_tier, or neither can -- \"both correct\" isn't a possible "
            "outcome in this table."
        )
        lines.append("")
        lines.append("| id | true | rule pred | llm pred | who was right |")
        lines.append("|---|---|---|---|---|")
        for d in divergence:
            who = "rule" if d["rule_correct"] else "llm" if d["llm_correct"] else "neither"
            lines.append(
                f"| {d['id']} | {d['true_tier']} | {d['rule_pred']} | {d['llm_pred']} | {who} |"
            )
        lines.append("")
        rule_wins = sum(1 for d in divergence if d["rule_correct"])
        llm_wins = sum(1 for d in divergence if d["llm_correct"])
        neither = sum(1 for d in divergence if not d["rule_correct"] and not d["llm_correct"])
        lines.append(
            f"Of {len(divergence)} disagreements: rule-correct={rule_wins}, "
            f"llm-correct={llm_wins}, neither-correct={neither}."
        )
        lines.append("")

    lines.append("## Misclassified prompts (rule-based)")
    lines.append("")
    for r in results:
        if r.rule_pred != r.true_tier:
            lines.append(f"- `{r.id}` true=**{r.true_tier}** pred=**{r.rule_pred}** -- {r.prompt[:90]}")
    lines.append("")

    if llm_all:
        lines.append("## Misclassified prompts (LLM-based)")
        lines.append("")
        for r in results:
            if r.llm_pred is not None and r.llm_pred != r.true_tier:
                lines.append(f"- `{r.id}` true=**{r.true_tier}** pred=**{r.llm_pred}** -- {r.prompt[:90]}")
        lines.append("")

    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 classification accuracy eval")
    parser.add_argument("--rule-only", action="store_true", help="Skip LLM classification (no API calls)")
    parser.add_argument(
        "--rpm", type=int, default=12,
        help="Max LLM classification calls per rolling 60s window. Gemini's free-tier "
        "cap observed for gemini-3.1-flash-lite was 15/min despite paid tier being "
        "enabled on this project; 12 leaves headroom. Raise this once billing/quota "
        "is confirmed to cover the classifier model.",
    )
    parser.add_argument("--max-retries", type=int, default=2, help="Retries per prompt on LLM failure")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    prompts = load_labeled_prompts()
    print(f"Loaded {len(prompts)} labeled prompts.\n")

    results = await run_eval(prompts, args.rpm, args.max_retries, args.rule_only)

    (RESULTS_DIR / "classification_predictions.json").write_text(
        json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    clean_results = [r for r in results if not r.borderline]

    rule_all = compute_metrics([r.true_tier for r in results], [r.rule_pred for r in results])
    rule_clean = compute_metrics(
        [r.true_tier for r in clean_results], [r.rule_pred for r in clean_results]
    )

    llm_failures = [r.id for r in results if r.llm_failed]
    llm_scored = [r for r in results if not r.llm_failed]
    llm_scored_clean = [r for r in clean_results if not r.llm_failed]

    llm_all = llm_clean = None
    if not args.rule_only and llm_scored:
        llm_all = compute_metrics([r.true_tier for r in llm_scored], [r.llm_pred for r in llm_scored])
        llm_clean = compute_metrics(
            [r.true_tier for r in llm_scored_clean], [r.llm_pred for r in llm_scored_clean]
        )

    total_llm_cost = sum(r.llm_cost for r in results)

    def domain_acc(records, pred_attr):
        acc: dict[str, list[int]] = {}
        for r in records:
            pred = getattr(r, pred_attr)
            if pred is None:
                continue
            correct, total = acc.get(r.domain, (0, 0))
            acc[r.domain] = (correct + (1 if pred == r.true_tier else 0), total + 1)
        return acc

    domain_accuracy = {
        "rule": domain_acc(results, "rule_pred"),
        "llm": domain_acc(results, "llm_pred") if llm_all else {},
    }

    divergence = find_divergence(results) if llm_all else []

    save_confusion_matrix_png(
        rule_all["confusion_matrix"], "Rule-based classifier",
        RESULTS_DIR / "confusion_matrix_rule.png",
    )
    if llm_all:
        save_confusion_matrix_png(
            llm_all["confusion_matrix"], "LLM-based classifier",
            RESULTS_DIR / "confusion_matrix_llm.png",
        )

    report = build_report(
        results, rule_all, rule_clean, llm_all, llm_clean,
        divergence, llm_failures, total_llm_cost, domain_accuracy,
    )
    (RESULTS_DIR / "classification_report.md").write_text(report, encoding="utf-8")

    (RESULTS_DIR / "classification_metrics.json").write_text(
        json.dumps(
            {
                "rule_all": rule_all, "rule_clean": rule_clean,
                "llm_all": llm_all, "llm_clean": llm_clean,
                "llm_failures": llm_failures, "total_llm_cost": total_llm_cost,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 68)
    print(f"Rule-based accuracy:  {rule_all['accuracy']:.1%}  (macro-avg recall {rule_all['macro_avg_recall']:.1%})")
    if llm_all:
        print(f"LLM-based accuracy:   {llm_all['accuracy']:.1%}  (macro-avg recall {llm_all['macro_avg_recall']:.1%})")
        if llm_failures:
            print(f"  ({len(llm_failures)} prompts excluded after exhausting retries: {llm_failures})")
        print(f"Classification cost for this run: ${total_llm_cost:.6f}")
    print(f"\nFull report: {RESULTS_DIR / 'classification_report.md'}")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(main())
