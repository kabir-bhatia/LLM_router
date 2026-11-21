# Kaggle smoke test v2: new local models + bigger GPU-tier models

Run 2026-11-20 on Kaggle T4×2 with `notebooks/local_bench_kaggle_v2.ipynb`, same 8 smoke prompts as v1
(`prompts.json`). Raw data: `results_v2_gpu.json`, `results_v2_cpu.json`, `results_v2_gpu_large.json`.

As in v1, this is a load-and-speed check, not an accuracy benchmark: one prompt per category.

## Did every model run?

Yes: 88/88 calls returned with no errors (7 models on GPU, 4 of them also CPU-only).

## Speed

| Model | Tier | GPU tok/s | GPU median latency | Median output tokens | CPU (2 threads) tok/s | CPU median latency |
|---|---|---|---|---|---|---|
| granite4:350m | local (new) | 178 | 0.3 s | **44** | 23.9 | **2.4 s** |
| llama3.2:1b | local (new) | 143 | 0.6 s | 79 | 12.8 | 8.0 s |
| gemma3:1b | local (new) | 140 | 0.9 s | 103 | 14.8 | 8.0 s |
| qwen3:1.7b | local (re-test) | 120 | 1.5 s | 160 | 11.6 | 14.8 s |
| gemma3:12b | GPU-server tier | 28 | 4.0 s | 99 | | |
| qwen2.5:14b | GPU-server tier | 25 | 5.8 s | 99 | | |
| phi4:14b | GPU-server tier | 16 | 7.0 s | 96 | | |

## Hand check on the 4 prompts with one right answer

| Model | Math (270) | Logic (Ben) | Sentiment (mixed) | NER (4 entities incl. date) |
|---|---|---|---|---|
| granite4:350m | ✓ | ✓ | ✓ | ✗ missed the date |
| llama3.2:1b | ✓ | ✓ (hedged: "it's likely") | ✗ negative | ✓ |
| gemma3:1b | ✓ | ✓ | ✓ | ✓ |
| qwen3:1.7b | ✓ | ✗ (reasons to Ben, answers Ana) | ✓ | ✓ |
| gemma3:12b | ✗ 150 (counted Monday's sales twice) | ✓ | ✓ | ✓ |
| phi4:14b | ✓ | ✓ | ✓ | ✓ |
| qwen2.5:14b | ✓ | ✓ | ✓ | ✓ |

All 7 found the bug in the code-debugging prompt. All summaries were one sentence with no invented facts spotted.

## Findings

1. **All 3 new local models work** and are fast. With qwen2.5:0.5b out of the set, granite4:350m is now the smallest and fastest model: 2.4 s per answer on 2 CPU threads, with the shortest answers (44 tokens). It got 3/4 here.
2. **gemma3:1b went 4/4 on one-quarter the size of gemma3:4b**, at about 8 s per answer on CPU. One prompt per category proves little, but it's a strong candidate for the CPU-only local tier.
3. **qwen3:1.7b is unchanged from v1** (same answers, as expected at temperature 0). Two problems remain:
   - It still states the wrong name on the logic puzzle after reasoning correctly.
   - Ollama's `think: false` appends a `/no_think` marker to the prompt, and the model copied it into its code answer (`- 1 / no_think`). The bench script now strips `/ no_think` and `<think>` blocks, but an answer that quotes code can still be corrupted. Worth checking in the dry run; if it keeps happening, run qwen3 with thinking on and strip the thinking block, at the cost of more tokens.
4. **Bigger isn't automatically better.** gemma3:12b got the simple math wrong (counted Monday's 120 twice), which the 1B Gemma got right. phi4:14b and qwen2.5:14b went 4/4. The real benchmark will show whether the 12–14B "own GPU server" tier is worth its cost.
5. **The 14B models run comfortably on one T4** (16–28 tok/s, 4–7 s per answer). The extended GPU tier is feasible on free Kaggle.
6. **Script fix:** v2 flagged 4 answers as "thinking leaked" when only trailing whitespace differed. Fixed in `notebooks/local_bench_ollama.py` (whitespace no longer counts; `/ no_think` with a space is now stripped too).
