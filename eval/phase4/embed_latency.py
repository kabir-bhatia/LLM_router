"""Per-prompt latency of encoding ONE prompt with MiniLM on this laptop's CPU (run in a subprocess with a timeout)."""
import json
import platform
import statistics
import sys
import time

platform._wmi = None
sys.path.insert(0, ".")
from router.data import ROOT, load_dev  # noqa: E402

from sentence_transformers import SentenceTransformer  # noqa: E402

texts = [t["prompt"] for t in load_dev()][::5][:48]
m = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
m.encode(["warm up"], normalize_embeddings=True)
lat = []
for t in texts:
    t0 = time.perf_counter()
    m.encode([t], normalize_embeddings=True)
    lat.append((time.perf_counter() - t0) * 1000)
res = {"n": len(lat), "mean_ms": statistics.mean(lat), "median_ms": statistics.median(lat), "p95_ms": sorted(lat)[int(0.95 * len(lat)) - 1]}
(ROOT / "eval" / "results" / "phase4" / "embed_latency.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print(res)
