# Phase 0 report: model sources

Run 2026-11-20 by `scripts/phase0_check.py` (raw data: `phase0_raw.json`, prices: `../model_prices.json`).
Test prompt: "What is 17 * 23? Answer with just the number."

## Summary

| Source | Status | Key finding |
|---|---|---|
| Gemini via Vertex AI | **FAIL** | Service-account key file not on disk (`FileNotFoundError` for the path in `GOOGLE_APPLICATION_CREDENTIALS`), so no call reached Google. This is *not* proof of the account suspension; it needs the key file back (or a new one) once the Cloud account is sorted out (session `gcloud-billing`). Not touched. |
| Gemini via AI Studio key | **works** | `gemini-3.1-flash-lite`: 1 call + burst of 5, all ok, no 429s. Only the cheapest model was tested; the handoff notes warn that 3.x models were throttled and `gemini-2.5-pro` 404'd on this path. |
| Hyde gateway | **1 of 5 models usable** | The key can only access `hyde/glm-5.3-flash`. `hyde/kimi-k3`, `hyde/kimi-k3.1-pro` and both embedding models return 403 `key_model_access_denied`. **Blocker for the Kimi blind judge.** |
| Fireworks | **10/10 models work** | Spend $0.0014 of the $0.20 cap. |
| Ollama local | **BLOCKED (machine)** | `qwen2.5:0.5b` pulled fine, but the llama runner crashes on load (`std::bad_alloc` / `unable to allocate CPU buffer`) for it **and** for the older tinyllama and llama3.2 models, with ~3.5 GB RAM free. Same family of machine-state problem the HANDOFF describes for torch; try a restart, then re-run `phase0_check ollama`. No tokens/s or RAM numbers yet. |
| Library tags | all 16 exist | Sizes below. |

## Total spend

Fireworks $0.001445; Gemini (AI Studio, ~6 calls of ~20 tokens) well under $0.001; Hyde $0 (free). **Total under $0.01.**

## Hyde details worth knowing

- `/v1/models` lists only `hyde/glm-5.3-flash` (the key is model-restricted), so the other names are untestable until the user gets a key with wider access.
- `hyde/glm-5.3-flash`: reports `completion_tokens_details.reasoning_tokens` (usage fields: completion_tokens, completion_tokens_details, prompt_tokens, prompt_tokens_details, total_tokens). `reasoning_effort` is accepted (low gave 3 reasoning tokens, high 9, default 29 on the tiny prompt), JSON mode accepted, `max_tokens=8` truncates (`finish_reason=length`), 5 concurrent calls all succeeded.

## Fireworks details worth knowing

- `/models` returns 31 entries (chat LLMs, routers, embedding models). All 10 tested chat models accepted `reasoning_effort=low`.
- Reasoning tokens are billed as output: `nemotron-lightning-3p5-30b-a3b` used all 256 tokens reasoning and never answered (finish=length), so it needs a larger `max_tokens` or a non-reasoning setup; do not cap tightly on reasoning models.
- `kimi-k3p1-pro` is listed `supports_chat: false` but answered fine on chat completions.
- `minimax-m3p1-flash` price comes from its model page only (not in the pricing table).

## Candidate lists (proposed, 8 local + 8 API)

**Local (Ollama; sizes from registry manifests):** qwen2.5:0.5b (0.4 GB), qwen2.5:1.5b (0.99), qwen3:1.7b (1.36), qwen3:4b (2.5), llama3.2:3b (2.02), gemma3:4b (3.35), phi3.5:3.8b (2.18), qwen2.5-coder:1.5b (0.99). Alternates if a slot is needed: qwen2.5:3b, llama3.2:1b, gemma3:1b, granite4:350m, smollm2:1.7b. `gemma3n:e2b/e4b` exist but are 7.8/9.8 GB, too big for the 4 GB box.

**API ($ per 1M input / output):**

| # | Model | Via | In | Out | Role |
|---|---|---|---|---|---|
| 1 | gemini-3.1-flash-lite | AI Studio | 0.25 | 1.50 | cheap tier (prices from `src/services/cost.py`, dated 2026-08-15, recheck) |
| 2 | nemotron-lightning-3p5-30b-a3b | Fireworks | 0.05 | 0.20 | cheapest |
| 3 | gpt-oss-120b | Fireworks | 0.15 | 0.60 | cheap open-weight |
| 4 | glm-5.3-flash | Hyde (priced at market) | 0.15 | 0.50 | contestant |
| 5 | minimax-m3p1-flash | Fireworks | 0.15 | 0.60 | cheap |
| 6 | deepseek-v4p1-flash | Fireworks | 0.30 | 1.20 | mid |
| 7 | glm-5p3 | Fireworks | 1.40 | 4.40 | mid-high |
| 8 | kimi-k3p1-pro | Fireworks | 2.00 | 10.00 | **proposed strongest-paid baseline** unless Vertex gemini-2.5-pro (1.25/10.00) is restored |

## Blockers / needs from the user

1. Ollama runner crash on this laptop (restart likely needed); then re-run `.venv/Scripts/python.exe -m scripts.phase0_check ollama`.
2. Hyde key restricted to `hyde/glm-5.3-flash`; need a key that also allows `hyde/kimi-k3`, `hyde/kimi-k3.1-pro` for the judge (and the embedding models, if wanted).
3. Vertex service-account JSON missing from the repo root; depends on the Cloud billing/suspension issue (other session).
4. Gemini 2.5-pro / 3.6-flash not verified on the AI Studio path.

## Code added

`src/providers/openai_compat.py` (Fireworks + Hyde), `OllamaProvider` restored in `src/providers/base.py`, `scripts/phase0_check.py`, `notebooks/local_bench_kaggle.ipynb` + `notebooks/local_bench_ollama.py` (not run).

## Raw tables (generated 2026-11-20 02:54:21)

### Gemini

| path | works | latency | tokens (in/out) | notes |
|---|---|---|---|---|
| Vertex AI (gemini-3.1-flash-lite) | False | - ms | -/- | FileNotFoundError: [Errno 2] No such file or directory: './project-0bfd279e-1899-43a5-9de-17a0df95b9e5.json' |
| AI Studio key | True | 3945 ms | 17/3 (thoughts None) | burst of 5: 5/5 ok; ok |

### Hyde gateway

Base URL: `https://inference.hyde.tech/v1`; /models lists: ['hyde/glm-5.3-flash']

| model | works | latency | tokens (in/out/reasoning) | $ | max_tokens=8 | JSON mode | reasoning_effort low/high | burst5 | notes |
|---|---|---|---|---|---|---|---|---|---|
| hyde/glm-5.3-flash | yes | 534 ms | 26/30/29 | 0 (free) | finish=length | ok | 3 / 9 | 5/5  | usage keys ['completion_tokens', 'completion_tokens_details', 'prompt_tokens', 'prompt_tokens_details', 'total_tokens'] |
| hyde/kimi-k3 | no | - | - | - | - | - | - | - | ProviderError: HTTP 403: {"error":{"message":"key not allowed to access model. This key can only access models=['hyde/glm-5.3-flash']. Tried to access hyde/kimi-k3","type":"key_model_access_denied","param":"model","code":"403"}} |
| hyde/kimi-k3.1-pro | no | - | - | - | - | - | - | - | ProviderError: HTTP 403: {"error":{"message":"key not allowed to access model. This key can only access models=['hyde/glm-5.3-flash']. Tried to access hyde/kimi-k3.1-pro","type":"key_model_access_denied","param":"model","code":"403"}} |

| embedding model | works | latency | dim | usage | burst5 | notes |
|---|---|---|---|---|---|---|
| hyde/qwen3-embedding-8b | False | - ms | - | None | -/5 | ProviderError: HTTP 403: {"error":{"message":"key not allowed to access model. This key can only access models=['hyde/glm-5.3-flash']. Tried to access hyde/qwen3-embedding-8b","type":"key_model_access_denied","param":"model","code":"403"}} |
| hyde/nemotron-3.5-embed-8b | False | - ms | - | None | -/5 | ProviderError: HTTP 403: {"error":{"message":"key not allowed to access model. This key can only access models=['hyde/glm-5.3-flash']. Tried to access hyde/nemotron-3.5-embed-8b","type":"key_model_access_denied","param":"model","code":"403"}} |

### Fireworks

Total spend: $0.001445 (cap $0.2)

| model | works | latency | tokens (in/out/reasoning) | $ | notes |
|---|---|---|---|---|---|
| nemotron-lightning-3p5-30b-a3b | True | 1037 ms | 32/256/256 | 0.0000528 | reasoning_effort=low finish=length |
| gpt-oss-120b | True | 1071 ms | 86/22/11 | 0.0000261 | reasoning_effort=low finish=stop |
| glm-5p3-flash | True | 512 ms | 26/6/2 | 0.0000069 | reasoning_effort=low finish=stop |
| minimax-m3p1-flash | True | 610 ms | 214/12/8 | 0.0000393 | reasoning_effort=low finish=stop |
| deepseek-v4p1-flash | True | 855 ms | 44/21/18 | 0.0000384 | reasoning_effort=low finish=stop |
| minimax-m3 | True | 690 ms | 138/51/48 | 0.0001026 | reasoning_effort=low finish=stop |
| nemotron-3-ultra-nvfp4 | True | 598 ms | 32/33/28 | 0.0000984 | reasoning_effort=low finish=stop |
| glm-5p3 | True | 708 ms | 26/10/6 | 0.0000804 | reasoning_effort=low finish=stop |
| qwen3p8-max | True | 824 ms | 56/62/56 | 0.0004840 | reasoning_effort=low finish=stop |
| kimi-k3p1-pro | True | 883 ms | 103/31/17 | 0.0005160 | reasoning_effort=low finish=stop |

### Ollama

Model qwen2.5:0.5b, server_up=True

| mode | latency | tokens (in/out) | tok/s | load ms | peak Ollama RSS MB |
|---|---|---|---|---|---|
| gpu | - | -/- | ProviderError: Ollama HTTP error: 500 | - | - |
| gpu | - | -/- | ProviderError: Ollama HTTP error: 500 | - | - |
| gpu | - | -/- | ProviderError: Ollama HTTP error: 500 | - | - |
| cpu_2threads | - | -/- | ProviderError: Ollama HTTP error: 500 | - | - |
| cpu_2threads | - | -/- | ProviderError: Ollama HTTP error: 500 | - | - |
| cpu_2threads | - | -/- | ProviderError: Ollama HTTP error: 500 | - | - |

### Ollama library tags

| tag | exists | size GB |
|---|---|---|
| qwen2.5:0.5b | True | 0.4 |
| qwen2.5:1.5b | True | 0.99 |
| qwen2.5:3b | True | 1.93 |
| qwen3:1.7b | True | 1.36 |
| qwen3:4b | True | 2.5 |
| llama3.2:1b | True | 1.32 |
| llama3.2:3b | True | 2.02 |
| gemma3:1b | True | 0.81 |
| gemma3:4b | True | 3.35 |
| gemma3n:e2b | True | 7.84 |
| gemma3n:e4b | True | 9.77 |
| phi3.5:latest | True | 2.18 |
| phi3.5:3.8b | True | 2.18 |
| qwen2.5-coder:1.5b | True | 0.99 |
| granite4:350m | True | 0.71 |
| smollm2:1.7b | True | 1.82 |

