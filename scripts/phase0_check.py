"""
Phase 0: prove every model source works before benchmarking.

Run (from repo root):
    .venv/Scripts/python.exe -m scripts.phase0_check [gemini|hyde|fireworks|ollama|tags|report ...]
No args = all sections. Raw results are merged into eval/results/phase0_raw.json;
`report` renders eval/results/phase0_report.md tables from that file.

Never prints keys. Fireworks spend is capped (FIREWORKS_CAP_USD).
"""

import asyncio
import json
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "eval" / "results" / "phase0_raw.json"
PRICES = json.loads((ROOT / "eval" / "model_prices.json").read_text(encoding="utf-8"))

PROMPT = "What is 17 * 23? Answer with just the number."
FIREWORKS_CAP_USD = 0.20

HYDE_CHAT = ["hyde/glm-5.3-flash", "hyde/kimi-k3", "hyde/kimi-k3.1-pro"]
HYDE_EMBED = ["hyde/qwen3-embedding-8b", "hyde/nemotron-3.5-embed-8b"]
FIREWORKS_MODELS = [
    "accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b",
    "accounts/fireworks/models/gpt-oss-120b",
    "accounts/fireworks/models/glm-5p3-flash",
    "accounts/fireworks/models/minimax-m3p1-flash",
    "accounts/fireworks/models/deepseek-v4p1-flash",
    "accounts/fireworks/models/minimax-m3",
    "accounts/fireworks/models/nemotron-3-ultra-nvfp4",
    "accounts/fireworks/models/glm-5p3",
    "accounts/fireworks/models/qwen3p8-max",
    "accounts/fireworks/models/kimi-k3p1-pro",
]
OLLAMA_TAGS = [
    "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen3:1.7b", "qwen3:4b",
    "llama3.2:1b", "llama3.2:3b", "gemma3:1b", "gemma3:4b", "gemma3n:e2b", "gemma3n:e4b",
    "phi3.5:latest", "phi3.5:3.8b", "qwen2.5-coder:1.5b", "granite4:350m", "smollm2:1.7b",
]
OLLAMA_PROMPTS = [
    "What is the capital of France? One word.",
    "Classify the sentiment (positive/negative) of: 'The battery died in an hour, awful.'",
    "Write a Python function that returns the square of x.",
]


def load_raw() -> dict:
    return json.loads(RAW.read_text(encoding="utf-8")) if RAW.exists() else {}


def save_section(name: str, data) -> None:
    raw = load_raw()
    raw[name] = data
    raw["_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")


def cost(table: str, model: str, pt: int, ct: int) -> float:
    p = PRICES.get(table, {}).get(model)
    return round((pt * p["input"] + ct * p["output"]) / 1e6, 8) if p else 0.0


def short_err(e: Exception) -> str:
    return f"{type(e).__name__}: {str(e)[:400]}"


# ---------------------------------------------------------------- Gemini
async def check_gemini() -> dict:
    from google import genai

    from src.config import get_settings
    from src.providers.gemini import GeminiProvider

    s = get_settings()
    out: dict = {"vertex": {}, "ai_studio": {}}
    model = s.tier_simple_model
    try:
        r = await GeminiProvider().generate(PROMPT, model)
        out["vertex"] = {"model": model, "works": True, "latency_ms": r.latency_ms,
                         "prompt_tokens": r.prompt_tokens, "completion_tokens": r.completion_tokens,
                         "text": r.text[:60]}
    except Exception as e:  # noqa: BLE001
        out["vertex"] = {"model": model, "works": False, "error": short_err(e)}

    if not s.google_api_key:
        out["ai_studio"] = {"works": False, "error": "GOOGLE_API_KEY not set"}
        return out
    client = genai.Client(api_key=s.google_api_key)

    async def one() -> dict:
        t0 = time.perf_counter()
        try:
            resp = await client.aio.models.generate_content(model=model, contents=PROMPT)
            u = resp.usage_metadata
            return {"ok": True, "ms": int((time.perf_counter() - t0) * 1000),
                    "pt": u.prompt_token_count, "ct": u.candidates_token_count,
                    "thoughts": getattr(u, "thoughts_token_count", None), "text": (resp.text or "")[:60]}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "ms": int((time.perf_counter() - t0) * 1000), "error": short_err(e)}

    single = await one()
    burst = await asyncio.gather(*[one() for _ in range(5)])
    out["ai_studio"] = {"model": model, "single": single,
                        "burst5_ok": sum(b["ok"] for b in burst),
                        "burst5_errors": sorted({b["error"] for b in burst if not b["ok"]})[:3],
                        "works": single["ok"]}
    return out


# ---------------------------------------------------------------- OpenAI-compatible
def usage_summary(data: dict) -> dict:
    u = data.get("usage") or {}
    det = u.get("completion_tokens_details") or {}
    return {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
            "reasoning_tokens": det.get("reasoning_tokens"), "usage_keys": sorted(u.keys())}


def msg_of(data: dict) -> dict:
    return (data.get("choices") or [{}])[0].get("message", {}) or {}


async def probe_chat(p, model: str, table: str, rich: bool, tag: str) -> dict:
    """One tiny call; rich=True also tests reasoning effort, JSON mode, max_tokens, 5-burst."""
    rec: dict = {"model": model}
    base = {"model": model, "messages": [{"role": "user", "content": PROMPT}], "temperature": 0}
    try:
        data, ms = await p.chat({**base, "max_tokens": 512})
        rec.update(works=True, latency_ms=ms, text=(msg_of(data).get("content") or "")[:60],
                   has_reasoning_content=bool(msg_of(data).get("reasoning_content") or msg_of(data).get("reasoning")),
                   finish=data["choices"][0].get("finish_reason"), **usage_summary(data))
        rec["cost_usd"] = cost(table, model, rec["prompt_tokens"] or 0, rec["completion_tokens"] or 0)
    except Exception as e:  # noqa: BLE001
        rec.update(works=False, error=short_err(e))
        return rec
    if not rich:
        return rec

    async def variant(name: str, extra: dict) -> None:
        try:
            d, ms = await p.chat({**base, **extra})
            rec[name] = {"ok": True, "ms": ms, "finish": d["choices"][0].get("finish_reason"),
                         "text": (msg_of(d).get("content") or "")[:60], **usage_summary(d)}
        except Exception as e:  # noqa: BLE001
            rec[name] = {"ok": False, "error": short_err(e)}

    await variant("max_tokens_8", {"max_tokens": 8})
    await variant("json_mode", {"max_tokens": 256, "response_format": {"type": "json_object"},
                                "messages": [{"role": "user", "content": 'Return JSON {"answer": <17*23>}'}]})
    for eff in ("low", "high"):
        await variant(f"reasoning_effort_{eff}", {"max_tokens": 1024, "reasoning_effort": eff})

    async def one() -> dict:
        try:
            _, ms = await p.chat({**base, "max_tokens": 64})
            return {"ok": True, "ms": ms}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": short_err(e)}

    burst = await asyncio.gather(*[one() for _ in range(5)])
    rec["burst5"] = {"ok": sum(b["ok"] for b in burst),
                     "errors": sorted({b["error"] for b in burst if not b["ok"]})[:3],
                     "median_ms": int(statistics.median([b["ms"] for b in burst if b["ok"]] or [0]))}
    return rec


async def check_hyde() -> dict:
    from src.providers import OpenAICompatProvider

    p = OpenAICompatProvider.hyde()
    out: dict = {"base_url": p.base_url, "chat": [], "embeddings": []}
    try:
        out["models_listed"] = [m.get("id") for m in await p.list_models()]
    except Exception as e:  # noqa: BLE001
        out["models_listed_error"] = short_err(e)
    for m in HYDE_CHAT:
        out["chat"].append(await probe_chat(p, m, "hyde", rich=True, tag="hyde"))
    for m in HYDE_EMBED:
        rec: dict = {"model": m}
        try:
            d, ms = await p.embed(m, ["hello world"])
            rec.update(works=True, latency_ms=ms, dim=len(d["data"][0]["embedding"]),
                       usage=d.get("usage"))

            async def one():
                try:
                    await p.embed(m, ["burst test"])
                    return None
                except Exception as e:  # noqa: BLE001
                    return short_err(e)

            errs = await asyncio.gather(*[one() for _ in range(5)])
            rec["burst5_ok"] = sum(e is None for e in errs)
            rec["burst5_errors"] = sorted({e for e in errs if e})[:3]
        except Exception as e:  # noqa: BLE001
            rec.update(works=False, error=short_err(e))
        out["embeddings"].append(rec)
    await p.close()
    return out


async def check_fireworks() -> dict:
    from src.providers import OpenAICompatProvider

    p = OpenAICompatProvider.fireworks()
    out: dict = {"models": [], "spent_usd": 0.0, "cap_usd": FIREWORKS_CAP_USD}
    try:
        listing = await p.list_models()
        out["models_available"] = [m.get("id") for m in listing]
    except Exception as e:  # noqa: BLE001
        out["listing_error"] = short_err(e)
    for m in FIREWORKS_MODELS:
        if out["spent_usd"] >= FIREWORKS_CAP_USD:
            out["models"].append({"model": m, "works": None, "error": "skipped: spend cap"})
            continue
        rec: dict = {"model": m}
        for extra_name, extra in (("reasoning_effort=low", {"reasoning_effort": "low"}), ("plain", {})):
            try:
                data, ms = await p.chat({"model": m, "messages": [{"role": "user", "content": PROMPT}],
                                         "temperature": 0, "max_tokens": 256, **extra})
                rec.update(works=True, latency_ms=ms, params=extra_name,
                           text=(msg_of(data).get("content") or "")[:60],
                           finish=data["choices"][0].get("finish_reason"), **usage_summary(data))
                rec["cost_usd"] = cost("fireworks", m, rec["prompt_tokens"] or 0, rec["completion_tokens"] or 0)
                out["spent_usd"] = round(out["spent_usd"] + rec["cost_usd"], 8)
                break
            except Exception as e:  # noqa: BLE001
                rec.update(works=False, params=extra_name, error=short_err(e))
        out["models"].append(rec)
    await p.close()
    return out


# ---------------------------------------------------------------- Ollama
def ollama_exe() -> str:
    import shutil
    return shutil.which("ollama") or r"C:\Users\Kabir\AppData\Local\Programs\Ollama\ollama.exe"


def ollama_rss_mb() -> float:
    import psutil
    total = 0
    for pr in psutil.process_iter(["name", "memory_info"]):
        if "ollama" in (pr.info["name"] or "").lower() and pr.info["memory_info"]:
            total += pr.info["memory_info"].rss
    return total / 2**20


async def check_ollama(model: str = "qwen2.5:0.5b") -> dict:
    from src.providers import OllamaProvider

    out: dict = {"model": model, "runs": []}
    probe = OllamaProvider()
    if not await probe.health_check():
        subprocess.Popen([ollama_exe(), "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.sleep(5)
    out["server_up"] = await probe.health_check()
    if model not in await probe.list_models():
        subprocess.run([ollama_exe(), "pull", model], check=False)
    for mode, opts in (("gpu", {"num_predict": 64, "temperature": 0}),
                       ("cpu_2threads", {"num_predict": 64, "temperature": 0, "num_gpu": 0, "num_thread": 2})):
        prov = OllamaProvider(keep_alive=0, options=opts)
        for prompt in OLLAMA_PROMPTS:
            peak = [0.0]
            stop = threading.Event()

            def poll():
                while not stop.is_set():
                    peak[0] = max(peak[0], ollama_rss_mb())
                    time.sleep(0.25)

            th = threading.Thread(target=poll, daemon=True)
            th.start()
            try:
                r = await prov.generate(prompt, model)
                d = r.raw_response
                tps = d["eval_count"] / (d["eval_duration"] / 1e9) if d.get("eval_duration") else None
                out["runs"].append({"mode": mode, "latency_ms": r.latency_ms,
                                    "prompt_tokens": r.prompt_tokens, "completion_tokens": r.completion_tokens,
                                    "tokens_per_s": round(tps, 1) if tps else None,
                                    "load_ms": int(d.get("load_duration", 0) / 1e6),
                                    "peak_ollama_rss_mb": round(peak[0]), "text": r.text[:50]})
            except Exception as e:  # noqa: BLE001
                out["runs"].append({"mode": mode, "error": short_err(e)})
            finally:
                stop.set()
                th.join()
        await prov.close()
    await probe.close()
    return out


async def check_tags() -> dict:
    res = {}
    async with httpx.AsyncClient(timeout=20) as c:
        for tag in OLLAMA_TAGS:
            name, _, t = tag.partition(":")
            r = await c.get(f"https://registry.ollama.ai/v2/library/{name}/manifests/{t}",
                            headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"})
            size = None
            if r.status_code == 200:
                try:
                    m = r.json()
                    size = round((sum(l["size"] for l in m.get("layers", [])) + m["config"]["size"]) / 1e9, 2)
                except Exception:  # noqa: BLE001
                    pass
            res[tag] = {"exists": r.status_code == 200, "http": r.status_code, "size_gb": size}
    return res


# ---------------------------------------------------------------- report
def render_report() -> str:
    raw = load_raw()
    L = [f"## Raw tables (generated {raw.get('_updated')})", ""]
    g = raw.get("gemini")
    if g:
        L += ["### Gemini", "", "| path | works | latency | tokens (in/out) | notes |", "|---|---|---|---|---|"]
        v = g["vertex"]
        L.append(f"| Vertex AI ({v.get('model')}) | {v.get('works')} | {v.get('latency_ms', '-')} ms | "
                 f"{v.get('prompt_tokens', '-')}/{v.get('completion_tokens', '-')} | {v.get('error', 'ok')} |")
        a = g["ai_studio"]
        s = a.get("single", {})
        L.append(f"| AI Studio key | {a.get('works')} | {s.get('ms', '-')} ms | {s.get('pt', '-')}/{s.get('ct', '-')} "
                 f"(thoughts {s.get('thoughts')}) | burst of 5: {a.get('burst5_ok')}/5 ok; "
                 f"{s.get('error') or '; '.join(a.get('burst5_errors', [])) or 'ok'} |")
        L.append("")
    h = raw.get("hyde")
    if h:
        L += ["### Hyde gateway", "", f"Base URL: `{h['base_url']}`; /models lists: {h.get('models_listed', h.get('models_listed_error'))}", "",
              "| model | works | latency | tokens (in/out/reasoning) | $ | max_tokens=8 | JSON mode | reasoning_effort low/high | burst5 | notes |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for r in h["chat"]:
            if not r.get("works"):
                L.append(f"| {r['model']} | no | - | - | - | - | - | - | - | {r.get('error')} |")
                continue
            def f(k):
                v = r.get(k, {})
                return "ok" if v.get("ok") else f"fail {str(v.get('error'))[:80]}"
            mt = r.get("max_tokens_8", {})
            lo, hi = r.get("reasoning_effort_low", {}), r.get("reasoning_effort_high", {})
            eff = (f"{lo.get('reasoning_tokens') if lo.get('ok') else 'rej'} / {hi.get('reasoning_tokens') if hi.get('ok') else 'rej'}")
            b = r.get("burst5", {})
            L.append(f"| {r['model']} | yes | {r['latency_ms']} ms | {r['prompt_tokens']}/{r['completion_tokens']}/{r.get('reasoning_tokens')} | "
                     f"0 (free) | finish={mt.get('finish')} | {f('json_mode')} | {eff} | {b.get('ok')}/5 {b.get('errors') or ''} | usage keys {r.get('usage_keys')} |")
        L += ["", "| embedding model | works | latency | dim | usage | burst5 | notes |", "|---|---|---|---|---|---|---|"]
        for r in h["embeddings"]:
            L.append(f"| {r['model']} | {r.get('works')} | {r.get('latency_ms', '-')} ms | {r.get('dim', '-')} | "
                     f"{r.get('usage')} | {r.get('burst5_ok', '-')}/5 | {r.get('error', '')} |")
        L.append("")
    fw = raw.get("fireworks")
    if fw:
        L += ["### Fireworks", "", f"Total spend: ${fw['spent_usd']:.6f} (cap ${fw['cap_usd']})", "",
              "| model | works | latency | tokens (in/out/reasoning) | $ | notes |", "|---|---|---|---|---|---|"]
        for r in fw["models"]:
            L.append(f"| {r['model'].split('/')[-1]} | {r.get('works')} | {r.get('latency_ms', '-')} ms | "
                     f"{r.get('prompt_tokens', '-')}/{r.get('completion_tokens', '-')}/{r.get('reasoning_tokens')} | "
                     f"{r.get('cost_usd', 0):.7f} | {r.get('error') or r.get('params')} finish={r.get('finish')} |")
        L.append("")
    o = raw.get("ollama")
    if o:
        L += ["### Ollama", "", f"Model {o['model']}, server_up={o['server_up']}", "",
              "| mode | latency | tokens (in/out) | tok/s | load ms | peak Ollama RSS MB |", "|---|---|---|---|---|---|"]
        for r in o["runs"]:
            L.append(f"| {r['mode']} | {r.get('latency_ms', '-')} | {r.get('prompt_tokens', '-')}/{r.get('completion_tokens', '-')} | "
                     f"{r.get('tokens_per_s', r.get('error'))} | {r.get('load_ms', '-')} | {r.get('peak_ollama_rss_mb', '-')} |")
        L.append("")
    t = raw.get("tags")
    if t:
        L += ["### Ollama library tags", "", "| tag | exists | size GB |", "|---|---|---|"]
        for k, v in t.items():
            L.append(f"| {k} | {v['exists']} | {v['size_gb']} |")
        L.append("")
    return "\n".join(L)


async def main(argv: list[str]) -> None:
    sections = argv or ["gemini", "hyde", "fireworks", "ollama", "tags"]
    fns = {"gemini": check_gemini, "hyde": check_hyde, "fireworks": check_fireworks,
           "ollama": check_ollama, "tags": check_tags}
    for s in sections:
        if s == "report":
            print(render_report())
            continue
        print(f"== {s} ...", flush=True)
        res = await fns[s]()
        save_section(s, res)
        print(f"== {s} done", flush=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
