# Handoff — Smart LLM Router extension project

Read this first. `PROJECT_LOG.md` has the full detailed history of every phase;
this file is the fast-orientation summary. Nothing is blocking progress as of
2026-11-19; the next work is Phase 6 (optional) and Phase 7.

## Status at a glance

| Phase | Status |
|---|---|
| 1 — Setup (SQLite, Vertex AI auth, local embeddings, all 3 Gemini tiers wired) | ✅ Done, verified end-to-end |
| 2 — Labeled eval dataset (108 prompts) | ✅ Done — `eval/labeled_prompts.json` |
| 3 — Classifier accuracy (LLM vs rule-based) | ✅ Done — `eval/results/classification_report.md` |
| 4 — Cost/accuracy tradeoff (real dual generation) | ✅ Done — `eval/results/cost_tradeoff_report.md` |
| 5 — Semantic-cache threshold validation | ✅ Done — `eval/results/threshold_sweep_report.md` (finding: 0.92 has 3 FPs) |
| 6 — Stretch (live eval endpoint / multi-turn demo) | Not started |
| 7 — Write-up & positioning (README rewrite, CV line, push to own repo) | Not started |

## Torch import hang -- RESOLVED (2026-11-19)

The `import torch` / `import sentence_transformers` hang described below is
gone. After a restart, `import torch` returns in ~3.8s (`torch ok 2.13.0+cpu`),
which supports the leaked-kernel-object theory: killing processes, freeing RAM
and the Defender exclusion did not fix it, and only a restart did.

Phase 5 was re-run on the healthy environment with
`.venv/Scripts/python.exe -m eval.threshold_sweep`. Output matches the
committed results exactly (`git diff eval/results/` is empty), so the result
is deterministic and reproducible.

**If it ever comes back:** restart the machine. Don't reinstall torch.

The history below is kept for context only.

## What actually happened (for context on the above)

1. Wrote `eval/cache_pairs.json` (54 labeled pairs) and `eval/threshold_sweep.py`.
2. First run: **segfault**, zero output, immediately.
3. Isolated it to `SentenceTransformer.encode(list_of_strings)` specifically —
   single-string `encode()` worked fine repeatedly; the batch/list path
   segfaulted or hung non-deterministically.
4. Rewrote `compute_similarities()` to embed one prompt at a time instead
   (see the function's docstring in `eval/threshold_sweep.py`) — this exact
   pattern had been reliable all session for single calls.
5. Re-ran: this time **hung** (not crashed) on the very first single embed
   call, which had never failed before. Investigated system state:
   - `tasklist`/WMI-based diagnostics themselves started timing out (bad sign)
   - `Get-Process` (lighter, non-WMI) worked: ~12GB total process working set,
     Windows "Memory Compression" active at 1GB (real memory pressure)
   - `[Microsoft.VisualBasic.Devices.ComputerInfo]` (avoids WMI entirely):
     16GB total RAM, ~3GB free at the low point
6. User freed memory (apps closed) → ~6.3GB free. Retried. Still hung.
7. Diagnosed via `time timeout N python -c "import sentence_transformers"`:
   wall time >> CPU time every time → genuinely blocked, not slow.
8. User added a Windows Defender exclusion for `.venv`. Retried. Still hung,
   identical signature.
9. Ran out of time in this session; wrote this handoff instead of continuing
   to guess blind.

## Key files map

```
src/
  config.py              -- Settings (Vertex AI + API key auth, tier models, etc.)
  core/router.py          -- RuleBasedRouter, LLMRouter, DifficultyTier
  providers/gemini.py      -- GeminiProvider (Vertex AI service account OR API key)
  providers/manager.py    -- ProviderManager (tier routing, retry, fallback escalation)
  services/cost.py        -- CostCalculator, MODEL_PRICING table (recheck before quoting numbers!)
  services/embeddings.py  -- local sentence-transformers embeddings (see caveats above)
  services/semantic_cache.py -- Redis-backed cache, degrades to no-op if Redis unavailable
  db/                     -- SQLite models/session (swapped from upstream's Postgres)

eval/
  LABELING_RUBRIC.md       -- how Phase 2 tiers were assigned (read this to understand true_tier)
  candidate_prompts.json   -- 108 unlabeled prompts (Phase 2 source)
  labeled_prompts.json     -- 108 labeled prompts (Phase 2 output, used by Phases 3-4)
  cache_pairs.json         -- 54 labeled pairs for Phase 5 (written, not yet run)
  eval_classification.py   -- Phase 3 script (done, ran successfully)
  eval_cost_tradeoff.py    -- Phase 4 script (done, ran successfully)
  threshold_sweep.py       -- Phase 5 script (written, BLOCKED on the issue above)
  results/                 -- all phase outputs: reports (.md), raw predictions (.json), charts (.png)

scripts/
  verify_setup.py          -- Phase 1 end-to-end check, run via `python -m scripts.verify_setup`
  apply_phase2_labels.py   -- one-off script that produced labeled_prompts.json (reference only)

PROJECT_LOG.md             -- full detailed history, read this for the "why" behind every decision
.env                        -- gitignored, has the real Vertex AI service account path + API key
project-0bfd279e-....json   -- Vertex AI service account key, gitignored, DO NOT commit
```

## Config / environment notes for the next agent

- **Auth**: `USE_VERTEX_AI=true` in `.env` (recommended, default) — uses the
  service account JSON at the repo root. Confirmed empirically to have full
  paid-tier throughput and no rate limiting, unlike the AI Studio API key
  path (see `PROJECT_LOG.md` Phase 3/4 for the full investigation — TL;DR:
  the API key throttled the 3.x Gemini model family to free-tier limits on
  this project despite paid tier being enabled; Vertex AI didn't have that
  problem).
- **Tiers**: SIMPLE=`gemini-3.1-flash-lite`, MEDIUM=`gemini-3.6-flash`,
  COMPLEX=`gemini-2.5-pro`. All GA (non-preview) models as of Aug 2026.
- **Venv**: must be created with `py -3.13` explicitly, NOT bare `py` (which
  defaults to the experimental free-threaded 3.13t build with no numpy/torch
  wheels — see `PROJECT_LOG.md` Phase 1 for the full story).
- **Redis**: off by default (`ENABLE_REDIS_CACHE=false`). Not needed for any
  phase including 5 (pure local computation).
- **Tests**: `.venv/Scripts/python.exe -m pytest -q` — was 37 passed, 1
  skipped (Redis-dependent test) as of the last successful run before this
  session's environment issues. Should still pass once the environment is
  healthy again; hasn't been re-verified since the segfaults started, since
  pytest doesn't touch sentence-transformers directly in most tests but
  `test_integration.py` does exercise the semantic cache path.
- **Pricing table**: `src/services/cost.py` `MODEL_PRICING` — was checked
  live against `ai.google.dev/gemini-api/docs/pricing` on 2026-08-15. Note
  `gemini-3.6-flash` carries promotional pricing expiring 2026-12-31.

## Remaining work

**Phase 5: done this session.** Ran `eval.threshold_sweep` after a reboot
unblocked `import torch`. Finding: the hardcoded `0.92` has **3 false
positives** on the 54-pair set (trap pairs scoring 0.96–0.99 — e.g. "direct
listing over an IPO" vs "an IPO over a direct listing" at sim 0.9936), and no
threshold below 1.00 reaches 97% precision. The trap and paraphrase similarity
distributions overlap at the top, so there's no clean better number — documented
in `PROJECT_LOG.md` Phase 5 with three defensible options (template-difference
guard / stronger embedding model / raise-to-1.00). The production default is
left at 0.92 with the finding flagged, since changing it is a product decision,
not a mechanical fix.

**Phase 6 (stretch, optional)**: either expose eval results as a live API
endpoint for interactive demo, or add a short multi-turn conversation example
showing per-turn re-routing. Keep small; the plan explicitly says prefer
"small and working" over "ambitious and broken" here.

**Phase 7 (write-up)**: rewrite `README.md`'s opening to credit
`Asirwad/smart-llm-router` as the base architecture, list the four concrete
extensions (labeled eval harness, classifier accuracy comparison, cost/accuracy
tradeoff analysis with misroute detection, cache threshold validation), link
the original repo, then push to the user's own clean repo. The CV line and
three interview talking points are already drafted in the user's original
plan message (start of this conversation) — all three now have their specific
numbers/findings: (1) classifier accuracy + the all-zero-COMPLEX-column
confusion matrix from Phase 3, (2) zero under-routes / the one specific
over-route failure mode from Phase 4, (3) the 0.92-has-false-positives finding
+ the trap/paraphrase overlap from Phase 5.

## One outstanding user-facing caveat to carry forward

Per `eval/README.md` and `PROJECT_LOG.md`: the Phase 2 labels and (per this
session's established pattern) the Phase 5 pair labels were drafted by
Claude at the user's explicit direction, not hand-labeled by the user
prompt-by-prompt. Both files carry `note` fields explaining the reasoning
specifically so they can be reviewed and defended. **The user should read
through both label sets before treating this as their own hand-labeled work**
for CV/interview purposes — this was stated directly to them earlier in the
session and is worth restating if it comes up again.
