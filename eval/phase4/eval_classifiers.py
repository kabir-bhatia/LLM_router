"""Evaluate the four task-type classifiers on the 240 dev prompts (5-fold stratified CV) and 30 OOS prompts.

- rules: hand-written, nothing learned -> evaluated once on all dev prompts (no folds needed, but optimistic: the author had
  seen some dev prompts).
- embedding LR: fit on 4 folds; the OOS threshold is chosen on the TRAINING folds only (inner 5-fold CV, flag at most 5% of in-scope
  prompts); the 30 OOS prompts are never trained on or used to pick the threshold.
- hybrid: strong rule first, else embedding LR.
- LLM: zero-shot, nothing learned.
"""
import router  # noqa: F401  (must come first: Windows platform.uname workaround; sklearn import hangs without it)
import json
import time
from collections import Counter

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from router.classify import CATEGORIES, LABELS, OOS, EmbeddingClassifier, hybrid_predict, pick_threshold, rule_classify
from router.data import ROOT, load_dev
from router.embeddings import embed

OUT = ROOT / "eval" / "results" / "phase4"
SEED = 20251120
BUDGET = 0.05


def confusion(true, pred, labels=LABELS):
    idx = {l: i for i, l in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)), int)
    for t, p in zip(true, pred):
        m[idx[t], idx[p if p in idx else OOS]] += 1
    return m


def md_conf(m, labels=LABELS):
    short = [l[:6] for l in labels]
    out = ["| true \\ pred | " + " | ".join(short) + " |", "|---|" + "---|" * len(labels)]
    for l, row in zip(labels, m):
        out.append(f"| {l} | " + " | ".join(str(int(x)) for x in row) + " |")
    return "\n".join(out)


def main():
    dev = load_dev()
    prompts = [t["prompt"] for t in dev]
    y = np.array([t["category"] for t in dev])
    oos = json.loads((ROOT / "eval" / "phase4" / "oos_prompts.json").read_text(encoding="utf-8"))["prompts"]
    X = embed(prompts)
    Xo = embed(oos)
    res = {}

    # (a) rules
    t0 = time.perf_counter()
    rp = [rule_classify(p) for p in prompts]
    rule_ms = (time.perf_counter() - t0) / len(prompts) * 1000
    ro = [rule_classify(p) for p in oos]
    rule_lab = [l if l is not None else "none" for l, _ in rp]
    fired = [i for i, (l, s) in enumerate(rp) if l is not None]
    strong = [i for i, (l, s) in enumerate(rp) if l is not None and s]
    res["rules"] = {
        "accuracy_all": float(np.mean([rule_lab[i] == y[i] for i in range(len(y))])),
        "coverage_any": len(fired) / len(y), "acc_when_fired": float(np.mean([rule_lab[i] == y[i] for i in fired])),
        "coverage_strong": len(strong) / len(y), "acc_when_strong": float(np.mean([rule_lab[i] == y[i] for i in strong])),
        "false_oos_dev": sum(l == OOS for l in rule_lab) / len(y),
        "oos_flagged": sum(l == OOS for l, _ in ro) / len(oos), "ms_per_prompt": rule_ms,
    }
    rule_pred_for_conf = [l if l is not None else OOS for l in rule_lab]  # an abstention shown in the OOS column
    res["rules"]["confusion_note"] = "abstentions are shown in the out_of_scope column"

    # (b) embedding and (c) hybrid, 5-fold CV
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    emb_pred = np.empty(len(y), dtype=object)
    emb_raw = np.empty(len(y), dtype=object)
    hyb_pred = np.empty(len(y), dtype=object)
    hyb_path = np.empty(len(y), dtype=object)
    oos_emb, oos_hyb, taus = [], [], []
    for tr, te in skf.split(X, y):
        clf = EmbeddingClassifier()
        inner = cross_val_predict(EmbeddingClassifier().lr, X[tr], y[tr], cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                                  method="predict_proba")
        tau = pick_threshold(inner.max(1), BUDGET)
        taus.append(tau)
        clf.fit(X[tr], y[tr])
        clf.threshold = tau
        lab, _ = clf.predict(X[te])
        emb_pred[te] = lab
        emb_raw[te] = clf.lr.classes_[clf.proba(X[te]).argmax(1)]
        hl, hp = hybrid_predict([prompts[i] for i in te], X[te], clf)
        hyb_pred[te] = hl
        hyb_path[te] = hp
        lo, _ = clf.predict(Xo)
        oos_emb.append(np.mean(lo == OOS))
        hlo, _ = hybrid_predict(oos, Xo, clf)
        oos_hyb.append(np.mean([l == OOS for l in hlo]))
    res["embedding"] = {"accuracy_no_oos_threshold": float(np.mean(emb_raw == y)), "accuracy": float(np.mean(emb_pred == y)),
                        "false_oos_dev": float(np.mean(emb_pred == OOS)), "oos_flagged": float(np.mean(oos_emb)),
                        "thresholds": [round(t, 3) for t in taus]}
    res["hybrid"] = {"accuracy": float(np.mean(hyb_pred == y)), "false_oos_dev": float(np.mean(hyb_pred == OOS)),
                     "oos_flagged": float(np.mean(oos_hyb)), "share_decided_by_rule": float(np.mean(hyb_path == "rule")),
                     "acc_rule_path": float(np.mean(hyb_pred[hyb_path == "rule"] == y[hyb_path == "rule"])),
                     "acc_embedding_path": float(np.mean(hyb_pred[hyb_path == "embedding"] == y[hyb_path == "embedding"]))}
    # embedding inference latency (LR only; encoding latency measured separately)
    clf = EmbeddingClassifier().fit(X, y)
    t0 = time.perf_counter()
    for i in range(len(y)):
        clf.predict(X[i:i + 1])
    lr_ms = (time.perf_counter() - t0) / len(y) * 1000
    enc = json.loads((OUT / "embed_latency.json").read_text(encoding="utf-8"))
    res["embedding"]["ms_per_prompt"] = enc["mean_ms"] + lr_ms
    res["hybrid"]["ms_per_prompt"] = rule_ms + (1 - res["hybrid"]["share_decided_by_rule"]) * (enc["mean_ms"] + lr_ms)

    # (d) LLM
    raw = {}
    for ln in (OUT / "llm_classifier_raw.jsonl").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            raw[r["key"]] = r
    import hashlib
    k = lambda p: hashlib.sha1(p.encode("utf-8")).hexdigest()
    llm_dev = [raw[k(p)] for p in prompts]
    llm_oos = [raw[k(p)] for p in oos]
    llm_lab = [r["label"] for r in llm_dev]
    failed = sum(r["raw"].startswith("FAILED") for r in llm_dev + llm_oos)
    allr = llm_dev + llm_oos
    res["llm"] = {"accuracy": float(np.mean(np.array(llm_lab) == y)), "false_oos_dev": float(np.mean([l == OOS for l in llm_lab])),
                  "oos_flagged": float(np.mean([r["label"] == OOS for r in llm_oos])), "failed_calls": failed,
                  "mean_latency_s": float(np.mean([r["latency_s"] for r in allr])),
                  "mean_tokens_in": float(np.mean([r["tokens_in"] for r in allr])), "mean_tokens_out": float(np.mean([r["tokens_out"] for r in allr])),
                  "cost_total_usd": float(sum(r["cost_usd"] for r in allr)), "n_calls": len(allr)}
    res["llm"]["cost_per_1000_usd"] = res["llm"]["cost_total_usd"] / len(allr) * 1000

    # per-category accuracy and confusion
    def percat(pred):
        return {c: float(np.mean(np.array(pred)[y == c] == c)) for c in CATEGORIES}
    res["per_category"] = {"rules": percat(np.array(rule_lab)), "embedding": percat(emb_pred), "hybrid": percat(hyb_pred),
                           "llm": percat(np.array(llm_lab))}
    confs = {"rules": confusion(y, rule_pred_for_conf), "embedding": confusion(y, emb_pred), "hybrid": confusion(y, hyb_pred),
             "llm": confusion(y, llm_lab)}
    (OUT / "classifier_cv_predictions.json").write_text(json.dumps(
        {t["id"]: {"hybrid": hyb_pred[i], "embedding": emb_pred[i], "rules": rule_lab[i], "llm": llm_lab[i], "true": y[i]}
         for i, t in enumerate(dev)}, indent=0), encoding="utf-8")
    res["rules_misses"] = [{"id": t["id"], "true": t["category"], "rule": rule_lab[i]} for i, t in enumerate(dev) if rule_lab[i] != y[i]][:60]
    (OUT / "classifier_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")

    # final default model (hybrid): fit on all 240 dev prompts; threshold from inner CV on all
    inner = cross_val_predict(EmbeddingClassifier().lr, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED), method="predict_proba")
    tau = pick_threshold(inner.max(1), BUDGET)
    art = ROOT / "router" / "artifacts"
    art.mkdir(exist_ok=True)
    np.savez(art / "task_type_lr.npz", coef=clf.lr.coef_, intercept=clf.lr.intercept_, classes=clf.lr.classes_, threshold=tau)

    L = ["# Task-type classifier comparison (dev only)", "",
         "240 in-scope dev prompts, 5-fold stratified CV (seed 20251120) + 30 out-of-scope prompts (`eval/phase4/oos_prompts.json`, written "
         "fresh; never trained on, never used to pick a threshold). Rules were hand-written (not learned), so they are NOT cross-validated and "
         "are somewhat optimistic: the author had seen some dev prompts (math/logic set A, summary prompts) when writing them. "
         f"Embedding OOS threshold = the {int(BUDGET*100)}th percentile of the top class probability on in-scope training prompts "
         "(inner CV), i.e. at most ~5% of in-scope prompts are sent to B1 needlessly.", "",
         "| classifier | in-scope accuracy | in-scope wrongly flagged OOS | OOS prompts flagged (of 30) | latency per prompt | cost per 1000 prompts |",
         "|---|---|---|---|---|---|"]
    R = res
    L.append(f"| (a) rules | {R['rules']['accuracy_all']:.1%} (abstains on {1-R['rules']['coverage_any']:.0%}; {R['rules']['acc_when_fired']:.1%} when it fires) | {R['rules']['false_oos_dev']:.1%} | {R['rules']['oos_flagged']:.0%} | {R['rules']['ms_per_prompt']*1000:.0f} µs | $0 |")
    L.append(f"| (b) MiniLM + LR | {R['embedding']['accuracy']:.1%} ({R['embedding']['accuracy_no_oos_threshold']:.1%} before the OOS threshold) | {R['embedding']['false_oos_dev']:.1%} | {R['embedding']['oos_flagged']:.0%} | {R['embedding']['ms_per_prompt']:.0f} ms (laptop CPU) | $0 |")
    L.append(f"| (c) hybrid: rule then embedding | {R['hybrid']['accuracy']:.1%} | {R['hybrid']['false_oos_dev']:.1%} | {R['hybrid']['oos_flagged']:.0%} | {R['hybrid']['ms_per_prompt']:.0f} ms avg | $0 |")
    L.append(f"| (d) LLM (glm-5.3-flash, zero-shot) | {R['llm']['accuracy']:.1%} | {R['llm']['false_oos_dev']:.1%} | {R['llm']['oos_flagged']:.0%} | {R['llm']['mean_latency_s']*1000:.0f} ms | ${R['llm']['cost_per_1000_usd']:.3f} at market price ({R['llm']['mean_tokens_in']:.0f} in / {R['llm']['mean_tokens_out']:.0f} out tokens per call; actual $0 via Hyde) |")
    L += ["", f"Hybrid: {R['hybrid']['share_decided_by_rule']:.0%} of dev prompts decided by a strong rule (accuracy {R['hybrid']['acc_rule_path']:.1%}); the rest by the embedding model (accuracy {R['hybrid']['acc_embedding_path']:.1%}).",
          f"Rules alone: strong rules fire on {R['rules']['coverage_strong']:.0%} of prompts with {R['rules']['acc_when_strong']:.1%} accuracy; any rule {R['rules']['coverage_any']:.0%} at {R['rules']['acc_when_fired']:.1%}.",
          f"LLM failed calls: {R['llm']['failed_calls']} (counted as out_of_scope).", "", "## Accuracy per category", "",
          "| category | rules | embedding | hybrid | LLM |", "|---|---|---|---|---|"]
    for c in CATEGORIES:
        L.append(f"| {c} | " + " | ".join(f"{R['per_category'][k][c]:.0%}" for k in ("rules", "embedding", "hybrid", "llm")) + " |")
    L += ["", "## Default classifier: (c) hybrid (strong rule, then MiniLM + logistic regression with the out_of_scope threshold)", "",
          f"- **Why not the LLM classifier, which scores highest ({R['llm']['accuracy']:.1%} in-scope, {R['llm']['oos_flagged']:.0%} of OOS flagged)?** "
          f"It adds a network call to every request ({R['llm']['mean_latency_s']*1000:.0f} ms, ~{R['llm']['mean_tokens_in']:.0f} tokens in) before any cheaper path can start, "
          f"and costs ${R['llm']['cost_per_1000_usd']:.3f} per 1000 prompts at market price, which is the same order as the whole bill for a cheap-model answer "
          "(a budget API call on these tasks is a few hundred tokens, roughly $0.0001-0.0003). A router whose classifier costs as much as a cheap answer cannot save money "
          "on the cheap paths. The hybrid is free and answers in ~20 ms on average (a strong rule is ~0.2 ms; the embedding path ~40 ms on this laptop CPU).",
          f"- **Why hybrid over the embedding model alone:** same in-scope accuracy ({R['hybrid']['accuracy']:.1%}), half of prompts skip the 40 ms encode, "
          "and the explicit out-of-scope rules catch whole-project / essay / translation requests that a probability threshold alone misses.",
          "- **Cost of a misclassification:** an in-scope prompt flagged out_of_scope goes to B1 (extra cost, correct answer); a prompt put in the wrong category "
          "can get the wrong validators and the wrong route (possible accuracy loss). The hybrid's category errors on dev are 2 math->summarisation, 1 code_gen->sentiment, "
          "and the rest are out_of_scope flags (see its confusion matrix).",
          "- **Fallback option, not built:** send only low-confidence prompts (embedding probability just above the threshold) to the LLM classifier.",
          "", "## Caveats (read before quoting numbers)", "",
          "- **CV is optimistic for templated prompts.** Many dev prompts of a category share a template (especially math, logic, NER, code), so a prompt's near-twin is often in the "
          "training fold. The Phase 6 test split (new templates for math/logic, held-out items elsewhere) is the honest number; expect lower accuracy there.",
          "- **The OOS prompts are not independent of the OOS rules.** I wrote the 30 OOS prompts first and then the OOS regex rules, so the rule/hybrid/LLM-prompt "
          "out-of-scope recall (80% / 95% / 100%) is partly in-sample. The only fully held-out OOS figure is the embedding threshold's "
          f"({R['embedding']['oos_flagged']:.0%}): the threshold was chosen without looking at any OOS prompt. Real traffic will contain out-of-scope prompts unlike these 30.",
          "- **Rules were written after a partial look at dev prompts** and are not cross-validated. Their weak spot is NER (7%): the rule phrasing did not match how the dev NER "
          "prompts are worded, so those prompts reach the embedding model; this is why the hybrid relies on the embedding path for roughly half of all prompts.",
          "- Difficulty and category labels, and the OOS list, come from the same author (me, with Kabir's review of the dataset); no external annotation.",
          "- n = 30 per category: a single misclassification moves a category's accuracy by 3.3 points."]
    for name in ("rules", "embedding", "hybrid", "llm"):
        L += ["", f"## Confusion matrix: {name} (rows true, columns predicted; dev in-scope only" + ("; rule abstentions appear in the out_of_scope column" if name == "rules" else "") + ")", "", md_conf(confs[name])]
    (OUT / "classifier_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()

