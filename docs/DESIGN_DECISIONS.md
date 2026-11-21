# Design decisions

Running log of the choices that shape the results, and the reason for each, so every one can be
defended in an interview. Status: **agreed** = confirmed by Kabir. All decisions below were agreed on 2026-11-20.
Last updated 2026-11-20.

---

## D1. The 16 models (agreed)

**Selection rules, written before benchmarking:**
- **Local (8):** fit in 4 GB VRAM at 4-bit, at least 5 families, at most 2 models per family, spread across 3 size groups, and include specialists (code, math/reasoning).
- **Paid API (8):** at least 6 model makers, three price groups (budget ≤ $0.60, mid ≤ $1.50, premium > $4 per 1M output tokens), served by an official provider, and **not the judge model**.

### Local: 8 models, 5 families

| Size | Model | Family | Why it's in the set |
|---|---|---|---|
| tiny | granite4:350m | IBM | smallest viable; the upstream project's original local model |
| tiny | gemma3:1b | Google | strong instruction-following for its size |
| tiny | llama3.2:1b | Meta | the most widely deployed small model family |
| small | qwen3:1.7b | Alibaba | newest-generation reasoning in a small model |
| small | qwen2.5-coder:1.5b | Alibaba | code specialist: tests whether specialisation beats size on code |
| mid | llama3.2:3b | Meta | same family as the 1b: shows what tripling size buys |
| mid | phi3.5:3.8b | Microsoft | trained heavily on reasoning/math data |
| mid | gemma3:4b | Google | best all-rounder in the smoke test (4/4) |

Dropped after the smoke test: qwen3:4b (never finishes an answer with thinking on; 105 s per answer on CPU) and qwen2.5:0.5b/1.5b (to keep Alibaba at 2).
granite4:350m, gemma3:1b and llama3.2:1b weren't in the smoke test, so they get one quick Kaggle run before the benchmark.

### Paid API: 8 models, 7 makers

| Price group | Model | Maker | $ in / out per 1M | Runs on |
|---|---|---|---|---|
| budget | nemotron-lightning-3p5-30b-a3b | NVIDIA | 0.05 / 0.20 | Fireworks |
| budget | glm-5.3-flash | Zhipu | 0.15 / 0.50 (market price) | Hyde (free to us) |
| budget | gpt-oss-120b | OpenAI (open weights) | 0.15 / 0.60 | Fireworks |
| budget | minimax-m3p1-flash | MiniMax | 0.15 / 0.60 | Fireworks |
| mid | deepseek-v4p1-flash | DeepSeek | 0.30 / 1.20 | Fireworks |
| mid | gemini-3.1-flash-lite | Google | 0.25 / 1.50 | AI Studio |
| premium | glm-5p3 | Zhipu | 1.40 / 4.40 | Fireworks |
| premium | kimi-k3p1-pro | Moonshot | 2.00 / 10.00 | Fireworks |

The two GLM models are deliberately a pair: same maker, flash vs full, which shows what the premium tier buys.
All costs in the analysis use the list price in `eval/model_prices.json`, whoever actually served the call.

**Optional extended tier (Kaggle allowing):** 2–3 bigger open models on the T4×2 GPUs
(e.g. gemma3:12b, phi4:14b, qwen2.5:14b) as a "self-hosted GPU server" tier, priced at cloud GPU
rates. These are not part of the 16. They answer "what if the company runs a GPU box?"

## D2. Two baselines, chosen by the data (agreed)

| | Definition | How it's chosen |
|---|---|---|
| **B1: Best single model** | Every task goes to the most accurate API model | Highest overall dev accuracy among the 8 API models; ties go to the cheaper one |
| **B2: Cheapest sufficient model** | Every task goes to the cheapest API model that is "good enough" | Cheapest API model whose overall dev accuracy is not worse than B1 by more than the D4 margin |

**Execution:**
1. Phase 3 (benchmark on dev) gives every API model's accuracy and cost per category.
2. A script (`eval/pick_baselines.py`) applies the two rules above and writes `baselines.json`, with the numbers behind each choice. Nothing is chosen by hand.
3. Phase 6 runs **router, B1 and B2 on the same held-out test tasks**, 3 runs each, graded by the same graders.
4. Report: accuracy and cost of all three, and savings of the router vs B1 and vs B2.

The headline claim is savings vs B1 at equal accuracy. B2 is the tougher comparison and is reported next to it.

## D3. Statistics on every number (agreed)

- 50 tasks per category (400 total), split 60% dev / 40% test.
- Every accuracy number has a 95% confidence interval (Wilson interval).
- Final results are the mean ± spread over 3 runs.

## D4. When a category may go to a cheaper path (agreed)

A cheaper path (solver, local model, or cheaper API model) gets a category only if:
- **No-worse test:** on the same dev tasks, a paired bootstrap shows its accuracy is at most 5 percentage points below B1, with 95% confidence.
- **Floor:** its accuracy is at least 80%.

Otherwise the category goes to the next path up.

## D5. Cost reporting (agreed)

Savings are reported two ways:
1. **Marginal:** local inference costs $0, since the hardware is already paid for.
2. **With hardware:** local requests are priced at measured latency × the hourly rate of the smallest cloud machine that runs them (CPU instance for ≤4 GB models; T4 GPU instance for the extended tier).

## D6. Traffic mix (agreed)

- (a) Savings and accuracy are reported **per category**.
- (b) The overall number is recomputed for 3–4 scenario mixes: equal shares, "support desk" (sentiment, summaries, NER, factual), "developer tools" (code-heavy), "analyst" (math, logic, factual). The range is reported.
- (c) Bonus if time allows: estimate a real-world mix by running the task-type classifier over a sample of public user prompts (e.g. WildChat), after checking the dataset licence.

## D7. Solvers tested on phrasings they never saw (agreed)

Math and logic test items use templates written separately from the ones used while building the
solvers, plus hand-written items. Solver results report **coverage** (share of tasks it answered)
and **precision** (share of its answers that were right).

## D8. Judge (agreed)

- **Default:** GLM 5.3 Flash via Hyde (free) grades blind, pass/fail against the reference answer, for factual and summary answers. GLM's own answers are graded by qwen3p8-max instead, so no model grades itself.
- **Judge check in Phase 2, before the benchmark is graded:** ~40 answers (mixed models, both categories) are graded by **both** GLM and qwen3p8-max (Qwen cost ≈ $0.10) and by Kabir by hand. Agreement with the hand labels is reported overall and split by the answering model's family.
- **Decision rule:** keep GLM if its agreement is ≥ 90% and no worse than Qwen's by more than 5 points; otherwise Qwen judges everything (≈ $3.4–5 extra).
- **Timing:** the judge is fixed before the routing policy is frozen and before the test split is opened. Every model answer is saved to disk, so switching judges only re-grades saved answers; no model is re-run.

## D9. Difficulty within a category (agreed)

Each category's tasks carry a difficulty label (easy / hard). Routing is decided per
**(category × difficulty)** cell, with the difficulty estimated at run time by a cheap local
classifier. A cell with too few dev tasks falls back to the category-level decision. Prompts that
fit none of the 8 categories, or are far bigger than the dataset's tasks (e.g. "build a whole
website"), go to an **out-of-scope route**: straight to B1.

**Update (agreed 2026-11-21):** the out-of-scope route goes to **B2** (the cheapest model that passed the 3-point test vs B1), not B1.

## D10. Grading rule for summaries and a language check (agreed 2026-11-20)

Decided during the Phase 2 judge check, on dev/calibration answers only, before any benchmark grading.

**Summaries: "faithful and keeps the core".** Each summary task has 2 **core** facts (the headline and its
main "but"/consequence) and its other facts are **secondary**. An answer PASSES only if all of these hold:
1. **Both core facts are present.** A headline number counts as core only when the story *is* that number.
2. **Nothing is wrong:** no statement contradicts the source, no invented fact or invented cause, and no reversed relationship (e.g. "growers worry about jobs" when the text says growers are short of workers).
3. Missing secondary facts or numbers never fails.

**Tolerated (not errors):** dropping a qualifier while keeping the claim's direction (e.g. "remote workers were
less likely to be promoted" for "juniors remote 4+ days were"), and wording a non-expert explanation would use.

**Not tolerated:** contradiction, invention, reversal, a one-sided summary that leaves out the story's main
downside when that downside is a core fact.

**Factual answers stay strict:** every required point present, nothing wrong. One clarification:
simplifications that standard popular-science explanations use are fine ("greenhouse gases trap the sun's
heat"); statements a textbook calls wrong are not ("observing a particle disturbs it" as the meaning of the
uncertainty principle).

**Language check (all 8 categories, code, not the judge):** an answer containing non-English script
(e.g. CJK characters) FAILS regardless of content. The judge grades facts; code grades format and language.

Why: the strict all-facts rule failed fluent, faithful summaries for missing minor details, which no reader
would mind. False statements remain the failure that matters, because a reader trusts a summary that is
quietly wrong.

## D11. Phase 3 benchmark settings (agreed 2026-11-20)

- **Models:** the 16 in D1, plus the optional "own GPU server" tier (gemma3:12b, phi4:14b, qwen2.5:14b) reported separately, outside the 16.
- **Runs:** one run per model on the 240 dev tasks, temperature 0 where supported. Repeats are kept for Phase 6.
- **Local models:** accuracy on Kaggle GPU (Ollama, Q4); CPU speed (2 threads, no GPU) on a fixed 40-task sample (5 per category). qwen3:1.7b with thinking off.
- **Paid API models: low reasoning effort for all**, the same setting the router uses in production. Reasoning tokens are billed and logged.
  - Known caveat, to state openly: low effort can lower the paid models' accuracy on hard reasoning tasks, so B1 is "the best model as it would be deployed cheaply", not each model at full strength. This makes the local-vs-B1 comparison somewhat easier to pass. If asked: production would run at this setting, so that's the fair comparison for this router; the default-effort comparison is listed as future work.
- **Budget:** hard cap $5 on Fireworks for Phase 3. Gemini runs on the free AI Studio tier, throttled to its rate limit ($0 actual, list price in the analysis). GLM via Hyde is free (market price in the analysis).

## D12. Two-level routing rule (agreed 2026-11-20, replaces the per-cell test in D4)

Decided after the Phase 4 power analysis (`eval/results/phase4/power_analysis.md`) and **before any Phase 3
accuracy was looked at**. At 15 dev tasks per cell, the D4 paired-bootstrap test rejected even an
equally good model 25–70% of the time, so routing would have depended on luck.

1. **Cell rule (category × difficulty, 15 dev tasks):** the cheapest option takes the cell if it has
   **at most one more miss than B1 in that cell** and **accuracy ≥ 80%**. Plain counts, no resampling.
   If a cell has fewer than 10 tasks, the category-level decision is used instead.
2. **Whole-router guardrail (all 240 dev tasks):** replay the full cascade (solver → local + validators →
   API) on every dev task. The router must be **at most 3 points less accurate than B1 at 95% confidence**
   (paired bootstrap, one-sided). If it fails, cells are handed back to the next option up, largest
   accuracy loss first, until it passes.
3. **B2** (D2) uses the same 240-task test: the cheapest single API model at most 3 points worse than B1 at
   95% confidence.

Interview line: per-cell choices are point estimates because 15 tasks can't support a significance test;
the statistical guarantee is on the whole router, where 240 tasks can.

Guardrail replay uses the classifiers' out-of-fold predicted labels (agreed 2026-11-21); GPU-server tier excluded from the main policy, reported as a separate scenario.

Escalation target = B2 (agreed 2026-11-21): when a validator rejects a local answer, or a prompt is out of scope, the request goes to B2, the cheapest model that passed the 3-point test vs B1. B1 remains the reference for the guardrail and the top of each cell's ladder, so a cell can still be handed back to B1 (e.g. `summarisation|hard`). Reason: with escalation to B1 the router cost more than always-B2.

## D13. LLM-assisted solvers (agreed 2026-11-20)

The pure-Python parsers answered 100% of template set A (built on) but 0% of unseen set-B/hand items
(precision 100%, coverage 0%). New design: **the local model translates, Python solves.**
- Math: the local model turns the word problem into a single arithmetic expression; Python evaluates it
  with the safe AST evaluator.
- Logic: the local model turns the puzzle into JSON (entities, attributes, constraints, question); Python
  brute-forces all assignments and answers **only if exactly one satisfies every constraint**.
- Self-gating stays: unparseable output, an invalid expression, zero or several solutions → defer to the
  next layer.
- D7 still applies: translation prompts and parsing are developed on dev set A only; coverage and precision
  are reported on unseen dev set B + hand items.
- The old pure-Python parsers stay as a zero-cost first try; the LLM-assisted path runs when they defer.
