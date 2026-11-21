"""Difficulty classifier (easy/hard) on the 240 dev prompts: 5-fold CV stratified by category x difficulty.

Variants: majority (50%), cheap features + category, embedding + category, both. The category is the TRUE category here (at run time it is the
task-type classifier's prediction; the hybrid classifier's accuracy is reported separately). Hard/easy labels are the Phase 1 author labels.
"""
import router  # noqa: F401  (must come first: Windows platform.uname workaround; sklearn import hangs without it)
import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from router.data import ROOT, load_dev
from router.difficulty import CATEGORIES, category_onehot, features
from router.embeddings import embed

OUT = ROOT / "eval" / "results" / "phase4"
SEED = 20251120


def main():
    dev = load_dev()
    prompts = [t["prompt"] for t in dev]
    cats = np.array([t["category"] for t in dev])
    y = np.array([t["difficulty"] == "hard" for t in dev]).astype(int)
    F = np.stack([features(p) for p in prompts])
    C = np.stack([category_onehot(c) for c in cats])
    E = embed(prompts)
    # per-category standardisation of the cheap features (length means different things for a summary and a sentiment prompt)
    Fz = np.zeros_like(F)
    sets = {
        "features + category": lambda tr, te: (np.hstack([F, C]), None),
        "embedding + category": lambda tr, te: (np.hstack([E, C]), None),
        "features + embedding + category": lambda tr, te: (np.hstack([F, E, C]), None),
    }
    strat = np.array([f"{c}|{d}" for c, d in zip(cats, y)])
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    res = {}
    for name, build in sets.items():
        X, _ = build(None, None)
        pred = np.zeros(len(y), int)
        for tr, te in skf.split(X, strat):
            # interactions with category: one model per category would be starved (n=24 train per category), so one global model
            m = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=5000))
            m.fit(X[tr], y[tr])
            pred[te] = m.predict(X[te])
        res[name] = {"accuracy": float((pred == y).mean()),
                     "per_category": {c: float((pred[cats == c] == y[cats == c]).mean()) for c in CATEGORIES}}
    # per-category models on features only (24 train / 6 test per fold per category) for comparison
    pred = np.zeros(len(y), int)
    for c in CATEGORIES:
        idx = np.where(cats == c)[0]
        sk = StratifiedKFold(5, shuffle=True, random_state=SEED)
        for tr, te in sk.split(idx, y[idx]):
            m = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=5000))
            m.fit(F[idx[tr]], y[idx[tr]])
            pred[idx[te]] = m.predict(F[idx[te]])
    res["per-category models, features only"] = {"accuracy": float((pred == y).mean()),
                                                  "per_category": {c: float((pred[cats == c] == y[cats == c]).mean()) for c in CATEGORIES}}
    res["majority baseline"] = {"accuracy": 0.5, "per_category": {c: 0.5 for c in CATEGORIES}}
    (OUT / "difficulty_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    # Final deployable model (features + category, fit on all 240) and CV-predicted (category, difficulty) labels for the policy replay:
    # the test fold sees the hybrid classifier's CV-predicted category (an out_of_scope prediction is routed to B1 by the replay).
    X = np.hstack([F, C])
    pc = json.loads((OUT / "classifier_cv_predictions.json").read_text(encoding="utf-8"))
    pred_labels = {}
    for tr, te in skf.split(X, strat):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=5000)).fit(X[tr], y[tr])
        for i in te:
            pcat = pc[dev[i]["id"]]["hybrid"]
            xi = np.hstack([F[i], category_onehot(pcat)])[None, :]
            pred_labels[dev[i]["id"]] = [pcat, "hard" if m.predict(xi)[0] == 1 else "easy"]
    (OUT / "predicted_labels.json").write_text(json.dumps(pred_labels, indent=0), encoding="utf-8")
    final = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=5000)).fit(X, y)
    art = ROOT / "router" / "artifacts"
    art.mkdir(exist_ok=True)
    sc, lr = final.steps[0][1], final.steps[1][1]
    np.savez(art / "difficulty_lr.npz", mean=sc.mean_, scale=sc.scale_, coef=lr.coef_, intercept=lr.intercept_)
    L = ["# Difficulty classifier (easy/hard), dev only", "",
         "5-fold CV stratified by category x difficulty (seed 20251120), n = 240 (15 easy + 15 hard per category). The true category is given to the model "
         "(at run time it comes from the task-type classifier). Labels are the Phase 1 author labels; Phase 3 will show whether 'hard' really is harder "
         "for models. Chance = 50%.", "", "| variant | overall | " + " | ".join(CATEGORIES) + " |", "|---|---|" + "---|" * len(CATEGORIES)]
    for name, r in res.items():
        L.append(f"| {name} | {r['accuracy']:.1%} | " + " | ".join(f"{r['per_category'][c]:.0%}" for c in CATEGORIES) + " |")
    L += ["", "**Reading:** the cheap features (length, number counts, constraint words, code lines, 'either', negations) + category reach ~75% overall, well above chance; "
          "adding the MiniLM embedding makes it *worse* (~55%: 384 dimensions against 192 training prompts overfit), so the deployed difficulty model is features + category "
          "(`router/artifacts/difficulty_lr.npz`). It works where difficulty is structural (math, logic, NER: more steps, more constraints, more entities) and is near chance for "
          "sentiment and summarisation, where 'hard' is about subtle wording or a tight limit. Caveat: dev prompts of one category share templates, so CV folds contain near-twins "
          "and the numbers are optimistic; and 'hard' is the author's label until Phase 3 shows which cells really are harder for models. Where the classifier is near chance, the "
          "policy should not rely on the difficulty split (the policy code falls back to category level when a cell is too small; it could also be told to ignore difficulty for such categories).",
          "", "Per-category cells have n = 30, so each percentage has a 95% interval of roughly +/-17 points; read the overall column, and treat a "
          "category as 'predictable' only when it is far above 50%."]
    (OUT / "difficulty_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()

