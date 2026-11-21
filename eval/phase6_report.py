"""Phase 6 step 5b: statistics, plots and final_report.md from graded_scores.jsonl (eval/phase6_grade.py). Nothing is tuned here.

  python -X utf8 -m eval.phase6_report
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from eval.grade import wilson
from eval.phase4.policy_lib import noninferior
from eval.task_schema import CATEGORIES, load_tasks

ROOT = Path(__file__).resolve().parent
P6 = ROOT / "results" / "phase6"
K = P6 / "kaggle_out" / "phase6_out"
CPU_RATE, GPU_RATE = 0.05, 0.35  # USD per hour (D5)
GPU_RUNS = ["router_main_gpu_run1", "router_main_gpu_run2", "router_main_gpu_run3"]
ALL_ROUTER = [*GPU_RUNS, "router_main_cpu_check", "router_gpu_server_run1"]
B1R, B2R = [f"B1_run{i}" for i in (1, 2, 3)], [f"B2_run{i}" for i in (1, 2, 3)]
MIXES = {  # D6; the code-heavy mix is my definition (flagged in the report)
    "equal": {c: 1 / 8 for c in CATEGORIES},
    "support desk": {"sentiment": .25, "summarisation": .25, "ner": .25, "factual": .25},
    "developer tools": {"code_gen": .35, "code_debug": .35, "factual": .10, "math": .10, "logic": .10},
    "analyst": {"math": 1 / 3, "logic": 1 / 3, "factual": 1 / 3},
}


def load():
    rows = [json.loads(l) for l in (P6 / "graded_scores.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    S = defaultdict(dict)
    for r in rows:
        S[r["system"]][r["task_id"]] = r
    return S


def ok(r):
    return r["passed"] is True


def acc(rows, cat=None):
    rs = [r for r in rows.values() if cat is None or r["category"] == cat]
    return sum(ok(r) for r in rs) / len(rs)


def cost(rows, cat=None):
    return sum(r["cost_usd"] or 0 for r in rows.values() if cat is None or r["category"] == cat)


def attempts(r):
    return [s for s in (r.get("trace") or []) if s["step"] in ("local", "translator")]


def hw_costs(S):
    """With-hardware cost per router system (D5). CPU check: measured latency x $0.05/h. Main-policy GPU runs: each local attempt priced with the
    CPU-check latency of the same (task, step, model), else that (step, model)'s CPU median. GPU-server run: measured T4 latency x $0.35/h."""
    lat, med = {}, defaultdict(list)
    for tid, r in S["router_main_cpu_check"].items():
        for s in attempts(r):
            lat[(tid, s["step"], s["model"])] = s.get("latency_ms") or 0
            med[(s["step"], s["model"])].append(s.get("latency_ms") or 0)
    med = {k: st.median(v) for k, v in med.items()}
    out = {}
    for name in ALL_ROUTER:
        tot = 0.0
        for tid, r in S[name].items():
            for s in attempts(r):
                if name == "router_gpu_server_run1":
                    ms_, rate = s.get("latency_ms") or 0, GPU_RATE
                elif name == "router_main_cpu_check":
                    ms_, rate = s.get("latency_ms") or 0, CPU_RATE
                else:
                    ms_, rate = lat.get((tid, s["step"], s["model"]), med.get((s["step"], s["model"]), 0)), CPU_RATE
                tot += ms_ / 3.6e6 * rate
        out[name] = tot
    return out


def ms(xs, f="{:.1%}"):
    return f"{f.format(st.mean(xs))} ± {f.format(st.pstdev(xs))}"


def sav(c, b):
    return 1 - c / b


def main():
    S = load()
    ids = sorted(t["id"] for t in load_tasks(ROOT / "tasks_8cat.json") if t["split"] == "test")
    names = sorted(S)
    assert len(ids) == 160 and all(len(S[n]) == 160 for n in names) and len(names) == 11, {n: len(S[n]) for n in names}
    HW = hw_costs(S)
    R, L = {}, []
    w = L.append
    ncat = {c: sum(1 for r in S["B1_run1"].values() if r["category"] == c) for c in CATEGORIES}

    # ------------------------------------------------------------ 1 headline
    H = {"Router (main policy, GPU)": GPU_RUNS, "B1 always kimi-k3p1-pro": B1R, "B2 always deepseek-v4p1-flash": B2R}
    A = {k: [acc(S[r]) for r in v] for k, v in H.items()}
    C = {k: [cost(S[r]) for r in v] for k, v in H.items()}
    ra, b1a, b2a = (st.mean(A[k]) for k in H)
    rc, b1c, b2c = (st.mean(C[k]) for k in H)
    rhw = st.mean(HW[r] for r in GPU_RUNS)
    R["headline"] = {k: {"acc_runs": A[k], "cost_runs": C[k]} for k in H}
    R["savings"] = dict(marginal_vs_B1=sav(rc, b1c), marginal_vs_B2=sav(rc, b2c), hw_vs_B1=sav(rc + rhw, b1c), hw_vs_B2=sav(rc + rhw, b2c))
    w("# Phase 6 final report: router vs B1 vs B2 on the 160 held-out test tasks\n")
    w("Frozen at tag `phase6-frozen` (see `FREEZE.md`; no post-freeze fix was needed, so nothing was re-run). All numbers come from `graded_scores.jsonl` "
      "(frozen graders and judge: GLM 5.3 Flash, Qwen for GLM's own answers) and the raw files `answers_b1b2.jsonl` and `kaggle_out/phase6_out/*`. "
      "Costs are tokens x list price (Hyde GLM and Gemini are priced at list although free to us); cash spend is in section 11. "
      "B1 and B2 get the true category's system prompt (as in Phase 3); the router classifies by itself.\n")
    w("## 1. Headline\n")
    w("Mean ± standard deviation over 3 runs (D3). Wilson 95% CI is for the mean accuracy over n = 160 tasks.\n")
    w("| System | Accuracy (3 runs) | Wilson 95% CI | Run values | Cost, 160 tasks (list) | Cost per 1000 requests |\n|---|---|---|---|---|---|")
    for k in H:
        lo, hi = wilson(round(st.mean(A[k]) * 160), 160)
        w(f"| {k} | {ms(A[k])} | {lo:.1%} to {hi:.1%} | {', '.join(f'{x:.1%}' for x in A[k])} | ${st.mean(C[k]):.4f} | ${st.mean(C[k]) / 160 * 1000:.2f} |")
    w("\n| Savings of the router | vs B1 | vs B2 |\n|---|---|---|")
    w(f"| **Marginal** (local = $0) | **{R['savings']['marginal_vs_B1']:.1%}** | **{R['savings']['marginal_vs_B2']:.1%}** |")
    w(f"| **With hardware** (CPU instance $0.05/h x CPU-check latency of each local attempt: +${rhw:.4f} per 160 tasks) | "
      f"{R['savings']['hw_vs_B1']:.1%} | {R['savings']['hw_vs_B2']:.1%} |")
    w(f"\nAccuracy difference router - B1: {100 * (ra - b1a):+.1f} points; router - B2: {100 * (ra - b2a):+.1f} points. "
      f"B1 costs {b1c / b2c:.1f}x B2.\n")

    # ------------------------------------------------------------ 2 guardrail
    w("## 2. Guardrail re-check on test (D12)\n")
    w("Rule: the router is at most 3 points less accurate than B1 at 95% confidence (one-sided paired bootstrap over the 160 tasks, 10,000 resamples, "
      "`eval/phase4/policy_lib.noninferior`). Reported as it came out.\n")
    w("| Comparison | Router acc | Reference acc | Observed diff | One-sided 95% lower bound | Result |\n|---|---|---|---|---|---|")
    vec = lambda n: np.array([1.0 if ok(S[n][i]) else 0.0 for i in ids])
    mean_vec = lambda runs: np.mean([vec(r) for r in runs], 0)
    pairs = [(f"router run {i + 1} vs B1 run {i + 1}", vec(GPU_RUNS[i]), vec(B1R[i])) for i in range(3)]
    pairs.append(("**router mean of 3 vs B1 mean of 3**", mean_vec(GPU_RUNS), mean_vec(B1R)))
    pairs += [(f"router run {i + 1} vs B2 run {i + 1} (informational)", vec(GPU_RUNS[i]), vec(B2R[i])) for i in range(3)]
    pairs += [(f"B2 run {i + 1} vs B1 run {i + 1} (B2's own D12 test)", vec(B2R[i]), vec(B1R[i])) for i in range(3)]
    G = {}
    for lab, a, b in pairs:
        p, lo, d = noninferior(a, b)
        G[lab.strip("*")] = dict(passed=bool(p), lower=lo, diff=d, a=float(a.mean()), b=float(b.mean()))
        w(f"| {lab} | {a.mean():.1%} | {b.mean():.1%} | {100 * d:+.1f} pts | {100 * lo:+.1f} pts | **{'PASS' if p else 'FAIL'}** |")
    w("")
    R["guardrail"] = G
    gmain = G["router mean of 3 vs B1 mean of 3"]

    # ------------------------------------------------------------ 3 per category
    w("## 3. Per-category results\n")
    w("Accuracy and cost = mean over the 3 runs; cost is the category's total over its test tasks (list price, marginal).\n")
    w("| Category | n | Router acc | B1 acc | B2 acc | Router cost | B1 cost | B2 cost | Savings vs B1 | Savings vs B2 |\n|---|---|---|---|---|---|---|---|---|---|")
    PC = {}
    for c in CATEGORIES:
        f = lambda runs: (st.mean(acc(S[r], c) for r in runs), st.mean(cost(S[r], c) for r in runs))
        (a1, c1), (a2, c2), (a3, c3) = f(GPU_RUNS), f(B1R), f(B2R)
        PC[c] = dict(n=ncat[c], router=(a1, c1), b1=(a2, c2), b2=(a3, c3))
        w(f"| {c} | {ncat[c]} | {a1:.1%} | {a2:.1%} | {a3:.1%} | ${c1:.4f} | ${c2:.4f} | ${c3:.4f} | {sav(c1, c2):.1%} | {sav(c1, c3):.1%} |")
    w("")
    R["per_category"] = PC

    # ------------------------------------------------------------ 4 mixes
    w("## 4. Traffic mixes (D6)\n")
    w("Per-category means re-weighted. Shares: equal = 1/8 each; support desk = sentiment, summarisation, NER, factual 25% each; developer tools = "
      "code_gen 35%, code_debug 35%, factual / math / logic 10% each (my definition of 'code-heavy'); analyst = math, logic, factual 1/3 each. "
      "Cost is per request (list price, marginal).\n")
    w("| Mix | Router acc | B1 acc | B2 acc | Router $/req | B1 $/req | B2 $/req | Savings vs B1 | Savings vs B2 |\n|---|---|---|---|---|---|---|---|---|")
    MX = {}
    for m, sh in MIXES.items():
        accs = {k: sum(s * PC[c][k][0] for c, s in sh.items()) for k in ("router", "b1", "b2")}
        cs = {k: sum(s * PC[c][k][1] / PC[c]["n"] for c, s in sh.items()) for k in ("router", "b1", "b2")}
        MX[m] = dict(vs_b1=sav(cs["router"], cs["b1"]), vs_b2=sav(cs["router"], cs["b2"]), acc=accs, cost=cs)
        w(f"| {m} | {accs['router']:.1%} | {accs['b1']:.1%} | {accs['b2']:.1%} | ${cs['router']:.5f} | ${cs['b1']:.5f} | ${cs['b2']:.5f} | {MX[m]['vs_b1']:.1%} | {MX[m]['vs_b2']:.1%} |")
    v1, v2 = [x["vs_b1"] for x in MX.values()], [x["vs_b2"] for x in MX.values()]
    w(f"\nRange of savings across the mixes: vs B1 **{min(v1):.1%} to {max(v1):.1%}**, vs B2 {min(v2):.1%} to {max(v2):.1%}.\n")
    R["mixes"] = MX

    # ------------------------------------------------------------ 5 paths
    w("## 5. Paths, escalation, zero-API-cost categories\n")
    w("| Run | solver | local | api (incl. escalated and out-of-scope) | of which escalated after a failed local/translator step | predicted out-of-scope | accuracy |\n|---|---|---|---|---|---|---|")
    PATH = {}
    for n in ALL_ROUTER:
        rs = S[n].values()
        c = Counter(r["layer"] for r in rs)
        PATH[n] = dict(solver=c["solver"], local=c["local"], api=c["api"], escalated=sum(1 for r in rs if r["escalated"]),
                       oos=sum(1 for r in rs if r["pred_category"] == "out_of_scope"))
        w(f"| {n} | {c['solver']} | {c['local']} | {c['api']} | {PATH[n]['escalated']} | {PATH[n]['oos']} | {acc(S[n]):.1%} |")
    R["paths"] = PATH
    w("\n**Strict rule for \"N of 8 at 0 API cost\":** a category counts only if **every** test task of that category (by true category) was answered by a solver or a "
      "local model (final layer solver or local, never api) in **all 3** main-policy GPU runs.\n")
    w("| Category | n | share answered at $0 (run 1 / 2 / 3) | Counts under the strict rule |\n|---|---|---|---|")
    zero = []
    for c in CATEGORIES:
        sh = [sum(x["layer"] in ("solver", "local") for x in S[r].values() if x["category"] == c) / ncat[c] for r in GPU_RUNS]
        zero.append(all(s == 1.0 for s in sh))
        w(f"| {c} | {ncat[c]} | {' / '.join(f'{s:.0%}' for s in sh)} | {'**yes**' if zero[-1] else 'no'} |")
    w(f"\n**Strict count: {sum(zero)} of 8** categories at 0 API cost.\n")
    R["zero_api_strict"] = sum(zero)
    R["zero_api_categories"] = [c for c, z in zip(CATEGORIES, zero) if z]

    # ------------------------------------------------------------ 6 classifier etc.
    w("## 6. Classifier, solver and validator numbers (test split)\n")
    r1 = S["router_main_gpu_run1"]
    lab = lambda rs: {i: (x["pred_category"], x["pred_difficulty"]) for i, x in rs.items()}
    same = all(lab(S[n]) == lab(r1) for n in ALL_ROUTER)
    cat_ok = sum(x["pred_category"] == x["category"] for x in r1.values())
    oos = [x for x in r1.values() if x["pred_category"] == "out_of_scope"]
    typed = [x for x in r1.values() if x["pred_category"] == x["category"]]
    diff_ok = sum(x["pred_difficulty"] == x["difficulty"] for x in typed)
    lo, hi = wilson(cat_ok, 160)
    w(f"Labels are identical in all 5 router runs: {same}. Out-of-scope recall cannot be measured on the test split (it holds no out-of-scope prompts); only the false-out-of-scope rate.\n")
    w(f"- **Task-type accuracy:** {cat_ok}/160 = {cat_ok / 160:.1%} (Wilson {lo:.1%} to {hi:.1%}). In-scope tasks predicted out-of-scope (counted wrong, sent to B2): {len(oos)} ({len(oos) / 160:.1%}).")
    ws = Counter((x["category"], x["pred_category"]) for x in r1.values() if x["pred_category"] != x["category"])
    w("- Confusions (true -> predicted): " + (", ".join(f"{a}->{b} x{n}" for (a, b), n in ws.most_common()) or "none") + ".")
    for src in ("rule", "embedding", "embedding-threshold"):
        sel = [x for x in r1.values() if x["label_source"] == src]
        if sel:
            w(f"- Label source `{src}`: {len(sel)} tasks, category accuracy {sum(x['pred_category'] == x['category'] for x in sel) / len(sel):.1%}.")
    lo, hi = wilson(diff_ok, len(typed))
    w(f"- **Difficulty accuracy** (on the {len(typed)} tasks with the right category): {diff_ok}/{len(typed)} = {diff_ok / len(typed):.1%} (Wilson {lo:.1%} to {hi:.1%}).\n")
    R["classifier"] = dict(cat_acc=cat_ok / 160, oos_false=len(oos), diff_acc=diff_ok / len(typed), same_labels=same)

    w("**Solvers (math and logic).** Coverage = share of math+logic tasks whose final answer came from the solver layer; precision = share of those correct. "
      "'Via translator' = the D13 local-model translator produced the input of the Python solver.\n")
    w("| Run | math+logic tasks | solver answers (coverage) | correct (precision) | via translator | pure-Python parser |\n|---|---|---|---|---|---|")
    SOL = {}
    for n in ALL_ROUTER:
        ml = [x for x in S[n].values() if x["category"] in ("math", "logic")]
        sv = [x for x in ml if x["layer"] == "solver"]
        tr = [x for x in sv if any(s["step"] == "translator" and s["ok"] for s in x["trace"])]
        k = sum(ok(x) for x in sv)
        SOL[n] = dict(n=len(ml), solver=len(sv), correct=k, translator=len(tr))
        w(f"| {n} | {len(ml)} | {len(sv)} ({len(sv) / len(ml):.1%}) | {k}/{len(sv)} ({k / max(1, len(sv)):.1%}) | {len(tr)} | {len(sv) - len(tr)} |")
    R["solvers"] = SOL
    w("\nAll solver answers on test came through the D13 translator; the pure-Python parser deferred on every math/logic test task (its recipes did not match the unseen phrasings; "
      "reasons are in each run's trace), so the solver layer answered 17.5% of math+logic with 100% precision.")
    w("\n**Validators and local answers.** Local attempts (every `local` trace step) split into accepted, rejected by a validator and timed out (30 s budget). "
      "A validator 'catch rate' on wrong local answers cannot be computed: rejected answers are not stored or graded. The observable numbers are the "
      "rejection share and the precision of accepted local answers (a wrong accepted answer is a validator miss).\n")
    w("| Run | local attempts | accepted | rejected by validator | timed out | other error | accepted & correct | accepted & wrong (misses) |\n|---|---|---|---|---|---|---|---|")
    VAL = {}
    for n in ALL_ROUTER:
        steps = [(x, s) for x in S[n].values() for s in x["trace"] if s["step"] == "local"]
        acc_ = [x for x, s in steps if s["ok"]]
        to = sum(1 for x, s in steps if not s["ok"] and (s.get("why") or "") == "timeout")
        er = sum(1 for x, s in steps if not s["ok"] and s.get("error") and (s.get("why") or "") != "timeout")
        rej = sum(1 for x, s in steps if not s["ok"]) - to - er
        good = sum(ok(x) for x in acc_)
        VAL[n] = dict(attempts=len(steps), accepted=len(acc_), rejected=rej, timeout=to, other_err=er, correct=good)
        w(f"| {n} | {len(steps)} | {len(acc_)} | {rej} | {to} | {er} | {good} | {len(acc_) - good} |")
    R["validators"] = VAL
    w("\n**Every wrong answer whose final layer was a local model or a solver:**\n")
    w("| System | Task | True category | Layer | Model | Grader detail |\n|---|---|---|---|---|---|")
    nw = 0
    for n in ALL_ROUTER:
        for i in ids:
            x = S[n][i]
            if x["layer"] in ("local", "solver") and not ok(x):
                nw += 1
                w(f"| {n} | {i} | {x['category']} | {x['layer']} | {x['answered_by']} | {str(x['detail'])[:90].replace('|', '/')} |")
    if not nw:
        w("| (none) | | | | | |")
    R["wrong_local_or_solver"] = nw
    w("\n**All wrong answers by final layer** (3 main GPU runs pooled): " + ", ".join(
        f"{lay} {sum(1 for r in GPU_RUNS for x in S[r].values() if x['layer'] == lay and not ok(x))}/{sum(1 for r in GPU_RUNS for x in S[r].values() if x['layer'] == lay)}"
        for lay in ("solver", "local", "api")) + ".\n")

    # ------------------------------------------------------------ 7 variation
    w("## 7. Why the API count differs across the 3 GPU runs (96 / 90 / 89)\n")
    RAW = {r: {x["id"]: x for x in json.load(open(K / r / "results.json", encoding="utf-8"))["results"]}
           for r in ("main_gpu_run1", "main_gpu_run2", "main_gpu_run3", "main_cpu_check", "gpu_server_run1")}
    order = list(RAW["main_gpu_run1"])
    w("| Run | api | local | solver | local timeouts | validator rejections | wall clock |\n|---|---|---|---|---|---|---|")
    to_tasks = {}
    for r in ("main_gpu_run1", "main_gpu_run2", "main_gpu_run3"):
        c = Counter(x["layer"] for x in RAW[r].values())
        to_tasks[r] = [(order.index(i), s["model"], s.get("latency_ms")) for i, x in RAW[r].items() for s in x["trace"]
                       if s["step"] == "local" and (s.get("why") or "") == "timeout"]
        rej = sum(1 for x in RAW[r].values() for s in x["trace"] if s["step"] == "local" and not s["ok"] and (s.get("why") or "") != "timeout")
        el = json.load(open(K / r / "results.json", encoding="utf-8"))["meta"]["elapsed_s"]
        w(f"| {r} | {c['api']} | {c['local']} | {c['solver']} | {len(to_tasks[r])} | {rej} | {el:.0f} s |")
    firsts = {}
    for i, x in RAW["main_gpu_run1"].items():
        for s in x["trace"]:
            if s["step"] == "local":
                firsts.setdefault(s["model"], order.index(i))
    route = lambda r, i: (RAW[r][i]["layer"], RAW[r][i]["model"])
    dd = {(a, b): [i for i in order if route(a, i) != route(b, i)] for a, b in (("main_gpu_run1", "main_gpu_run2"), ("main_gpu_run1", "main_gpu_run3"), ("main_gpu_run2", "main_gpu_run3"))}
    w(f"\nRun 1 had **{len(to_tasks['main_gpu_run1'])} local timeouts** (each used the whole 30 s budget, so the task was escalated to the API); runs 2 and 3 had "
      f"**{len(to_tasks['main_gpu_run2'])} and {len(to_tasks['main_gpu_run3'])}**. Run 1 timeouts (position of the task in the file, model, ms): {to_tasks['main_gpu_run1']}. "
      f"Position of the first use of each model in run 1: {firsts}. The timeouts sit at the first uses of each model (and at model swaps), where Ollama has to load the "
      "weights after a fresh `ollama pull`; by run 2 they are cached and no call came close to the budget. Run 1 also took about twice as long on the wall clock. "
      "So the gap between run 1 and runs 2/3 is a **cold-start effect**, not model nondeterminism.\n")
    w(f"Final-route differences: run 1 vs 2 = {len(dd[('main_gpu_run1', 'main_gpu_run2')])} tasks, run 1 vs 3 = {len(dd[('main_gpu_run1', 'main_gpu_run3')])}, "
      f"run 2 vs 3 = {len(dd[('main_gpu_run2', 'main_gpu_run3')])}. The remaining difference between runs 2 and 3 (and the extra validator rejection in run 2) is GPU sampling, which is "
      "not bit-exact even at temperature 0. The cold start is a real property of a freshly started server, so run 1 stays in the 3-run mean ± spread; the effect is shown, not removed.\n")
    R["variation"] = dict(timeouts={r: len(v) for r, v in to_tasks.items()}, diffs={f"{a}|{b}": len(v) for (a, b), v in dd.items()})

    # ------------------------------------------------------------ 8 cpu
    w("## 8. CPU-deployment check (1 run: CPU only, 2 threads, 30 s budget)\n")
    cpu, g2 = S["router_main_cpu_check"], S["router_main_gpu_run2"]
    lat = lambda rs: sorted((x["latency_ms"] or 0) / 1000 for x in rs.values())
    pc = lambda a, q: a[min(len(a) - 1, int(q * len(a)))]
    lc, lg = lat(cpu), lat(g2)
    cputo = sum(1 for x in cpu.values() for s in x["trace"] if s["step"] in ("local", "translator") and (s.get("why") or "") == "timeout")
    w("| | CPU check | main GPU run 2 (warm) | main GPU mean of 3 |\n|---|---|---|---|")
    w(f"| Accuracy | {acc(cpu):.1%} | {acc(g2):.1%} | {ra:.1%} |")
    pm = lambda k: st.mean(PATH[r][k] for r in GPU_RUNS)
    w(f"| solver / local / api | {PATH['router_main_cpu_check']['solver']} / {PATH['router_main_cpu_check']['local']} / {PATH['router_main_cpu_check']['api']} | "
      f"{PATH['router_main_gpu_run2']['solver']} / {PATH['router_main_gpu_run2']['local']} / {PATH['router_main_gpu_run2']['api']} | {pm('solver'):.0f} / {pm('local'):.0f} / {pm('api'):.0f} |")
    w(f"| Cost (list, marginal) | ${cost(cpu):.4f} | ${cost(g2):.4f} | ${rc:.4f} |")
    w(f"| Cost with hardware (CPU $0.05/h) | ${cost(cpu) + HW['router_main_cpu_check']:.4f} | ${cost(g2) + HW['router_main_gpu_run2']:.4f} | ${rc + rhw:.4f} |")
    w(f"| Latency p50 / p95 / max (s per request) | {pc(lc, .5):.1f} / {pc(lc, .95):.1f} / {lc[-1]:.1f} | {pc(lg, .5):.1f} / {pc(lg, .95):.1f} / {lg[-1]:.1f} | |")
    w(f"| Local or translator steps that hit the 30 s budget | {cputo} | {sum(1 for x in g2.values() for s in attempts(x) if (s.get('why') or '') == 'timeout')} | |")
    def step_lat(rs):
        v = sorted((s.get("latency_ms") or 0) / 1000 for x in rs.values() for s in x["trace"] if s["step"] == "local" and (s.get("why") or "") != "timeout")
        return f"{pc(v, .5):.1f} / {pc(v, .95):.1f}"
    w(f"| Local step latency p50 / p95 (s, timeouts excluded) | {step_lat(cpu)} | {step_lat(g2)} | |")
    cc, ch = cost(cpu), cost(cpu) + HW["router_main_cpu_check"]
    w(f"| Savings vs B1 / B2, marginal | {sav(cc, b1c):.1%} / {sav(cc, b2c):.1%} | | {sav(rc, b1c):.1%} / {sav(rc, b2c):.1%} |")
    w(f"| Savings vs B1 / B2, with hardware | {sav(ch, b1c):.1%} / {sav(ch, b2c):.1%} | | {sav(rc + rhw, b1c):.1%} / {sav(rc + rhw, b2c):.1%} |")
    w("\nRequest latency in `router.run` includes queueing: 8 requests run concurrently but local-model calls are serialised (one at a time), so a request waits for the "
      "local lane. The per-step local latency row is the cleaner per-call number; request latency is a batch-throughput figure, not what a single user on a CPU box would see.")
    p_, lo_, d_ = noninferior(vec("router_main_cpu_check"), mean_vec(B1R))
    w(f"\nGuardrail for the CPU check vs the B1 mean: diff {100 * d_:+.1f} pts, lower bound {100 * lo_:+.1f} pts, **{'PASS' if p_ else 'FAIL'}**. "
      "This run is the honest deployment number for a CPU-only box: the GPU runs overstate the local share, because local answers that take longer than 30 s on 2 CPU threads fall through to the API.\n")
    R["cpu"] = dict(acc=acc(cpu), cost=cc, hw=HW["router_main_cpu_check"], local=PATH["router_main_cpu_check"]["local"], guard=bool(p_),
                    sav_b1=sav(cc, b1c), sav_b1_hw=sav(ch, b1c), p50=pc(lc, .5), p95=pc(lc, .95))

    # ------------------------------------------------------------ 9 gpu server
    w("## 9. GPU-server scenario (`routing_policy_gpu_server.json`, 1 run on a T4)\n")
    gs = S["router_gpu_server_run1"]
    gcost, ghw = cost(gs), HW["router_gpu_server_run1"]
    w("| | GPU-server router | main router (GPU mean) | B1 | B2 |\n|---|---|---|---|---|")
    w(f"| Accuracy | {acc(gs):.1%} | {ra:.1%} | {b1a:.1%} | {b2a:.1%} |")
    w(f"| solver / local / api | {PATH['router_gpu_server_run1']['solver']} / {PATH['router_gpu_server_run1']['local']} / {PATH['router_gpu_server_run1']['api']} | "
      f"{pm('solver'):.0f} / {pm('local'):.0f} / {pm('api'):.0f} | 0 / 0 / 160 | 0 / 0 / 160 |")
    w(f"| API cost, 160 tasks (list) | ${gcost:.4f} | ${rc:.4f} | ${b1c:.4f} | ${b2c:.4f} |")
    w(f"| + hardware (T4 $0.35/h x measured local latency = ${ghw:.4f}) | ${gcost + ghw:.4f} | ${rc + rhw:.4f} (CPU-priced) | | |")
    w(f"| Savings vs B1, marginal / with hardware | {sav(gcost, b1c):.1%} / {sav(gcost + ghw, b1c):.1%} | {sav(rc, b1c):.1%} / {sav(rc + rhw, b1c):.1%} | | |")
    w(f"| Savings vs B2, marginal / with hardware | {sav(gcost, b2c):.1%} / {sav(gcost + ghw, b2c):.1%} | {sav(rc, b2c):.1%} / {sav(rc + rhw, b2c):.1%} | | |")
    p_, lo_, d_ = noninferior(vec("router_gpu_server_run1"), mean_vec(B1R))
    w(f"\nGuardrail vs the B1 mean: diff {100 * d_:+.1f} pts, lower bound {100 * lo_:+.1f} pts, **{'PASS' if p_ else 'FAIL'}**. Single run, so no spread. "
      "The hardware price counts only the GPU seconds used by local steps; an always-on box costs far more per request at low traffic.\n")
    R["gpu_server"] = dict(acc=acc(gs), cost=gcost, hw=ghw, guard=bool(p_), sav_b1=sav(gcost, b1c), sav_b1_hw=sav(gcost + ghw, b1c))

    # ------------------------------------------------------------ 10 data quality
    w("## 10. Data quality\n")
    nj = {n: sum(1 for r in S[n].values() if r["passed"] is None) for n in names}
    lf = {n: sum(1 for r in S[n].values() if r.get("language_fail")) for n in names}
    up = {n: sum(1 for r in S[n].values() if r.get("unparsed")) for n in names}
    w(f"- Judge returned no verdict (counted wrong): {sum(nj.values())} of {len(names) * 160} answers.")
    w(f"- Non-English-script failures (D10): {sum(lf.values())} ({', '.join(f'{n} {v}' for n, v in lf.items() if v) or 'none'}).")
    w(f"- Grader could not parse the answer: {sum(up.values())} ({', '.join(f'{n} {v}' for n, v in up.items() if v) or 'none'}).")
    w(f"- Call errors: {sum(1 for n in names for r in S[n].values() if str(r['detail']).startswith('call error'))}.\n")

    # ------------------------------------------------------------ 11 spend
    w("## 11. Spend\n")
    b_cash = sum(cost(S[r]) for r in B1R + B2R)
    kst = json.load(open(K / "status.json"))
    w(f"- B1 + B2 on the laptop (Fireworks): ${b_cash:.4f}. Router on Kaggle, 5 runs (Fireworks only): ${kst['fireworks_spend_usd']:.4f}. "
      "Judge: GLM via Hyde is free; Qwen (Fireworks) is used only for GLM-answered factual/summary items (see `grade_run.log` / `judge_cache.jsonl`). Phase cap: $3.\n")

    # ------------------------------------------------------------ plots
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for (lab, runs), col in zip({"Router main (GPU)": GPU_RUNS, "B1 kimi-k3p1-pro": B1R, "B2 deepseek-v4p1-flash": B2R}.items(), ("tab:green", "tab:red", "tab:blue")):
        ax.scatter([cost(S[r]) / 160 * 1000 for r in runs], [100 * acc(S[r]) for r in runs], c=col, label=lab, s=40)
    for lab, n, col, mk in (("Router CPU check", "router_main_cpu_check", "tab:olive", "s"), ("Router GPU-server", "router_gpu_server_run1", "tab:purple", "^")):
        ax.scatter([cost(S[n]) / 160 * 1000], [100 * acc(S[n])], c=col, label=lab, s=60, marker=mk)
    ax.set_xlabel("API cost per 1000 requests (USD, list price, marginal)")
    ax.set_ylabel("Accuracy on 160 test tasks (%)")
    ax.set_title("Accuracy vs cost")
    ax.legend(fontsize=8)
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(P6 / "plot_accuracy_vs_cost.png", dpi=130)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(CATEGORIES))
    for j, (lab, key, col) in enumerate((("Router", "router", "tab:green"), ("B1", "b1", "tab:red"), ("B2", "b2", "tab:blue"))):
        ax.bar(x + (j - 1) * .27, [PC[c][key][1] / PC[c]["n"] * 1000 for c in CATEGORIES], .27, label=lab, color=col)
    ax.set_xticks(x)
    ax.set_xticklabels(CATEGORIES, rotation=30, ha="right")
    ax.set_ylabel("USD per 1000 requests (list price)")
    ax.set_title("API cost by category (mean of 3 runs)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(P6 / "plot_cost_by_category.png", dpi=130)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    bot = np.zeros(len(ALL_ROUTER))
    for lay, col in (("solver", "tab:green"), ("local", "tab:olive"), ("api", "tab:red")):
        v = np.array([PATH[n][lay] for n in ALL_ROUTER])
        ax.bar([n.replace("router_", "") for n in ALL_ROUTER], v, bottom=bot, label=lay, color=col)
        bot += v
    ax.set_ylabel("tasks (of 160)")
    ax.set_title("Final answering layer per run")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(P6 / "plot_path_shares.png", dpi=130)
    plt.close(fig)
    w("## 12. Plots\n")
    w("![accuracy vs cost](plot_accuracy_vs_cost.png)\n\n![cost by category](plot_cost_by_category.png)\n\n![path shares](plot_path_shares.png)\n")

    # ------------------------------------------------------------ 13 headline summary
    w("## 13. Headline numbers\n")
    w("| Question | Measured on the held-out test set |\n|---|---|")
    w(f"| Cost saving | **{R['savings']['marginal_vs_B1']:.1%}** vs B1 (marginal), {R['savings']['hw_vs_B1']:.1%} with hardware; "
      f"{R['savings']['marginal_vs_B2']:.1%} vs the cheaper B2; traffic mixes {min(v1):.0%} to {max(v1):.0%} vs B1; CPU-only deployment {sav(cc, b1c):.1%} (marginal) |")
    w(f"| Accuracy | router {ms(A['Router (main policy, GPU)'])} vs B1 {ms(A['B1 always kimi-k3p1-pro'])}; guardrail vs B1 "
      f"**{'passed' if gmain['passed'] else 'FAILED'}** (lower bound {100 * gmain['lower']:+.1f} pts, margin -3) |")
    w("| Scope of the evaluation | 16 models x 8 categories on 240 dev tasks (Phase 3); policy derived on dev only; final test on 160 held-out tasks |")
    w(f"| Categories at 0 API cost (strict rule) | **{sum(zero)} of 8** ({', '.join(R['zero_api_categories']) or 'none'}); per-run shares in section 5 |")
    w("\nNothing above was tuned after the test split was opened.\n")

    (P6 / "final_report.md").write_text("\n".join(L), encoding="utf-8")
    (P6 / "final_numbers.json").write_text(json.dumps(R, indent=1, default=float), encoding="utf-8")
    print("wrote final_report.md")


if __name__ == "__main__":
    main()
