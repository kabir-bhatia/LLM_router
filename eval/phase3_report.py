"""Phase 3 outputs from graded answers: benchmark_matrix.json, benchmark_report.md (tables), plots.

Usage: .venv/Scripts/python.exe -X utf8 -m eval.phase3_report
Inputs (all in eval/results/phase3/): graded_gpu_scores.jsonl (API + local GPU answers, 240 dev tasks per model),
graded_cpu_scores.jsonl (local CPU run, 40-task sample), plus the raw answer files for token counts.
Findings text is kept in findings.md (written by hand after reading the tables) and appended to the report.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eval.answers import read_answers  # noqa: E402
from eval.grade import wilson  # noqa: E402
from eval.task_schema import CATEGORIES  # noqa: E402

D = Path(__file__).resolve().parent / "results" / "phase3"
CORE_LOCAL = ["granite4:350m", "gemma3:1b", "llama3.2:1b", "qwen3:1.7b", "qwen2.5-coder:1.5b",
              "llama3.2:3b", "phi3.5:3.8b", "gemma3:4b"]
SERVER = ["gemma3:12b", "phi4:14b", "qwen2.5:14b"]
API = ["nemotron-lightning-3p5-30b-a3b", "gpt-oss-120b", "minimax-m3p1-flash", "deepseek-v4p1-flash",
       "glm-5p3", "kimi-k3p1-pro", "hyde/glm-5.3-flash", "gemini-3.1-flash-lite"]
# Assumed cloud rates for D5 "with hardware" costs (NOT from model_prices.json; stated in the report).
CPU_HOURLY, GPU_HOURLY = 0.05, 0.35


def load_rows(path):
    return [json.loads(l) for l in (D / path).read_text(encoding="utf-8").splitlines() if l.strip()]


def cell(rows):
    done = [r for r in rows if r["passed"] is not None]
    k = sum(1 for r in done if r["passed"])
    lo, hi = wilson(k, len(done))
    return dict(k=k, n=len(done), acc=k / len(done) if done else None, lo=lo, hi=hi)


def pct(x):
    return f"{x:.0%}" if x is not None else "-"


def p95(xs):
    xs = sorted(xs)
    return xs[max(0, int(round(0.95 * len(xs))) - 1)] if xs else None


def main():
    gpu = load_rows("graded_gpu_scores.jsonl")
    cpu = load_rows("graded_cpu_scores.jsonl")
    ans = {}
    for f in ["answers_api.jsonl", "raw_gpu_a/answers_gpu_a.jsonl", "raw_gpu_b/answers_gpu_b.jsonl"]:
        for a in read_answers(D / f):
            ans[(a["model"], a["task_id"])] = a
    cpu_ans = {(a["model"], a["task_id"]): a for a in read_answers(D / "raw_cpu/answers_cpu.jsonl")}

    by = defaultdict(list)
    for r in gpu:
        by[r["model"]].append(r)
    cby = defaultdict(list)
    for r in cpu:
        cby[r["model"]].append(r)

    matrix = {"meta": {"split": "dev", "tasks_per_model": 240, "ci": "Wilson 95%",
                       "api_reasoning_effort": "low", "cpu_sample": "eval/results/phase3/cpu_sample_ids.json",
                       "assumed_hourly_usd": {"cpu_2vcpu": CPU_HOURLY, "t4_gpu": GPU_HOURLY}}, "models": {}}
    for m in API + CORE_LOCAL + SERVER:
        rows = by.get(m, [])
        if not rows:
            continue
        a_rows = [ans[(m, r["task_id"])] for r in rows]
        e = dict(group="api" if m in API else ("local" if m in CORE_LOCAL else "gpu_server"),
                 overall=cell(rows),
                 categories={c: {d: cell([r for r in rows if r["category"] == c and d in (r["difficulty"], "all")])
                                 for d in ("easy", "hard", "all")} for c in CATEGORIES},
                 difficulty={d: cell([r for r in rows if r["difficulty"] == d]) for d in ("easy", "hard")},
                 tokens=dict(in_mean=statistics.mean(a["tokens_in"] or 0 for a in a_rows),
                             out_mean=statistics.mean(a["tokens_out"] or 0 for a in a_rows),
                             reasoning_mean=statistics.mean(a["tokens_reasoning"] or 0 for a in a_rows)),
                 latency_ms=dict(p50=statistics.median(a["latency_ms"] for a in a_rows if a["latency_ms"] is not None),
                                 p95=p95([a["latency_ms"] for a in a_rows if a["latency_ms"] is not None])),
                 unparsed=sum(1 for r in rows if r["unparsed"]), call_errors=sum(1 for a in a_rows if a["error"]),
                 truncated=sum(1 for a in a_rows if (a.get("finish_reason") or a.get("done_reason")) in ("length", "MAX_TOKENS")),
                 language_fails=sum(1 for r in rows if r.get("language_fail")))
        if e["group"] == "api":
            e["cost_per_task_usd"] = statistics.mean(a["cost_usd"] or 0 for a in a_rows)
            e["cost_total_usd"] = sum(a["cost_usd"] or 0 for a in a_rows)
        else:
            e["cost_per_task_usd_marginal"] = 0.0
            rate = GPU_HOURLY if e["group"] == "gpu_server" else CPU_HOURLY
            if e["group"] == "gpu_server":
                e["cost_per_task_usd_hardware"] = statistics.mean(a["latency_ms"] or 0 for a in a_rows) / 3.6e6 * rate
        if m in cby:
            cr = cby[m]
            ca = [cpu_ans[(m, r["task_id"])] for r in cr]
            lat = [a["latency_ms"] for a in ca if a["latency_ms"] is not None]
            e["cpu"] = dict(n=len(cr), latency_p50_ms=statistics.median(lat), latency_p95_ms=p95(lat),
                            acc_on_sample=cell(cr), tokens_out_mean=statistics.mean(a["tokens_out"] or 0 for a in ca),
                            cost_per_task_usd_hardware=statistics.mean(lat) / 3.6e6 * CPU_HOURLY)
        matrix["models"][m] = e
    (D / "benchmark_matrix.json").write_text(json.dumps(matrix, indent=1), encoding="utf-8")

    # ---------------- plots
    def heat(models, fname, title):
        data = np.array([[matrix["models"][m]["categories"][c]["all"]["acc"] for c in CATEGORIES] for m in models])
        fig, ax = plt.subplots(figsize=(10, 0.45 * len(models) + 2))
        im = ax.imshow(data, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax.set_xticks(range(len(CATEGORIES)), CATEGORIES, rotation=30, ha="right")
        ax.set_yticks(range(len(models)), models)
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                ax.text(j, i, f"{data[i, j]:.0%}", ha="center", va="center", fontsize=8,
                        color="white" if data[i, j] < 0.6 else "black")
        ax.set_title(title)
        fig.colorbar(im, ax=ax, label="accuracy (dev, n=30 per cell)")
        fig.tight_layout()
        fig.savefig(D / fname, dpi=140)
        plt.close(fig)

    m16 = [m for m in CORE_LOCAL + API if m in matrix["models"]]
    heat(m16, "accuracy_heatmap_16x8.png", "Accuracy per model x category, 240 dev tasks (API at low reasoning effort)")
    srv = [m for m in SERVER if m in matrix["models"]]
    if srv:
        heat(srv, "accuracy_heatmap_gpu_server.png", "GPU-server tier (outside the 16 models)")

    # accuracy (full dev, GPU run) vs CPU latency, Pareto front
    pts = [(m, matrix["models"][m]["cpu"]["latency_p50_ms"] / 1000, matrix["models"][m]["overall"]["acc"])
           for m in CORE_LOCAL if m in matrix["models"] and "cpu" in matrix["models"][m]]
    front = [p for p in pts if not any(q[1] <= p[1] and q[2] >= p[2] and (q[1] < p[1] or q[2] > p[2]) for q in pts)]
    fig, ax = plt.subplots(figsize=(8, 5))
    for m, x, y in pts:
        ax.scatter(x, y, s=70, color="tab:red" if (m, x, y) in front else "tab:blue", zorder=3)
        ax.annotate(m, (x, y), textcoords="offset points", xytext=(5, 4), fontsize=8)
    fs = sorted(front, key=lambda p: p[1])
    ax.plot([p[1] for p in fs], [p[2] for p in fs], "r--", lw=1, label="Pareto front")
    ax.set_xlabel("median CPU latency per answer, 2 threads (s), 40-task sample")
    ax.set_ylabel("overall dev accuracy (GPU run, 240 tasks)")
    ax.set_title("Local models: accuracy vs CPU latency")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(D / "local_accuracy_vs_cpu_latency.png", dpi=140)
    plt.close(fig)
    matrix["pareto_local"] = [p[0] for p in fs]

    # accuracy vs cost, API models
    fig, ax = plt.subplots(figsize=(8, 5))
    for m in API:
        e = matrix["models"].get(m)
        if e:
            x, y = e["cost_per_task_usd"] * 1000, e["overall"]["acc"]
            ax.errorbar(x, y, yerr=[[y - e["overall"]["lo"]], [e["overall"]["hi"] - y]], fmt="o", capsize=3)
            ax.annotate(m, (x, y), textcoords="offset points", xytext=(5, 4), fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("list-price cost per task (milli-USD, log scale)")
    ax.set_ylabel("overall dev accuracy (95% Wilson CI)")
    ax.set_title("API models at low reasoning effort: accuracy vs cost")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(D / "api_accuracy_vs_cost.png", dpi=140)
    plt.close(fig)
    (D / "benchmark_matrix.json").write_text(json.dumps(matrix, indent=1), encoding="utf-8")

    # ---------------- markdown
    L = ["# Phase 3 benchmark report (dev split, 240 tasks per model)", "",
         "Accuracy = passed / graded with Wilson 95% CI. Judge for factual/summarisation: GLM 5.3 Flash (D8/D10), "
         "Qwen for GLM's own answers. API models ran at **low reasoning effort** (D11): B1 is therefore the best model as it "
         "would be deployed cheaply, not each model at full strength. Per-cell n is 15 (easy/hard) or 30 (category); read those "
         "as indicative. Local accuracy is from the Kaggle T4 run; local CPU speed is from a fixed 40-task sample "
         "(2 threads, no GPU). One run per model, temperature 0.", ""]

    def row(m):
        e = matrix["models"][m]
        o = e["overall"]
        return o, e

    def overall_table(models, local):
        T = ["| model | overall acc [95% CI] | easy | hard | tokens in / out (mean) | reasoning tok | "
             + ("GPU p50 / p95 ms | CPU p50 / p95 s | " if local else "latency p50 / p95 ms | cost per task (list) | ")
             + "unparsed | trunc | call err |", "|" + "---|" * (11 if local else 11)]
        for m in models:
            if m not in matrix["models"]:
                continue
            o, e = row(m)
            t, lt = e["tokens"], e["latency_ms"]
            base = (f"| {m} | {pct(o['acc'])} [{pct(o['lo'])}-{pct(o['hi'])}] | {pct(e['difficulty']['easy']['acc'])} | "
                    f"{pct(e['difficulty']['hard']['acc'])} | {t['in_mean']:.0f} / {t['out_mean']:.0f} | {t['reasoning_mean']:.0f} | ")
            if local:
                c = e.get("cpu")
                base += (f"{lt['p50']:.0f} / {lt['p95']:.0f} | "
                         + (f"{c['latency_p50_ms'] / 1000:.1f} / {c['latency_p95_ms'] / 1000:.1f} | " if c else "- | "))
            else:
                base += f"{lt['p50']:.0f} / {lt['p95']:.0f} | ${e['cost_per_task_usd']:.5f} | "
            L.append(base + f"{e['unparsed']} | {e['truncated']} | {e['call_errors']} |")
        return T + L[len(L) - sum(1 for m in models if m in matrix['models']):] if False else None

    def emit(models, local, title):
        header = ["", f"## {title}", ""]
        cols = ("| model | overall acc [95% CI] | easy | hard | tokens in / out (mean) | reasoning tok | "
                + ("GPU p50 / p95 ms | CPU p50 / p95 s | " if local else "latency p50 / p95 ms | cost per task (list) | ")
                + "unparsed | trunc | call err |")
        L.extend(header + [cols, "|" + "---|" * (cols.count("|") - 1)])
        for m in models:
            if m not in matrix["models"]:
                continue
            o, e = row(m)
            t, lt = e["tokens"], e["latency_ms"]
            s = (f"| {m} | {pct(o['acc'])} [{pct(o['lo'])}-{pct(o['hi'])}] | {pct(e['difficulty']['easy']['acc'])} | "
                 f"{pct(e['difficulty']['hard']['acc'])} | {t['in_mean']:.0f} / {t['out_mean']:.0f} | {t['reasoning_mean']:.0f} | ")
            if local:
                c = e.get("cpu")
                s += (f"{lt['p50']:.0f} / {lt['p95']:.0f} | "
                      + (f"{c['latency_p50_ms'] / 1000:.1f} / {c['latency_p95_ms'] / 1000:.1f} | " if c else "- | "))
            else:
                s += f"{lt['p50']:.0f} / {lt['p95']:.0f} | ${e['cost_per_task_usd']:.5f} | "
            L.append(s + f"{e['unparsed']} | {e['truncated']} | {e['call_errors']} |")

    emit(API, False, "API models (8)")
    emit(CORE_LOCAL, True, "Local models (8), accuracy on GPU, speed on CPU")
    emit(SERVER, True, "GPU-server tier (outside the 16): gemma3:12b, phi4:14b, qwen2.5:14b (T4 x2)")

    L += ["", "## Accuracy per category (all difficulties, n=30; Wilson 95% CI)", ""]
    allm = [m for m in API + CORE_LOCAL + SERVER if m in matrix["models"]]
    L += ["| model | " + " | ".join(CATEGORIES) + " |", "|" + "---|" * (len(CATEGORIES) + 1)]
    for m in allm:
        cs = matrix["models"][m]["categories"]
        L.append(f"| {m}{' (server tier)' if m in SERVER else ''} | " + " | ".join(
            f"{pct(cs[c]['all']['acc'])} [{pct(cs[c]['all']['lo'])}-{pct(cs[c]['all']['hi'])}]" for c in CATEGORIES) + " |")
    for d in ("easy", "hard"):
        L += ["", f"## Accuracy per category, {d} tasks (n=15)", ""]
        L += ["| model | " + " | ".join(CATEGORIES) + " |", "|" + "---|" * (len(CATEGORIES) + 1)]
        for m in allm:
            cs = matrix["models"][m]["categories"]
            L.append(f"| {m} | " + " | ".join(
                f"{cs[c][d]['k']}/{cs[c][d]['n']} [{pct(cs[c][d]['lo'])}-{pct(cs[c][d]['hi'])}]" for c in CATEGORIES) + " |")

    L += ["", "## Cost (D5)", "",
          f"Marginal local cost is $0. With hardware, a local answer is priced at its measured latency x an assumed rate: "
          f"CPU instance ${CPU_HOURLY}/h (2 vCPU, assumption, not from the price table), T4 GPU box ${GPU_HOURLY}/h (assumption).", "",
          "| model | CPU latency-priced cost per task | GPU latency-priced cost per task |", "|---|---|---|"]
    for m in CORE_LOCAL + SERVER:
        e = matrix["models"].get(m)
        if e:
            cc = e.get("cpu", {}).get("cost_per_task_usd_hardware")
            gc = e.get("cost_per_task_usd_hardware")
            L.append(f"| {m} | {'$%.6f' % cc if cc is not None else '-'} | {'$%.6f' % gc if gc is not None else '-'} |")
    L += ["", "![heatmap](accuracy_heatmap_16x8.png)", "", "![server tier](accuracy_heatmap_gpu_server.png)", "",
          "![local pareto](local_accuracy_vs_cpu_latency.png)", "", "![api cost](api_accuracy_vs_cost.png)", ""]
    L.append(f"Local Pareto front (accuracy vs CPU median latency): {', '.join(matrix['pareto_local'])}.")
    fnd = D / "findings.md"
    if fnd.exists():
        L += ["", fnd.read_text(encoding="utf-8")]
    (D / "benchmark_report.md").write_text("\n".join(L), encoding="utf-8")
    print("wrote benchmark_matrix.json, benchmark_report.md, plots")


if __name__ == "__main__":
    main()
