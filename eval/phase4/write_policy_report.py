"""Writes eval/results/phase4/policy_report.md from routing_policy*.json, policy_replay.json, baselines.json and the other Phase 4 result files."""
import json

from router.data import ROOT

D = ROOT / "eval" / "results" / "phase4"


def j(name):
    return json.loads((D / name).read_text(encoding="utf-8"))


def pct(x):
    return f"{x:.1%}"


def paths(s):
    p = s["paths"]
    return f"{p.get('solver',0)} / {p.get('local',0)} / {p.get('escalated',0)} / {p.get('api',0)}"


def policy_section(L, title, fname, pol):
    g = pol["guardrail"]
    f = g["final"]
    L += [f"### {title} (`{fname}`)", "",
          f"Guardrail (D12, replayed on the out-of-fold predicted labels): router at most {g['margin']*100:.0f} points worse than B1 at {g['confidence']:.0%}, "
          f"one-sided paired bootstrap over 240 tasks. **Final: {'PASSED' if f['passed'] else 'FAILED'}** - router {pct(f['router_accuracy'])} vs B1 "
          f"{pct(f['b1_accuracy'])}, lower bound of the difference {f['lower_bound']:+.3f}. Solvers enabled: {pol['solvers_enabled']}.", "",
          "| cell | model | kind | n | B1 misses | reason (cell rule on true labels) |", "|---|---|---|---|---|---|"]
    for cell, c in sorted(pol["cells"].items()):
        L.append(f"| {cell} | {c['model']} | {c['kind']} | {c.get('n','')} | {c.get('b1_misses','')} | {c['reason']} |")
    L.append(f"| out of scope | {pol['out_of_scope']['model']} | api | | | {pol['out_of_scope']['reason']} |")
    L += ["", "Guardrail log (every step):", "", "| step | action | passed | lower bound | router acc |", "|---|---|---|---|---|"]
    for s in g["steps"]:
        L.append(f"| {s['step']} | {s['action']} | {s['passed']} | {s.get('lower_bound', float('nan')):+.3f} | {pct(s.get('router_accuracy', float('nan')))} |")
    handed = [c for c, v in pol["cells"].items() if "HANDED BACK" in v["reason"]]
    L += ["", f"Cells handed back: {', '.join(sorted(handed)) if handed else 'none'}.", ""]


def main():
    base, rep = j("baselines.json"), j("policy_replay.json")
    b1, b2 = base["B1"], base["B2"]
    c1, c2 = b1["cost_usd"], b2["cost_usd"]
    V = rep["variants"]
    L = ["# Phase 4 policy report (dev split only, 240 tasks, API spend $0 - all numbers are replays of Phase 3 answers)", "",
         "## Baselines (D2, D12)", "",
         f"- **B1** = {b1['model']}: accuracy {pct(b1['accuracy'])}, cost ${c1:.4f} on the 240 dev tasks ({b1['rule']}).",
         f"- **B2** = {b2['model']}: accuracy {pct(b2['accuracy'])}, cost ${c2:.4f}; lower bound of (B2 - B1) = {b2['diff_vs_b1_lower_bound']:+.3f} "
         f"(passes the 3-point test). {b2['rule']}.", "",
         "## Labels used in the replay", "",
         "The router sees the classifiers' guesses in production, so the **official** replay and the guardrail use out-of-fold predicted labels: the category comes from "
         "the 5-fold CV hybrid task-type classifier and the difficulty from the fold's difficulty model (`predicted_labels.json`, written by `eval_difficulty.py`; every "
         "task is predicted by a model that did not train on it). The cell rule itself is derived on the true labels. Replays with the true labels are shown for reference only. "
         "A task predicted out-of-scope goes straight to B1.", ""]

    def table(tier, rows):
        out = ["| policy | accuracy | cost (USD) | vs B1 cost | vs B2 cost | solver / local / escalated / API |", "|---|---|---|---|---|---|",
               f"| always B1 | {pct(rep['always_b1']['accuracy'])} | {c1:.4f} | 1.00x | {c1/c2:.2f}x | - |",
               f"| always B2 | {pct(rep['always_b2']['accuracy'])} | {c2:.4f} | {c2/c1:.2f}x | 1.00x | - |"]
        for lab, key, extra in rows:
            v = V[key]
            for lbl, nm in (("predicted", "predicted labels (official)"), ("true", "true labels (reference)")):
                for sol, sn in (("with_solvers", "solvers on"), ("without_solvers", "solvers off")):
                    if lbl == "true" and sol == "without_solvers":
                        continue
                    s = v[f"{lbl}_{sol}"]
                    out.append(f"| {lab}, {nm}, {sn} | {pct(s['accuracy'])} | {s['cost_usd']:.4f} | {s['cost_usd']/c1:.2f}x | {s['cost_usd']/c2:.2f}x | {paths(s)} |")
        return out

    L += ["## Main router: 8 laptop-class local models + APIs (GPU-server models excluded, D1/D11)", "",
          "Local options: " + ", ".join(m for m in rep["main_options"] if ":" in m) + ".", ""]
    L += table("main", [("specified policy (`raw`)", "main/raw", ""), ("cascade variant", "main/cascade", "")]) + [""]
    r = V["main/raw"]["predicted_with_solvers"]
    L += [f"**Savings, specified policy, predicted labels:** {pct(1 - r['cost_usd']/c1)} cheaper than B1 (${c1 - r['cost_usd']:.4f} on the 240 tasks), "
          f"{(1 - r['cost_usd']/c2):+.1%} vs B2 (positive = cheaper than B2, negative = dearer); accuracy {r['accuracy'] - b1['accuracy']:+.1%} vs B1, {r['accuracy'] - b2['accuracy']:+.1%} vs B2.", ""]
    pth = r["paths"]
    L += [f"**Who answers (specified policy, predicted labels):** solvers {pth['solver']} ({pth['solver']/240:.0%}), local models {pth['local']} ({pth['local']/240:.0%}), "
          f"escalated to B2 after a validator rejection {pth['escalated']} ({pth['escalated']/240:.0%}), routed straight to an API model {pth['api']} ({pth['api']/240:.0%}). "
          f"So {(pth['solver']+pth['local'])/240:.0%} of the tasks are answered without any paid call.", "",
          "**Escalation target (D12 update, 2026-11-21):** validator-rejected local answers and out-of-scope prompts go to B2, not B1 (with B1 as escalation target the router cost more than always-B2). "
          "B1 stays the reference of the guardrail and the top of every cell's ladder, so cells can still be handed back to B1.", ""]
    L += ["`raw` = D12 cell rule on each option's own dev accuracy (the specified policy). `cascade` = same rule but local options are judged by their accuracy *with* "
          "validators and escalation, a variant for comparison.", ""]
    for title, fname in (("Policy table, specified policy", "routing_policy.json"), ("Policy table, cascade variant", "routing_policy_cascade.json")):
        policy_section(L, title, fname, j(fname))
    L += ["## Separate scenario: self-hosted GPU-server tier (gemma3:12b, phi4:14b, qwen2.5:14b)", "",
          "These three models are not part of the 16 (D1/D11). This scenario answers 'what if the company runs a GPU box?': the same policy search with them added as local options. "
          "Priced two ways (D5): **marginal $0** per local answer (the `cost` column) and **with hardware** = measured latency x $0.35/h (T4 instance), added for every attempt a "
          "GPU-tier model makes (including attempts that are then escalated). Guardrail on predicted labels as above.", "",
          "| policy | accuracy | API cost, marginal $0 | + GPU hardware | total with hardware | total vs B1 | total vs B2 | solver / local / escalated / API |", "|---|---|---|---|---|---|---|---|"]
    for lab, key in (("specified policy (`raw`)", "gpu_server/raw"), ("cascade variant", "gpu_server/cascade")):
        for lbl, nm in (("predicted", "predicted labels (official)"), ("true", "true labels (reference)")):
            s = V[key][f"{lbl}_with_solvers"]
            tot = s["cost_usd"] + s["hw_cost_usd"]
            L.append(f"| {lab}, {nm} | {pct(s['accuracy'])} | {s['cost_usd']:.4f} | {s['hw_cost_usd']:.4f} | {tot:.4f} | {tot/c1:.2f}x | {tot/c2:.2f}x | {paths(s)} |")
    L += ["", "Hardware cost counts only the latency of the three GPU-tier answers actually used in the replay; it ignores idle time, which a real server would also pay for.", ""]
    for title, fname in (("GPU-server policy table, specified policy", "routing_policy_gpu_server.json"),
                         ("GPU-server policy table, cascade variant", "routing_policy_gpu_server_cascade.json")):
        policy_section(L, title, fname, j(fname))
    L += ["## Solvers (see solver_report.md, translator_report.md)", "",
          "- Pure-Python solvers: 22/22 set-A dev tasks per category, 100% precision, 0% coverage on the unseen B + hand items (D13 was adopted for that reason).",
          "- D13 translators (dev math + logic, 5 local models): chosen math = phi3.5:3.8b, logic = gemma3:4b (precision 100% on the answered dev items). Combined "
          "path (pure-Python first, translator when it defers) answers 27/30 math and 22/30 logic dev items with no wrong answer. Unseen logic B + hand stays at "
          "0/8 answered with the chosen translator; unseen math gains 5/8. Several non-chosen translators gave wrong answers that passed the gates "
          "(e.g. gemma3:1b math 11/21 correct), so the gates alone do not guarantee precision; selection on precision is what protects the router. "
          "Selection used all 30 dev items per category, so these figures are optimistic until the Phase 6 test split.", "",
          "## Classifiers (see classifier_report.md, difficulty_report.md)", "",
          "- Task type, 5-fold CV on dev: rules 69.6%, MiniLM embeddings + logistic regression 96.7%, hybrid (default) 96.7%, LLM (free GLM) 99.6%.",
          "- Difficulty classifier: 75.4%. Predicted labels differ from the true ones on 8 tasks (category) and 62 tasks (difficulty) out of 240.",
          "- Out-of-scope detection and validator results are in classifier_report.md and validator_check.md.", "",
          "## Power analysis", "", "See power_analysis.md. D12 was adopted because the original per-cell bootstrap test had very low power at n = 15/30; "
          "the cell rule is now a count rule and the statistical guarantee is the whole-router guardrail above.", "",
          "## Caveats", "",
          "- Everything is measured on the dev split that was also used to choose the routes; the guardrail's confidence is for the dev tasks, not a promise for new tasks. "
          "The held-out test split in Phase 6 is the real check.",
          "- Cells have 15 tasks; one task is 6.7 points inside a cell."]
    (D / "policy_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote policy_report.md")


if __name__ == "__main__":
    main()
