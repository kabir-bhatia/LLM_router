"""
Phase 5 -- Semantic-cache threshold validation.

The semantic cache in src/services/semantic_cache.py hardcoded a 0.92 cosine
similarity threshold with no validation behind it (settings.semantic_similarity_threshold
now controls it, but the value itself was never actually checked against
anything). This script is that check.

Method: embed both sides of each pair in eval/cache_pairs.json with the same
local model production uses (sentence-transformers/all-MiniLM-L6-v2, via
src/services/embeddings.py), compute cosine similarity (a dot product, since
the vectors are already L2-normalized), then sweep the threshold and measure
precision/recall against the hand-set should_cache_hit label.

No API calls, no Redis -- pure local embeddings + numpy. Runs in seconds.

Usage:
    .venv/Scripts/python.exe -m eval.threshold_sweep

Outputs (eval/results/):
    threshold_sweep_report.md
    threshold_sweep_pairs.json      -- every pair with its measured similarity
    threshold_sweep_curve.png       -- precision/recall vs threshold
    threshold_sweep_distribution.png -- similarity scores by category
"""

import json
from pathlib import Path

import numpy as np

from src.services.embeddings import get_embeddings_service

PAIRS_PATH = Path("eval/cache_pairs.json")
RESULTS_DIR = Path("eval/results")

# Precision matters more than recall here: a false positive means the cache
# silently serves a WRONG cached answer for a different question (an invisible
# correctness bug); a false negative just means a cache miss, which costs a
# few cents and a normal generation. F0.5 weights precision 4x recall's
# contribution -- deliberately, not a default choice.
F_BETA = 0.5

# The precision floor used for the second recommendation strategy below.
MIN_ACCEPTABLE_PRECISION = 0.97


def load_pairs() -> list[dict]:
    return json.loads(PAIRS_PATH.read_text(encoding="utf-8"))


def compute_similarities(pairs: list[dict]) -> list[dict]:
    """
    Embed every unique prompt once, then compute cosine similarity per pair.

    Embeds one prompt at a time via embed_sync rather than batching through
    embed_batch_sync. The batch path (SentenceTransformer.encode on a list)
    reproducibly segfaulted / hit MemoryError on this machine under real
    memory pressure (~12GB across processes, Windows actively compressing
    memory) -- likely a spike in the batch code path's memory use, not
    anything specific to this dataset's ~100 prompts. Single-string encode
    never failed once across repeated tries, and at this dataset size the
    per-call overhead is irrelevant (a few dozen prompts, each well under a
    second).
    """
    embeddings_service = get_embeddings_service()

    unique_prompts = sorted({p["prompt_a"] for p in pairs} | {p["prompt_b"] for p in pairs})
    vector_by_prompt = {prompt: np.array(embeddings_service.embed_sync(prompt)) for prompt in unique_prompts}

    enriched = []
    for pair in pairs:
        va = vector_by_prompt[pair["prompt_a"]]
        vb = vector_by_prompt[pair["prompt_b"]]
        similarity = float(np.dot(va, vb))  # vectors are L2-normalized -> dot product == cosine similarity
        enriched.append({**pair, "similarity": similarity})
    return enriched


def precision_recall_at(pairs: list[dict], threshold: float) -> dict:
    tp = fp = fn = tn = 0
    for p in pairs:
        predicted_hit = p["similarity"] >= threshold
        actual_safe = p["should_cache_hit"]
        if predicted_hit and actual_safe:
            tp += 1
        elif predicted_hit and not actual_safe:
            fp += 1
        elif not predicted_hit and actual_safe:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0  # no predicted hits -> vacuously precise
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f_beta = (
        (1 + F_BETA**2) * precision * recall / (F_BETA**2 * precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {
        "threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f_beta": f_beta,
    }


def sweep(pairs: list[dict], step: float = 0.01) -> list[dict]:
    thresholds = np.arange(0.50, 1.00 + step, step)
    return [precision_recall_at(pairs, round(float(t), 4)) for t in thresholds]


def recommend_thresholds(curve: list[dict]) -> dict:
    best_f_beta = max(curve, key=lambda r: r["f_beta"])

    precision_gated = [r for r in curve if r["precision"] >= MIN_ACCEPTABLE_PRECISION]
    most_permissive_safe = min(precision_gated, key=lambda r: r["threshold"]) if precision_gated else None

    return {"best_f_beta": best_f_beta, "most_permissive_safe": most_permissive_safe}


def save_curve_png(curve: list[dict], default_threshold: float, recommended: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    thresholds = [r["threshold"] for r in curve]
    precision = [r["precision"] for r in curve]
    recall = [r["recall"] for r in curve]
    f_beta = [r["f_beta"] for r in curve]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(thresholds, precision, label="Precision", linewidth=2)
    ax.plot(thresholds, recall, label="Recall", linewidth=2)
    ax.plot(thresholds, f_beta, label=f"F{F_BETA} (precision-weighted)", linewidth=1.5, linestyle="--")

    ax.axvline(default_threshold, color="gray", linestyle=":", label=f"Current default ({default_threshold})")
    if recommended["most_permissive_safe"]:
        rec_t = recommended["most_permissive_safe"]["threshold"]
        ax.axvline(rec_t, color="green", linestyle=":", label=f"Recommended ({rec_t:.2f})")

    ax.set_xlabel("Similarity threshold")
    ax.set_ylabel("Score")
    ax.set_title("Semantic cache: precision/recall vs. similarity threshold")
    ax.legend(loc="lower left", fontsize=9)
    ax.set_ylim(-0.05, 1.05)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_distribution_png(pairs: list[dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    categories = ["exact_duplicate", "paraphrase", "narrower_or_broader", "related_topic_different_ask", "unrelated"]
    labels = ["exact\nduplicate", "paraphrase", "trap\n(narrower/broader)", "related,\ndifferent ask", "unrelated"]
    colors = ["#2ca02c", "#98df8a", "#d62728", "#ff9896", "#1f77b4"]

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, (cat, label, color) in enumerate(zip(categories, labels, colors)):
        sims = [p["similarity"] for p in pairs if p["category"] == cat]
        jitter = np.random.default_rng(42).uniform(-0.15, 0.15, size=len(sims))
        ax.scatter([i + j for j in jitter], sims, color=color, alpha=0.8, s=40)

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(labels, fontsize=9)
    ax.axhline(0.92, color="gray", linestyle=":", label="Current default (0.92)")
    ax.set_ylabel("Cosine similarity")
    ax.set_title("Similarity by pair category (should_cache_hit only for exact_duplicate/paraphrase)")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_report(pairs: list[dict], curve: list[dict], default_threshold: float, recommended: dict) -> str:
    default_stats = min(curve, key=lambda r: abs(r["threshold"] - default_threshold))
    best_f = recommended["best_f_beta"]
    safe = recommended["most_permissive_safe"]

    lines = ["# Phase 5 -- Semantic Cache Threshold Validation", ""]
    lines.append(
        f"{len(pairs)} hand-labeled prompt pairs, embedded with the production model "
        "(`sentence-transformers/all-MiniLM-L6-v2`, local, no API calls), swept across "
        "similarity thresholds from 0.50 to 1.00."
    )
    lines.append("")
    lines.append(
        "**Why precision matters more than recall here:** a false positive (cache fires when "
        "it shouldn't) means the system *silently serves a wrong cached answer* -- an invisible "
        "correctness bug the user has no way to detect. A false negative (cache doesn't fire when "
        "it safely could) just means one extra real generation, costing a few cents. The "
        f"recommendation below is optimized accordingly: F{F_BETA} weights precision over recall, "
        f"and a second, stricter framing asks for the most permissive threshold that still keeps "
        f"precision at or above {MIN_ACCEPTABLE_PRECISION:.0%} on this dataset."
    )
    lines.append("")

    lines.append("## Where the current default (0.92) actually sits")
    lines.append("")
    lines.append(
        f"At threshold **{default_stats['threshold']:.2f}**: precision "
        f"**{default_stats['precision']:.1%}**, recall **{default_stats['recall']:.1%}** "
        f"(TP={default_stats['tp']}, FP={default_stats['fp']}, FN={default_stats['fn']}, "
        f"TN={default_stats['tn']})."
    )
    if default_stats["fp"] > 0:
        fp_examples = [
            p for p in pairs
            if p["similarity"] >= default_stats["threshold"] and not p["should_cache_hit"]
        ]
        lines.append("")
        lines.append(
            f"**{len(fp_examples)} pair(s) would be dangerously cached at 0.92** -- similarity "
            "high enough to fire the cache despite the two prompts needing genuinely different "
            "answers:"
        )
        lines.append("")
        for p in fp_examples:
            lines.append(
                f"- `{p['id']}` (sim={p['similarity']:.4f}, {p['category']}): "
                f"\"{p['prompt_a']}\" vs. \"{p['prompt_b']}\""
            )
        lines.append("")
    else:
        lines.append("")
        lines.append("Zero false positives at 0.92 on this dataset -- it never fired incorrectly here.")
        lines.append("")

    lines.append("## Recommendations")
    lines.append("")
    lines.append(f"**By F{F_BETA} (precision-weighted) optimum:** threshold **{best_f['threshold']:.2f}** "
                 f"-- precision {best_f['precision']:.1%}, recall {best_f['recall']:.1%}.")
    lines.append("")
    if safe:
        lines.append(
            f"**By precision floor ({MIN_ACCEPTABLE_PRECISION:.0%} minimum):** the most permissive "
            f"(lowest, so highest-recall) threshold that still keeps precision at or above "
            f"{MIN_ACCEPTABLE_PRECISION:.0%} is **{safe['threshold']:.2f}** -- precision "
            f"{safe['precision']:.1%}, recall {safe['recall']:.1%}."
        )
    else:
        lines.append(
            f"No threshold in the sweep range reaches {MIN_ACCEPTABLE_PRECISION:.0%} precision on "
            "this dataset -- see the false positives above for why."
        )
    lines.append("")

    verdict_default_precision = default_stats["precision"]
    if verdict_default_precision >= MIN_ACCEPTABLE_PRECISION and default_stats["fp"] == 0:
        verdict = (
            f"**0.92 holds up.** It has zero false positives on this dataset and its recall "
            f"({default_stats['recall']:.1%}) is close to what the recommended thresholds achieve -- "
            "there isn't a clearly better value to switch to based on this evidence."
        )
    elif safe and safe["threshold"] < default_stats["threshold"]:
        verdict = (
            f"**0.92 is more conservative than it needs to be.** A threshold around "
            f"{safe['threshold']:.2f} keeps the same precision floor while catching more genuine "
            "duplicates (higher recall) -- 0.92 is leaving real cache hits, and real savings, on "
            "the table."
        )
    elif safe and safe["threshold"] > default_stats["threshold"]:
        verdict = (
            f"**0.92 is riskier than it looks.** {default_stats['fp']} false positive(s) at that "
            f"threshold mean it does occasionally serve a wrong cached answer on prompts this "
            f"pattern-matched against. A threshold closer to {safe['threshold']:.2f} would close "
            "that gap at some cost to recall."
        )
    else:
        verdict = "See the precision/recall figures above -- no clean single-line verdict for this dataset."
    lines.append(f"## Verdict\n\n{verdict}")
    lines.append("")

    lines.append("## Full sweep (selected thresholds)")
    lines.append("")
    lines.append("| threshold | precision | recall | TP | FP | FN | TN |")
    lines.append("|---|---|---|---|---|---|---|")
    shown = {round(t, 2) for t in np.arange(0.60, 1.00, 0.02)} | {default_stats["threshold"], best_f["threshold"]}
    if safe:
        shown.add(safe["threshold"])
    for r in curve:
        if round(r["threshold"], 2) in {round(s, 2) for s in shown}:
            lines.append(
                f"| {r['threshold']:.2f} | {r['precision']:.1%} | {r['recall']:.1%} | "
                f"{r['tp']} | {r['fp']} | {r['fn']} | {r['tn']} |"
            )
    lines.append("")

    lines.append("## Similarity by category (sanity check on the dataset itself)")
    lines.append("")
    lines.append("| category | n | mean sim | min | max |")
    lines.append("|---|---|---|---|---|")
    for cat in ["exact_duplicate", "paraphrase", "narrower_or_broader", "related_topic_different_ask", "unrelated"]:
        sims = [p["similarity"] for p in pairs if p["category"] == cat]
        if not sims:
            continue
        lines.append(f"| {cat} | {len(sims)} | {np.mean(sims):.4f} | {min(sims):.4f} | {max(sims):.4f} |")
    lines.append("")
    lines.append(
        "If `narrower_or_broader` (the trap category -- same template, different correct answer) "
        "overlaps heavily with `paraphrase` in this table, that's the actual argument for why "
        "validating the threshold empirically matters: lexical/structural similarity and semantic "
        "*safety-to-cache* are not the same thing, and a threshold picked by eyeballing a couple of "
        "examples can't tell them apart."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from src.config import get_settings

    default_threshold = get_settings().semantic_similarity_threshold

    pairs = load_pairs()
    print(f"Loaded {len(pairs)} pairs. Embedding locally (no API calls)...")
    pairs = compute_similarities(pairs)

    (RESULTS_DIR / "threshold_sweep_pairs.json").write_text(
        json.dumps(pairs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    curve = sweep(pairs)
    recommended = recommend_thresholds(curve)

    save_curve_png(curve, default_threshold, recommended, RESULTS_DIR / "threshold_sweep_curve.png")
    save_distribution_png(pairs, RESULTS_DIR / "threshold_sweep_distribution.png")

    report = build_report(pairs, curve, default_threshold, recommended)
    (RESULTS_DIR / "threshold_sweep_report.md").write_text(report, encoding="utf-8")

    default_stats = min(curve, key=lambda r: abs(r["threshold"] - default_threshold))
    print("\n" + "=" * 68)
    print(f"At default {default_threshold}: precision={default_stats['precision']:.1%} recall={default_stats['recall']:.1%}")
    print(f"Best F{F_BETA}: threshold={recommended['best_f_beta']['threshold']:.2f} "
          f"precision={recommended['best_f_beta']['precision']:.1%} recall={recommended['best_f_beta']['recall']:.1%}")
    if recommended["most_permissive_safe"]:
        s = recommended["most_permissive_safe"]
        print(f"Most permissive @ >={MIN_ACCEPTABLE_PRECISION:.0%} precision: threshold={s['threshold']:.2f} recall={s['recall']:.1%}")
    print(f"\nFull report: {RESULTS_DIR / 'threshold_sweep_report.md'}")
    print("=" * 68)


if __name__ == "__main__":
    main()
