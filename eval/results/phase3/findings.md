## Findings

**Strong per category (dev, n=30 per cell, so CIs are wide).**
- **API tier is near the ceiling.** deepseek-v4p1-flash and kimi-k3p1-pro tie at 99% overall; gpt-oss-120b and gemini-3.1-flash-lite are at 97%. Math, sentiment, code debugging and code generation are 97-100% for almost every API model, so the API models barely separate there. The tie at the top means B1 (D2: ties go to the cheaper) will be deepseek-v4p1-flash at about $0.00034 per task vs kimi at $0.00184; `pick_baselines.py` decides, not this report.
- **Summarisation is the one category where API models differ** (63% nemotron/minimax, 77% glm, 80% gpt-oss, 83% gemini, 93% deepseek, 97% kimi). It is also the weakest category for every local model (13-63%).
- **Logic and NER separate the local models.** Logic: all eight local models are 33-53%, even gemma3:4b (43%) that is otherwise strong; the 14B server tier reaches 63-77%; API models 87-100%. NER: gemma3:4b 90%, qwen3:1.7b 67%, llama3.2:3b/phi3.5 50% mostly from ignoring the JSON-only instruction.
- **Local models that already clear 90% on a category (dev point estimates, not yet a policy):** gemma3:4b on math (100%), sentiment (100%), code debugging (93%), NER (90%), code generation (90%) and factual (90%); phi3.5:3.8b on math (100%); qwen3:1.7b on math and sentiment (90%); llama3.2:3b on sentiment (97%). Phase 4 applies the D4 test to these; the lower CI bound is ~74-89% for n=30.
- **Local Pareto front (accuracy vs CPU median latency):** granite4:350m (47%, 3.1 s), qwen3:1.7b (69%, 7.2 s), llama3.2:3b (76%, 15.8 s), gemma3:4b (82%, 22.4 s). phi3.5:3.8b is dominated (72% at 29 s), as are gemma3:1b, qwen2.5-coder:1.5b and llama3.2:1b.
- **GPU-server tier** (gemma3:12b 86%, qwen2.5:14b 88%, phi4:14b 90%) beats every 1-4B local model except by a few points over gemma3:4b (82%), but at 5-7 s per answer on a T4 pair; it does not reach the API tier's accuracy.

**Surprises.**
- The easy/hard label barely separates API models (e.g. kimi 99%/99%, deepseek 98%/99%); it does separate the local models (gemma3:4b 86% vs 78%, qwen3 74% vs 63%). Per-cell n is 15, so D9's difficulty routing will mostly matter for local models.
- qwen2.5-coder:1.5b (code specialist) is the best 1-2B model at code debugging (80%) but only ties the generalists at code generation (63%, vs gemma3:1b 67%, llama3.2:1b 70%), and is the worst at summarisation (13%) and logic (33%).
- qwen3:1.7b (thinking off) is the best small model on math (90%) but its Kaggle re-run was only 138/240 identical to the Phase 2 dry run, while gemma3:1b was 240/240 identical: qwen3 is not fully deterministic at temperature 0 here.
- At low effort, nemotron-lightning spends ~940 reasoning tokens per answer on average (10x the others) and 11 answers ran out of its token budget with an empty or partial reply; 4 of its 11 summarisation failures are empty replies from these runaways (the rest are judge verdicts or limit breaks). minimax had one similar runaway (code_gen-001).
- Gemini's p95 latency is 22.9 s (median 2.3 s) because of the free-tier throttle and retries in the runner; do not read it as model latency.

**Grader artefacts and fixes (recorded; all models re-graded after the change so they stay comparable).**
1. *Language check false positives (fixed).* The D10 check failed correct technical answers because of letter-like symbols (micro sign in "µm", ℏ, ᵀ, superscript ⁿᵗ): 4 API answers (minimax x2, hyde/glm, kimi), all factual. The check now flags only real non-English scripts; genuine leaks still fail (qwen3:1.7b "镑", two qwen2.5:14b answers that drift into Chinese). Test added in `eval/graders/test_language.py`.
2. *Unparsed answers (left strict, no extractor change).* NER answers that are bullet lists or single objects instead of the requested JSON list (granite 24, llama3.2:1b 28, llama3.2:3b 5, qwen2.5-coder 2, phi3.5 13) fail as instruction violations: a router would reject them. Only 5 phi3.5 answers have a valid JSON list followed by extra text, so a lenient parser would change them; not done, to stay consistent with the Phase 2 rule that prose around the JSON fails. granite4:350m code_debug (4) has no code, only a description: genuine failure.
3. *Summaries.* Most summary failures are definite constraint breaks (word/sentence/bullet limits: minimax 8 of 11, gpt-oss 4 of 6) rather than judge verdicts; judge verdicts dominate for glm, gemini, kimi and deepseek.
4. *Call errors.* phi3.5:3.8b returned HTTP 500 on 3 logic prompts (logic-021, -047, -048); counted as failures, not re-run. 24 phi3.5 answers hit the token limit.

**Caveats to say out loud.** API models ran at low reasoning effort (D11), so the API ceiling is "as deployed cheaply"; one run per model at temperature 0; the 40-task CPU sample (5 per category) makes CPU p95 noisy; local accuracy is measured on a Kaggle T4, CPU timing on Kaggle CPUs (2 threads), not on Kabir's laptop; cost rates for the "with hardware" view ($0.05/h CPU, $0.35/h T4) are assumptions, not quotes.

## Spend (Phase 3)

| provider | what | USD |
|---|---|---|
| Fireworks | 6 API models, 240 dev tasks each (+16-task smoke, included) | 0.771 |
| Fireworks | Qwen judge calls for GLM answers during Phase 3 grading | 0.349 |
| **Fireworks total** | cap $5.00 | **1.12** |
| Hyde GLM | free to us; list-price equivalent | 0.014 (list) |
| Gemini AI Studio | free tier; list-price equivalent | 0.105 (list) |
