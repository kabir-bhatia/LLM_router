# Phase 5 -- Semantic Cache Threshold Validation

54 hand-labeled prompt pairs, embedded with the production model (`sentence-transformers/all-MiniLM-L6-v2`, local, no API calls), swept across similarity thresholds from 0.50 to 1.00.

**Why precision matters more than recall here:** a false positive (cache fires when it shouldn't) means the system *silently serves a wrong cached answer* -- an invisible correctness bug the user has no way to detect. A false negative (cache doesn't fire when it safely could) just means one extra real generation, costing a few cents. The recommendation below is optimized accordingly: F0.5 weights precision over recall, and a second, stricter framing asks for the most permissive threshold that still keeps precision at or above 97% on this dataset.

## Where the current default (0.92) actually sits

At threshold **0.92**: precision **81.2%**, recall **59.1%** (TP=13, FP=3, FN=9, TN=29).

**3 pair(s) would be dangerously cached at 0.92** -- similarity high enough to fire the cache despite the two prompts needing genuinely different answers:

- `trap-07` (sim=0.9600, narrower_or_broader): "Summarize this refund policy: Refunds are issued within 5 business days." vs. "Summarize this refund policy: Refunds are issued within 30 business days, no exceptions."
- `trap-09` (sim=0.9839, narrower_or_broader): "Design a rate limiter for a single-region API with 1,000 requests/second." vs. "Design a rate limiter for a multi-region API with 100,000 requests/second."
- `trap-12` (sim=0.9936, narrower_or_broader): "Explain why a company might choose a direct listing over an IPO." vs. "Explain why a company might choose an IPO over a direct listing."

## Recommendations

**By F0.5 (precision-weighted) optimum:** threshold **0.82** -- precision 79.2%, recall 86.4%.

**By precision floor (97% minimum):** the most permissive (lowest, so highest-recall) threshold that still keeps precision at or above 97% is **1.00** -- precision 100.0%, recall 9.1%.

## Verdict

**0.92 is riskier than it looks.** 3 false positive(s) at that threshold mean it does occasionally serve a wrong cached answer on prompts this pattern-matched against. A threshold closer to 1.00 would close that gap at some cost to recall.

## Full sweep (selected thresholds)

| threshold | precision | recall | TP | FP | FN | TN |
|---|---|---|---|---|---|---|
| 0.60 | 62.9% | 100.0% | 22 | 13 | 0 | 19 |
| 0.62 | 63.6% | 95.5% | 21 | 12 | 1 | 20 |
| 0.64 | 63.6% | 95.5% | 21 | 12 | 1 | 20 |
| 0.66 | 65.6% | 95.5% | 21 | 11 | 1 | 21 |
| 0.68 | 67.7% | 95.5% | 21 | 10 | 1 | 22 |
| 0.70 | 66.7% | 90.9% | 20 | 10 | 2 | 22 |
| 0.72 | 71.4% | 90.9% | 20 | 8 | 2 | 24 |
| 0.74 | 71.4% | 90.9% | 20 | 8 | 2 | 24 |
| 0.76 | 74.1% | 90.9% | 20 | 7 | 2 | 25 |
| 0.78 | 74.1% | 90.9% | 20 | 7 | 2 | 25 |
| 0.80 | 76.0% | 86.4% | 19 | 6 | 3 | 26 |
| 0.82 | 79.2% | 86.4% | 19 | 5 | 3 | 27 |
| 0.84 | 79.2% | 86.4% | 19 | 5 | 3 | 27 |
| 0.86 | 78.3% | 81.8% | 18 | 5 | 4 | 27 |
| 0.88 | 77.3% | 77.3% | 17 | 5 | 5 | 27 |
| 0.90 | 78.9% | 68.2% | 15 | 4 | 7 | 28 |
| 0.92 | 81.2% | 59.1% | 13 | 3 | 9 | 29 |
| 0.94 | 80.0% | 54.5% | 12 | 3 | 10 | 29 |
| 0.96 | 80.0% | 36.4% | 8 | 2 | 14 | 30 |
| 0.98 | 80.0% | 36.4% | 8 | 2 | 14 | 30 |
| 1.00 | 100.0% | 9.1% | 2 | 0 | 20 | 32 |

## Similarity by category (sanity check on the dataset itself)

| category | n | mean sim | min | max |
|---|---|---|---|---|
| exact_duplicate | 8 | 0.9864 | 0.9200 | 1.0000 |
| paraphrase | 14 | 0.8726 | 0.6077 | 0.9809 |
| narrower_or_broader | 12 | 0.8147 | 0.6084 | 0.9936 |
| related_topic_different_ask | 12 | 0.3910 | 0.0868 | 0.6455 |
| unrelated | 8 | 0.0473 | -0.0465 | 0.1408 |

If `narrower_or_broader` (the trap category -- same template, different correct answer) overlaps heavily with `paraphrase` in this table, that's the actual argument for why validating the threshold empirically matters: lexical/structural similarity and semantic *safety-to-cache* are not the same thing, and a threshold picked by eyeballing a couple of examples can't tell them apart.
