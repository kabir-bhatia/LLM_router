# Project Log

Extending [Asirwad/smart-llm-router](https://github.com/Asirwad/smart-llm-router) into a
placement-ready project: labeled evaluation harness, cost/accuracy tradeoff analysis,
and semantic-cache threshold validation.

Working directory: `D:\LLM_Router`

---

## Phase 1 — Setup & Understanding

**Status: complete.** `/v1/complete` returns a routed response with `model_used`,
`difficulty_tag`, `estimated_cost` via the real HTTP API, not just unit-level checks.
Full test suite: 37 passed, 1 skipped (Redis, off by design — see below).

### Stack decisions

| Component | Upstream | This project | Why |
|---|---|---|---|
| Database | PostgreSQL | SQLite (`aiosqlite`) | Zero-setup, single file, no server to run |
| Simple/Medium/Complex models | Ollama (local Granite) + Gemini Flash/Pro | Gemini only, three tiers | One provider, one auth path, no local model server |
| Embeddings | Ollama (`nomic-embed-text`, 768-dim) | Local `sentence-transformers/all-MiniLM-L6-v2` (384-dim) | No network round-trip; Phase 5 re-embeds the corpus on every sweep run, which would be slow and rate-limited against an API |
| Semantic cache | Redis Stack (RediSearch), assumed always up | Same, but **off by default**, degrades to no-op when absent | No Docker on this machine; Phase 5 (the actual novel contribution) needs only numpy, not a running cache |

### Model tiers (as of 2026-08-15)

Gemini's lineup has moved to a 3.x generation since my training data. Checked
`client.models.list()` directly against the live API key rather than assuming.

| Tier | Model | Input $/1M | Output $/1M | Notes |
|---|---|---|---|---|
| SIMPLE | `gemini-3.1-flash-lite` | $0.25 | $1.50 | also used as the classifier model |
| MEDIUM | `gemini-3.6-flash` | $0.75 | $3.75 | promotional pricing through 2026-12-31, ~2x after |
| COMPLEX | `gemini-3.5-flash` | $1.50 | $9.00 | **see quota issue below** |

**Quota issue found live, not anticipated:** `gemini-2.5-pro` — the intended COMPLEX
model and the only GA Pro-tier model — returned `404 "no longer available to new
users"` on this project's key. The preview Pro alternatives
(`gemini-3.1-pro-preview`, `gemini-pro-latest`) both returned `429 RESOURCE_EXHAUSTED`
despite the paid tier being enabled. Worth checking billing/quota at
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) — Pro-tier access
may need to be explicitly requested or a different project used.

Landed on `gemini-3.5-flash` as a working stand-in: GA, reliable on this key, and
genuinely pricier than MEDIUM ($1.50/$9.00 vs $0.75/$3.75), which is what actually
matters — the tier cost *ordering* has to hold or "escalating to COMPLEX" would be a
cost decrease, which breaks the entire premise of the router. (`gemini-2.5-flash` was
briefly considered and rejected for exactly this reason: it's *cheaper* than MEDIUM.)

Switching back to `gemini-2.5-pro` once quota is resolved is a one-line change —
`TIER_COMPLEX_MODEL` in `.env`, plus updating `BASELINE_MODEL` in
[src/services/cost.py](src/services/cost.py) — both models are already priced in the
table.

### Bugs found and fixed along the way

These weren't refactors for their own sake — each one would have corrupted a number
this project reports.

1. **Silent classifier fallback** ([src/core/router.py](src/core/router.py)) —
   `LLMRouter.classify()` fell back to rule-based classification on *any* exception,
   silently. An eval run where the API key was wrong or every call errored would have
   reported rule-based accuracy as if it were the LLM's. Added
   `LLMRouter.last_used_fallback`, which `scripts/verify_setup.py` checks.

2. **Pricing lookup guessed instead of failing** ([src/services/cost.py](src/services/cost.py)) —
   Unknown models fell back to prefix-matching (`"gemini-2.0-flash-lite"` matches the
   `"gemini-2.0-flash"` key by `startswith`, so a lite request could bill at the pricier
   flash rate depending on dict ordering), and *further* fell back to baseline pricing
   for anything still unmatched — silently reporting 0% savings for a misconfigured
   model instead of erroring. Now raises `KeyError` with the list of known models.
   Every cost figure in Phases 3-4 depends on this table being exact.

3. **Error misclassification via substring matching** ([src/providers/gemini.py](src/providers/gemini.py)) —
   Found live, mid-verification: a `404 "model deprecated"` error from Gemini got
   classified as a **rate limit**, because the error message linked to
   `.../docs/migrate-to-interactions`, and the string `"migrate"` contains the
   substring `"rate"`. That misclassification would have sent the retry/backoff logic
   into repeated retries of a permanently-failing request instead of failing fast.
   Replaced with branching on the SDK's structured `APIError.code` (HTTP status).

4. **"Best model" override was dead by default** ([src/core/router.py](src/core/router.py)) —
   The keyword override (user says "give me the best model" → force COMPLEX) only
   existed in `RuleBasedRouter.classify()`. `use_llm_router=True` is the default, and
   `LLMRouter.classify()` never checked it — so a real user-facing feature silently did
   nothing under the default configuration. Extracted to a shared
   `_best_model_override()` helper both routers call, before spending an API call on
   classification.

5. **Windows console crash on startup** ([src/main.py](src/main.py)) — the emoji in
   the startup/shutdown log lines crash the FastAPI lifespan handler under Windows'
   default `cp1252` console encoding (`UnicodeEncodeError`), which meant the server
   never actually started on this machine. Fixed by reconfiguring stdout/stderr to
   UTF-8 at import time.

6. **Postgres-only types** ([src/db/models.py](src/db/models.py), [src/db/session.py](src/db/session.py)) —
   `sqlalchemy.dialects.postgresql.UUID` → dialect-generic `sqlalchemy.Uuid`. Connection
   pool kwargs (`pool_size`, `max_overflow`, `pool_recycle`) are Postgres-only and
   `aiosqlite` raises `TypeError` on them — now applied conditionally.

7. **Broken pre-existing unit test** ([tests/test_router.py](tests/test_router.py)) —
   asserted `get_router()` always returns `RuleBasedRouter`, which was never true given
   `use_llm_router` defaults to `True`. Fixed to assert the actual contract (factory
   honors the setting).

### Environment setup notes (Windows-specific)

- `py` (the Windows Python launcher) defaulted to **Python 3.13t**, the experimental
  free-threaded build, not standard 3.13. The `cp313t` ABI has no numpy/torch wheels,
  so `pip install` silently fell back to compiling numpy from source via meson and
  failed with an unrelated-looking error. Fix: `py -3.13` explicitly when creating the
  venv, not bare `py`.
- No Docker on this machine, which is the other reason Redis was deferred rather than
  containerized.

### What Phase 1's exit criteria actually required (and how it was verified)

> "Working local deployment, you can walk through every file's logic unaided."

Verified via `scripts/verify_setup.py` (6 checks: config → DB → embeddings →
classifier → generation → pricing coverage) and a live end-to-end HTTP round trip:
minted an API key via `POST /v1/keys`, then called `POST /v1/complete` for both a
SIMPLE prompt (routed to `gemini-3.1-flash-lite`, cost $0.000093, $0.000466 saved vs.
baseline) and a COMPLEX prompt (routed to `gemini-3.5-flash`, cost $0.0023, $0.00
saved — correctly $0, since that model *is* the baseline).

---

## Phase 2 — Build Your Own Evaluation Data

**Status: complete, but with an important caveat below.**

- Rubric written: [eval/LABELING_RUBRIC.md](eval/LABELING_RUBRIC.md) — defines
  SIMPLE/MEDIUM/COMPLEX by "cheapest tier that still gives an acceptable answer" (not
  prompt length or vibe), five tie-breaking rules, a `borderline` flag for genuinely
  ambiguous cases, target balance of ~33% per tier.
- 108 candidates written: [eval/candidate_prompts.json](eval/candidate_prompts.json) —
  support (24), codegen (24), architecture (24), analysis (24), summarization (12).
- **Labels applied**: [eval/labeled_prompts.json](eval/labeled_prompts.json), via
  [scripts/apply_phase2_labels.py](scripts/apply_phase2_labels.py). Distribution: 55%
  simple / 14% medium / 31% complex, 5 flagged borderline — skewed away from the ~33%
  target, left as-is rather than gamed to hit quota (adjusting labels just to balance
  tiers would corrupt the ground truth itself, which defeats the point of the exercise).

**Caveat, stated plainly:** the plan's own ground rule was that candidate prompts could
be generated, but labels had to be assigned by hand — specifically because that's what
makes the eval set a defensible artifact when questioned about it later, rather than a
rerun of someone else's numbers. The user explicitly directed Claude to do the labeling
instead of doing it themselves. That instruction was followed, but every COMPLEX and
borderline label carries a `note` explaining the reasoning, and `eval/README.md` now
says explicitly: **read `labeled_prompts.json` and adjust anything that doesn't match
your own judgment before treating this as your own hand-labeled work** — the value of
that claim on a CV depends on being able to defend individual labels in an interview,
which only holds if they're labels you'd actually stand behind.

---

## Phase 3 — Measure Classifier Accuracy

**Status: complete.** [eval/eval_classification.py](eval/eval_classification.py) runs
the labeled set through classification only (no generation) for both routers and
produces [eval/results/classification_report.md](eval/results/classification_report.md),
per-prompt predictions, raw metrics JSON, and confusion-matrix PNGs.

### Headline numbers (108 prompts, 5 borderline)

| classifier | accuracy | macro-avg recall |
|---|---|---|
| Rule-based | 50.9% | 41.0% |
| LLM-based (`gemini-3.1-flash-lite`) | 79.6% | 82.6% |

Macro-avg recall (per-class recall, averaged) is reported alongside raw accuracy
specifically because the dataset is 55% SIMPLE — raw accuracy alone would flatter
whichever classifier defaults toward the majority class.

**The most quotable finding:** the rule-based classifier's confusion matrix has an
**all-zero COMPLEX column** — it never once predicted COMPLEX across all 108 prompts,
even though 34 of them were labeled COMPLEX (0.00 precision/recall on that class). Its
scoring function tops out accumulating points toward MEDIUM in practice; the `>= 3`
threshold for COMPLEX essentially never fires on real prompts in this set. The LLM
classifier caught COMPLEX cleanly (0.89 precision, 1.00 recall).

**Where they disagree:** 66 of 108 prompts. LLM was correct in 47, rule-based in 16,
neither in 3 — when the two methods disagree, the LLM was right roughly 3x as often.

**LLM's actual error mode** (worth having ready for interviews): it over-predicts
MEDIUM for SIMPLE *definitional* questions -- "What is the CAP theorem?", "What's the
difference between authentication and authorization?" — 18 of its 19 errors are this
exact shape. Plausible read: definitional prompts share surface features with
"explain X" prompts (the classifier's MEDIUM anchor), even though the rubric treats
single-fact definitions as SIMPLE. This is a real, fixable-later prompt-engineering
gap in `LLMRouter.CLASSIFICATION_PROMPT`, not noise.

**Ablation cost:** classifying all 108 prompts through the LLM cost **$0.008 total**
— confirms the classifier design goal (classification must be far cheaper than the
tier spread it's choosing between) actually holds here.

### A real infra problem found and fixed mid-run, not anticipated

The first full run used a concurrency semaphore (5 concurrent calls) with no
awareness of actual API quota, and burst straight through Gemini's **free-tier limit
of 15 requests/minute** for `gemini-3.1-flash-lite` — confirmed by the 429 body
(`limit: 15 ... FreeTier`) — despite this project's paid tier being enabled. 52 of 108
prompts (48%) failed and were correctly excluded rather than silently scored (per the
fallback-flag fix from Phase 1), but that's too much data loss to report as a real
number. Replaced the semaphore with an actual rolling-window rate limiter
(`RateLimiter`, capped at 12 req/min) plus a rate-limit-aware backoff (25s specifically
on 429, vs. 2s for other transient errors, using the new `LLMRouter.last_error`
field). Second run: 0 failures, all 108 classified.

### Resolved: switched to Vertex AI (service account) auth

The open item above ("worth checking why paid tier isn't covering 3.x") turned out to
have a concrete cause and fix. The API key the project had been using was linked to a
**Vertex AI service account**, not a plain AI-Studio-only key — and Vertex AI is a
genuinely different auth path to the same underlying models, with its own billing and
quota system separate from the AI Studio free/paid tier gating.

Confirmed empirically with concurrent-burst tests, same models, same underlying
account, only the auth path different:

| model | via AI Studio API key | via Vertex AI (service account) |
|---|---|---|
| `gemini-3.1-flash-lite` | 16/20 succeeded (`FreeTier` 429s) | **20/20 succeeded** |
| `gemini-2.5-flash-lite` (control) | 20/20 succeeded | 20/20 succeeded |
| `gemini-2.5-pro` | 404 "deprecated for new users" | **10/10 succeeded** |

The `gemini-2.5-flash-lite` control matters: it proves the account/billing itself is
fine — it's specifically that Google hadn't finished extending paid-tier quota
coverage to the newest (3.x) model generation through the AI-Studio-key surface on
this project. Vertex AI had neither problem for any model tested, including the
Pro-tier model that had been 404'ing.

**Changes made:**
- [src/providers/gemini.py](src/providers/gemini.py) — `GeminiProvider` now branches
  on `settings.use_vertex_ai` (default `true`): Vertex AI via
  `google.oauth2.service_account.Credentials.from_service_account_file(...)`, or the
  AI Studio API key as an explicit fallback path (`use_vertex_ai=false`) for anyone
  re-running this project without a GCP service account.
- `TIER_COMPLEX_MODEL` restored to **`gemini-2.5-pro`** — the originally-intended,
  correct GA Pro-tier model, no longer needing the `gemini-3.5-flash` workaround from
  earlier in Phase 1. `BASELINE_MODEL` in `src/services/cost.py` restored to match.
  `gemini-3.5-flash` kept in the pricing table as a documented fallback for the
  API-key path.
- `pyproject.toml` — was missing `aiosqlite`, `sentence-transformers`, `google-auth`,
  and still listed the unused `asyncpg`; corrected so `pip install -e .` on a fresh
  clone actually reproduces this environment (it silently wouldn't have before).
- The downloaded service account JSON key lives at the repo root and is excluded via
  `.gitignore` (`project-*.json` and a few related patterns) — confirmed with
  `git check-ignore -v`, never staged.

**Does this invalidate the Phase 3 numbers reported above?** No — Phase 3 ran entirely
against `gemini-3.1-flash-lite` as the classifier model, which is the *same model
weights* regardless of which auth surface reaches it. The auth path affects
throughput and access, not the model's actual outputs. The 79.6%/50.9% accuracy
figures stand.

**Going forward:** Phase 4 (full generation across all three tiers) will run through
Vertex AI, which removes the need for the rate limiter's conservative 12 req/min pacing
— it can run at a much higher throughput now. The `RateLimiter` class stays in
`eval/eval_classification.py` regardless (good defensive engineering even with headroom
to spare), just won't be the bottleneck it was.

---

## Phase 4 — Regenerate Cost/Accuracy Tradeoff Numbers

**Status: complete.** [eval/eval_cost_tradeoff.py](eval/eval_cost_tradeoff.py) runs all
108 labeled prompts through the actual production pipeline
(`LLMRouter.classify` → `ProviderManager.generate`), plus — deliberately, not the
cheaper approximation — a real, separate baseline generation on `gemini-2.5-pro` for
every single prompt. `CostCalculator.estimate()` normally re-prices the routed
response's own token count under the baseline model, which is the right tradeoff for
a live request (no user should pay double latency just to compute a savings number),
but this is offline analysis with nothing waiting on it, so paying for a genuinely
separate generation (~$0.31 total across 108 baseline calls) produces an audited
number instead of an estimated one — the more defensible claim for a CV line.

### Headline numbers (108/108, one transient Vertex 429 retried and recovered)

| | total |
|---|---|
| Actual cost (routed) | $0.161 |
| Baseline cost (always `gemini-2.5-pro`) | $0.310 |
| **Savings** | **$0.149 (48.1%)** |

| true tier | n | savings % |
|---|---|---|
| simple | 59 | 67.1% |
| medium | 15 | 43.1% |
| complex | 34 | -4.7% (expected — see below, not a bug) |

The COMPLEX row reading near-zero/negative is correct, not an error: a correctly
routed COMPLEX prompt's actual model already *is* `gemini-2.5-pro` — the same model as
the baseline — so that row is two independent generations of the identical model on
the identical prompt (temperature 0.7), differing only by natural response-length
variance. Worth having this explanation ready, since the number looks alarming at a
glance.

### The safety result (the one worth leading with in an interview)

**Zero prompts were under-routed** — across all 108, not one COMPLEX-labeled prompt
was ever answered by a cheaper tier. The router's one job that actually matters
(never silently give a confidently-wrong cheap answer to a hard question) held
completely on this dataset.

**21/108 (19.4%) were over-routed** — sent to a pricier tier than their true label
warranted. This is money left on the table, not a quality risk, and it has a specific,
explainable shape: **18 of the 21 are the exact same failure mode Phase 3 already
found** — SIMPLE *definitional* questions ("What is the CAP theorem?", "What does
'eventual consistency' mean?", "What's the difference between authentication and
authorization?") getting bumped to MEDIUM. Phase 3 and Phase 4 are two independent
measurements (classification-only vs. full pipeline, different runs, some LLM
non-determinism between them) landing on the same specific error pattern — that
cross-validation is worth stating explicitly, since it turns "the classifier makes
mistakes" into "the classifier has one specific, identified, fixable gap."

### A real transient failure, handled correctly rather than papered over

One baseline call (`anal-015`) hit a transient Vertex 429 under concurrency=8 — Vertex
has much higher quota than the AI Studio free-tier path (Phase 3's problem), but not
infinite. The script's error handling excluded it from cost totals rather than
silently defaulting it to $0 or crashing the whole run; added a one-retry-with-backoff
path to the script for future runs, and patched this single missing data point with
one follow-up call rather than re-spending on the other 107 already-successful ones.
Final dataset: 108/108.

### Outputs

- [eval/results/cost_tradeoff_report.md](eval/results/cost_tradeoff_report.md) — full
  write-up: aggregate + per-tier cost table, every over-routed prompt listed with text
- [eval/results/cost_tradeoff_predictions.json](eval/results/cost_tradeoff_predictions.json)
  — raw per-prompt data (routed tier, actual tier, real token counts and cost on both
  sides, misroute classification)
- `eval/results/cost_by_tier.png` — actual vs. baseline cost, grouped by true tier

---

## Phase 5 — Semantic-Cache Threshold Validation

**Status: complete.** [eval/threshold_sweep.py](eval/threshold_sweep.py) embeds
the 54 hand-labeled pairs in [eval/cache_pairs.json](eval/cache_pairs.json) with
the production model (`sentence-transformers/all-MiniLM-L6-v2`, local, no API
calls, no Redis), sweeps the cosine-similarity threshold from 0.50→1.00, and
measures precision/recall against the `should_cache_hit` label. Outputs:
[eval/results/threshold_sweep_report.md](eval/results/threshold_sweep_report.md),
`threshold_sweep_pairs.json`, and two PNGs (`threshold_sweep_curve.png`,
`threshold_sweep_distribution.png`).

### The environment blocker, and how it ended

`import torch` hung on this machine for the entire prior session — a blocked
kernel wait (~0 CPU, full wall-clock), not slow computation. Diagnosed across
two sessions as a leaked OS-level named mutex left behind by an earlier
segfault in `SentenceTransformer.encode(list)`; `numpy` imported fine, so it was
specifically torch's native OpenMP runtime init. Killing the stuck holder
processes did **not** release it (confirmed by experiment this session) — only a
full machine reboot did. Post-reboot, `import torch` returned in ~2s and the
sweep ran in 19s. The lesson for anyone re-running this on Windows: if torch
suddenly hangs after a crash, reboot before anything else; process kills and
reinstalls won't help. The script's single-embed-at-a-time workaround in
`compute_similarities()` (vs. the faster batch path) was kept — it works
correctly either way at this dataset size and the batch path was the original
segfault trigger.

### Headline numbers (54 pairs: 22 should-cache-hit, 32 should-not)

| framing | threshold | precision | recall |
|---|---|---|---|
| Current default | 0.92 | **81.2%** | 59.1% |
| Best F0.5 (precision-weighted) | 0.82 | 79.2% | 86.4% |
| Most permissive at ≥97% precision | 1.00 | 100.0% | 9.1% |

### The finding (the one worth leading with)

**0.92 is riskier than it looks — it has 3 false positives on this dataset.**
Three `narrower_or_broader` trap pairs (same template, different correct answer)
scored *at or above* 0.92 and would be silently served from the cache:

- `trap-12` (sim **0.9936**): "Explain why a company might choose a direct
  listing over an IPO." vs. "...choose an IPO over a direct listing." — swapped
  preference; the cached answer argues the *opposite* of what was asked.
- `trap-09` (sim 0.9839): "Design a rate limiter for a single-region API with
  1,000 req/s." vs. "...multi-region API with 100,000 req/s." — same template,
  very different constraints and correct design.
- `trap-07` (sim 0.96): "Refunds issued within 5 business days." vs. "...30
  business days, no exceptions." — same template, different policy content.

This is the validation doing its job: a threshold "picked by eyeballing a couple
of examples" (which is how 0.92 got there) cannot tell lexical/structural
similarity from semantic *safety-to-cache*.

### Why there's no clean better number

The per-category similarity table is the real explanation:

| category | n | mean sim | min | max |
|---|---|---|---|---|
| exact_duplicate | 8 | 0.986 | 0.920 | 1.000 |
| paraphrase | 14 | 0.873 | 0.608 | 0.981 |
| narrower_or_broader (trap) | 12 | 0.815 | 0.608 | **0.994** |
| related_topic_different_ask | 12 | 0.391 | 0.087 | 0.646 |
| unrelated | 8 | 0.047 | -0.047 | 0.141 |

The trap category's *max* (0.994) sits **above the paraphrase mean** (0.873) and
inside the exact-duplicate range. There is no threshold that cleanly separates
"safe paraphrase" from "dangerous trap" — the distributions overlap at the top.
Raising the threshold toward 1.00 removes the false positives but collapses
recall (at 1.00, only exact duplicates are caught: 9.1% recall), which strips
out the entire *semantic* value of the cache and leaves it as an exact-match
cache. Lowering it (0.82, the F0.5 optimum) buys recall but adds more false
positives. The tension is fundamental to this embedding model on this failure
mode, not a tuning error.

### Recommendation carried into the project

The hardcoded `0.92` is **not defensible as-is** given the rubric's
precision-priority framing (a false-positive cache hit silently serves a wrong
answer — strictly worse than a miss). The defensible options, in order of how
much I'd want to defend them in an interview:

1. **Acknowledge the limitation and gate it.** Keep a similarity threshold for
   caching but add a guard for the specific high-similarity-trap shape
   (template-difference detection, or a cheap second-stage check on
   numerals/named entities / swapped operands), since those three FPs share an
   exact shape: the *only* difference is a swapped or substituted token. This is
   the real fix; it's out of scope for this phase but is the concrete next step
   the validation surfaced.
2. **Upgrade the embedding model.** `all-MiniLM-L6-v2` is a 384-dim/light model;
   a stronger encoder (e.g. `all-mpnet-base-v2`) may separate the trap pairs
   from paraphrases better. Worth re-running this sweep against it before
   committing.
3. **Raise the threshold toward 1.00** to eliminate FPs — but accept that this
   reduces the cache to near-exact-match and loses most of its value.

The production default in `src/config.py` (`semantic_similarity_threshold`) is
left at 0.92 for now, with this finding documented — changing it is a product
decision (accept-risk vs. safe-but-low-recall vs. invest in option 1/2), not a
mechanical fix, so it's flagged for the user rather than silently changed.

### Outputs

- [eval/results/threshold_sweep_report.md](eval/results/threshold_sweep_report.md)
  — full write-up: default-position analysis, the 3 FP pairs with text,
  recommendations, full sweep table, per-category similarity table.
- [eval/results/threshold_sweep_pairs.json](eval/results/threshold_sweep_pairs.json)
  — every pair with its measured similarity.
- `eval/results/threshold_sweep_curve.png` — precision/recall/F0.5 vs threshold.
- `eval/results/threshold_sweep_distribution.png` — similarity scores by
  category, showing the trap/paraphrase overlap visually.

---

## Phases 6-7

Phase 6 (stretch: live eval endpoint or multi-turn re-routing demo) — not
started; explicitly optional per the plan.

Phase 7 (write-up): rewrite `README.md`'s opening to credit
`Asirwad/smart-llm-router` as the base architecture, list the four extensions
(labeled eval harness, classifier-accuracy comparison, cost/accuracy tradeoff
with misroute detection, cache-threshold validation), link the original repo,
then push to the user's own clean repo. All four extensions now have results;
the three interview talking points are: (1) classifier accuracy + the
all-zero-COMPLEX-column confusion matrix from Phase 3, (2) zero under-routes /
the one specific over-route failure mode from Phase 4, (3) the 0.92-has-false-
positives finding + the trap/paraphrase overlap from Phase 5.

---

## Open items to revisit

- **Pro-tier quota** — resolved in Phase 3 (Vertex AI service-account auth restored
  `gemini-2.5-pro` access; `TIER_COMPLEX_MODEL` already set to it). Only revisit if
  switching back to the AI-Studio API-key path.
- **Cache threshold (from Phase 5)** — `0.92` is not defensible as-is (3 false
  positives on the 54-pair set; trap/paraphrase distributions overlap at the top, so
  no clean better number exists for this embedding model). Production default left at
  0.92 with the finding documented. Real fix is either a template-difference guard for
  the swapped-token trap shape, a stronger embedding model (`all-mpnet-base-v2`),
  or raising toward 1.00 (accepts near-exact-match-only recall). A product decision,
  not a mechanical change.
- **Redis Stack** — deferred; Phase 5's threshold sweep doesn't need it, but a live
  cache-hit demo (Phase 6 stretch) would.
- **Pricing table currency** — `MODEL_PRICING` in `src/services/cost.py` was checked
  live against `ai.google.dev/gemini-api/docs/pricing` on 2026-08-15. `gemini-3.6-flash`
  carries promotional pricing that roughly doubles on 2027-01-01 — re-check before
  quoting savings numbers if this project is revisited after that date.
