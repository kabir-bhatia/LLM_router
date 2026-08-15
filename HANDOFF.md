# Handoff — Smart LLM Router extension project

Read this first. `PROJECT_LOG.md` has the full detailed history of every phase;
this file is the fast-orientation summary plus the one thing actively blocking
progress right now.

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

## The one thing blocking you right now

`import sentence_transformers` (which pulls in `torch`) hangs indefinitely on
this machine — **not slow, actually stuck**: confirmed via `time timeout 60
python -c "import sentence_transformers"` showing 60s wall-clock but only
**0.07s of actual CPU time**. That signature (long wall time, near-zero CPU)
means the process is blocked waiting on something external, not computing.

Ruled out, in this order, each with real evidence:
1. **Low RAM** — machine has 16GB total; was down to ~3GB free, user freed it
   back up to ~6.3GB free. Still hung identically. Not (purely) this.
2. **Antivirus scanning torch's large DLLs** — added a Windows Defender
   exclusion for `D:\LLM_Router\.venv`. Still hung identically. Not this either.

**Confirmed this session (not a theory anymore), by direct experiment:**

1. **It's `torch`, not `sentence_transformers`.** `import torch` hangs with
   the same blocked-wait signature (30s wall, ~0.015s CPU — blocked on an
   external wait, not computing); `import numpy` returns instantly. So the
   hang is in torch's native C++/OpenMP runtime init, not the Python layer on
   top. `torch 2.13.0` is installed in the venv (verified via `pip show`).

2. **Killing the stuck holder processes does NOT release it.** There were 5
   orphaned `python.exe` processes at ~102MB working set each (torch's DLLs
   loaded partway, then blocked on the named mutex — `timeout` can't reap a
   process blocked inside a native DLL, so my repeated import tests had piled
   them up). I killed all 5 specifically (working-set > 50MB, unmistakably
   torch-loaded zombies, not harmless stubs). `import torch` **still hung
   identically afterward.** That rules out "a live zombie is holding the
   mutex" and confirms it's a *truly leaked* kernel named object (or torch's
   OpenMP runtime deadlocking on its own internal state) — i.e. the handoff's
   original "only a reboot releases it" conclusion holds, now backed by
   evidence rather than assumption.

3. **Implication for the secondary fix:** `pip install --force-reinstall
   torch --no-cache-dir` is a *long shot*. The signature is a blocked kernel
   wait, not a DLL load error — a corrupted DLL would error or crash, not
   block silently with ~0 CPU. Replacing the DLLs won't change the leaked
   kernel-object state. Don't burn the ~2GB download unless a clean reboot
   *also* fails to fix it (which would point to a genuinely different cause).

### Immediate next step

**The user has already been told to fully restart the machine** (this
session's background job ends at reboot, so the next session picks this up).
After a clean reboot, verify torch imports. Use bash for this — a PowerShell
`Start-Process ... -c` call mangled the quoting into a syntax error when I
tried it, but `bash`'s `timeout` around a `-c` one-liner is reliable:

```bash
cd /d/LLM_Router
time timeout 30 .venv/Scripts/python.exe -c "import torch; print('torch ok', torch.__version__)"
```

Expect `torch ok 2.13.0` in a few seconds. (It did, reliably, earlier in the
project before the segfaults broke the environment.)

Once that prints, Phase 5 is a one-command finish — **the script and data are
verified ready, no code changes needed** (read this session: `eval/threshold_sweep.py`
is complete and correct — F0.5 precision-weighting, a 97%-precision-floor
strategy, a per-category sanity check; `eval/cache_pairs.json` is 54
well-labeled pairs with the crucial `narrower_or_broader` trap category):

```bash
cd /d/LLM_Router
.venv/Scripts/python.exe -m eval.threshold_sweep
```

Pure local computation (no API calls, no Redis), runs in well under a minute
once imports work. Outputs `eval/results/threshold_sweep_report.md` +
`threshold_sweep_pairs.json` + two PNGs. Read the script's own docstring for
the full picture; short version: embeds 54 hand-labeled prompt pairs with the
production embedding model, sweeps the cache-similarity threshold, reports
precision/recall, and recommends whether 0.92 should change.

**One thing to check once it runs**: `eval/threshold_sweep.py`'s
`compute_similarities()` currently embeds one prompt at a time via
`embed_sync` in a loop (see the docstring on that function) — this was a
workaround for the *original* batch-encode segfault, made **before** the
Defender/RAM investigation ruled those out as the root cause of the *later*
hang. It's possible the single-embed workaround is unnecessary now and the
batch path (`embed_batch_sync`, faster) works fine post-reboot. Not urgent to
change — the current code works correctly either way, just marginally slower
for ~100 prompts (a few seconds either way) — but worth knowing it's there
and why.

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
