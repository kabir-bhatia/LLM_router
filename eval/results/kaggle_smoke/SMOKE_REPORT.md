# Kaggle smoke test: 8 local models

Run 2026-11-20 on a free Kaggle T4 with `notebooks/local_bench_kaggle.ipynb` (Ollama, temperature 0,
`num_predict` 512). 8 models × 8 prompts (one per category) on the GPU, plus a CPU-only pass
(2 threads, no GPU) for the smallest and largest model. Raw data: `results_gpu_smoke.json`,
`results_cpu_smoke.json`, prompts: `prompts.json`.

**This is a smoke test, not the benchmark.** One prompt per category says whether a model loads,
answers and how fast it is. It says almost nothing about accuracy. The ✓/✗ below are a hand check
of 4 prompts with a single right answer, kept only to spot obvious problems.

## Did every model run?

Yes: 64/64 GPU calls and 16/16 CPU calls returned, with no errors.

## Speed

| Model | GPU tok/s | GPU median latency | Median output tokens | CPU (2 threads) tok/s | CPU median latency |
|---|---|---|---|---|---|
| qwen2.5:0.5b | 243 | 0.5 s | 96 | 25.5 | 6.2 s |
| qwen2.5:1.5b | 128 | 0.8 s | 95 | | |
| qwen2.5-coder:1.5b | 126 | 0.7 s | 67 | | |
| qwen3:1.7b | 110 | 1.7 s | 160 | | |
| phi3.5:3.8b | 90 | 1.7 s | 148 | | |
| llama3.2:3b | 71 | 1.6 s | 93 | | |
| gemma3:4b | 54 | 2.5 s | 94 | | |
| qwen3:4b | 50 | 10.2 s | **512 (hit the cap)** | 5.0 | **105 s** |

## Hand check on the 4 prompts with one right answer

| Model | Math (270) | Logic (Ben) | Sentiment (mixed) | NER (4 entities, right types) |
|---|---|---|---|---|
| qwen2.5:0.5b | ✓ | ✗ Ana | ✗ negative | ✗ wrong types |
| qwen2.5:1.5b | ✓ | ✓ | ✗ negative | ✓ |
| qwen2.5-coder:1.5b | ✗ 150 | ✗ Ana | ✗ negative | ✓ |
| qwen3:1.7b | ✓ | ✗ (reasons to Ben, then answers Ana) | ✓ | ✓ |
| phi3.5:3.8b | ✓ | ✗ Ana | ✗ negative | ✓ |
| llama3.2:3b | ✓ | ✗ Ana | ✓ | ✓ |
| gemma3:4b | ✓ | ✓ | ✓ | ✓ |
| qwen3:4b | ✗ cut off | ✗ cut off | ✗ cut off | ✗ cut off |

Spotted in the free-text answers:
- **Summaries:** phi3.5 wrote "four-year" (the text says three), and gemma3 wrote "$40km". These are faithfulness errors a length check would not catch, so summaries need the judge.
- **Code debugging:** all 8 found the bug.

## Findings

1. **No infrastructure blocker.** All 8 models download, load and answer on a free T4. The laptop is not needed for local inference.
2. **qwen3:4b is unusable as configured.** It writes its reasoning into the answer and hits the 512-token cap on 7/8 prompts, so it never states an answer. `think: false` did not stop it, and on qwen3:1.7b the `/no_think` switch leaked into a code answer. Before the benchmark, either strip `<think>` output properly or swap in a non-thinking Qwen3 instruct variant. Check which tags exist.
3. **The CPU constraint matters.** On 2 threads, qwen2.5:0.5b answers in about 6 s and qwen3:4b in about 105 s. A 4B model is too slow for a CPU-only local tier, so the realistic local tier is 0.5–2B models, with bigger ones only on a GPU. This is the accuracy-vs-speed trade-off the benchmark has to measure.
4. **Logic is where small models break** (only 2/8 correct, several reasoned correctly and then stated the wrong name). That supports a deterministic logic solver as Layer 1. Math was right for 6/8.
5. **Answers are wordy** (about 95 output tokens median), and answer format varies (boxed, bold, prose). The benchmark needs a fixed answer-format instruction (e.g. a final `ANSWER:` line) so the graders can extract answers reliably. The same instruction will reduce paid output tokens later.
