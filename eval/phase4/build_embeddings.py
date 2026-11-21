"""Precompute and cache MiniLM embeddings for the 240 dev prompts + 30 OOS prompts (subprocess, timeout)."""
import json
import time

from router.data import ROOT, load_dev
from router.embeddings import embed

dev = load_dev()
oos = json.loads((ROOT / "eval" / "phase4" / "oos_prompts.json").read_text(encoding="utf-8"))["prompts"]
t = time.time()
e = embed([x["prompt"] for x in dev] + oos, timeout=900)
print(e.shape, round(time.time() - t, 1), "s")
