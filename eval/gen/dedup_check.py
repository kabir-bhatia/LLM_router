"""Near-duplicate check (plan section 5.3): flag prompt pairs within a category with similarity >= 0.95.

Primary: sentence-transformers all-MiniLM-L6-v2 embeddings (as in the plan). If the model cannot be loaded
(no network / hang), falls back to word 1-2gram TF-IDF cosine and records which method was used.
Templated items (same template, different numbers/names) are expected to score high; pairs are listed so
they can be judged. Writes eval/results/phase1_dedup.json.
Run: .venv/Scripts/python.exe -X utf8 -m eval.gen.dedup_check [--tfidf]
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

platform._wmi = None  # Windows: platform.uname() can hang on WMI (see tests/conftest.py)

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATS = ("factual", "math", "sentiment", "summarisation", "ner", "code_debug", "logic", "code_gen")
THRESH = 0.95


def embed_minilm(texts):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    return m.encode(texts, normalize_embeddings=True, batch_size=32)


def embed_tfidf(texts):
    from sklearn.feature_extraction.text import TfidfVectorizer
    v = TfidfVectorizer(ngram_range=(1, 2), lowercase=True).fit_transform(texts)
    arr = v.toarray()
    return arr / (np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12)


def main():
    use_tfidf = "--tfidf" in sys.argv
    out = {"method": None, "threshold": THRESH, "by_category": {}}
    for cat in CATS:
        items = json.loads((ROOT / "drafts" / f"{cat}.json").read_text(encoding="utf-8"))
        texts = [i["prompt"] for i in items]
        if not use_tfidf:
            try:
                emb, method = embed_minilm(texts), "minilm"
            except Exception as e:  # noqa: BLE001
                print("embedding model unavailable:", str(e)[:120])
                emb, method = embed_tfidf(texts), "tfidf"
        else:
            emb, method = embed_tfidf(texts), "tfidf"
        out["method"] = method
        sim = emb @ emb.T
        np.fill_diagonal(sim, 0)
        pairs = [(items[i]["id"], items[j]["id"], round(float(sim[i, j]), 3))
                 for i in range(len(items)) for j in range(i + 1, len(items)) if sim[i, j] >= THRESH]
        out["by_category"][cat] = {"max_similarity": round(float(sim.max()), 3), "flagged_pairs": pairs}
        print(cat, method, "max", round(float(sim.max()), 3), "flagged", len(pairs))
    (ROOT / "results" / "phase1_dedup.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
