"""Run-time labels for the router: task category (hybrid classifier, rules then MiniLM) and difficulty (easy/hard).

Uses the Phase 4 artifacts as they are (router/artifacts/*.npz, router/classify.py, router/difficulty.py).
The MiniLM embedding is only computed when no strong rule fires. `embed_fn(prompt) -> vector` is injectable (tests use a fake;
the default reads the on-disk cache and, for unseen prompts, computes in a subprocess: see router/embeddings.py).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import numpy as np

from router.classify import OOS, HybridClassifier, rule_classify
from router.difficulty import category_onehot, features

ART = Path(__file__).resolve().parent / "artifacts"


def default_embed(prompt: str):
    from router.embeddings import embed
    return embed([prompt])[0]


class Labeler:
    def __init__(self, embed_fn: Optional[Callable] = None, task_clf: Optional[HybridClassifier] = None, diff_path=None):
        self.embed_fn = embed_fn or default_embed
        self.clf = task_clf or HybridClassifier.load(ART / "task_type_lr.npz")
        z = np.load(diff_path or ART / "difficulty_lr.npz", allow_pickle=False)
        self.mean, self.scale, self.coef, self.intercept = z["mean"], z["scale"], z["coef"][0], float(z["intercept"][0])

    def category(self, prompt: str) -> dict:
        lab, strong = rule_classify(prompt)
        if lab is not None and strong:
            return {"label": lab, "path": "rule", "confidence": 1.0}
        return self.clf.predict(prompt, self.embed_fn(prompt))

    def difficulty(self, prompt: str, category: str) -> str:
        if category == OOS:
            return "easy"
        x = np.hstack([features(prompt), category_onehot(category)])
        return "hard" if float(self.coef @ ((x - self.mean) / self.scale) + self.intercept) > 0 else "easy"

    def label(self, prompt: str) -> dict:
        c = self.category(prompt)
        return {"category": c["label"], "difficulty": self.difficulty(prompt, c["label"]), "path": c["path"], "confidence": c["confidence"]}
