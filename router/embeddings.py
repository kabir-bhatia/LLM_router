"""Cached MiniLM embeddings. sentence-transformers/torch imports can hang on this machine, so embeddings are
computed ONCE in a subprocess with a timeout and cached to disk (keyed by sha1 of the text). Everything else
loads the cache only; nothing in the router's test path imports torch.

    embed(texts) -> np.ndarray (n, 384), L2-normalised
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "eval" / "phase4" / "cache"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_WORKER = r'''
import json, sys, platform
platform._wmi = None
import numpy as np
from sentence_transformers import SentenceTransformer
texts = json.load(open(sys.argv[1], encoding="utf-8"))
m = SentenceTransformer(sys.argv[3], device="cpu")
e = m.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
np.save(sys.argv[2], np.asarray(e, dtype="float32"))
'''


def _key(t: str) -> str:
    return hashlib.sha1(t.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    f = CACHE_DIR / "embeddings.npz"
    if not f.exists():
        return {}
    z = np.load(f, allow_pickle=False)
    return dict(zip(z["keys"].tolist(), z["vecs"]))


def embed(texts, timeout: int = 900) -> np.ndarray:
    cache = _load_cache()
    missing = [t for t in dict.fromkeys(texts) if _key(t) not in cache]
    if missing:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tin, tout, wf = CACHE_DIR / "_in.json", CACHE_DIR / "_out.npy", CACHE_DIR / "_worker.py"
        tin.write_text(json.dumps(missing), encoding="utf-8")
        wf.write_text(_WORKER, encoding="utf-8")
        subprocess.run([sys.executable, "-X", "utf8", str(wf), str(tin), str(tout), MODEL], check=True, timeout=timeout)
        vecs = np.load(tout)
        for t, v in zip(missing, vecs):
            cache[_key(t)] = v
        keys = np.array(list(cache.keys()))
        np.savez(CACHE_DIR / "embeddings.npz", keys=keys, vecs=np.stack(list(cache.values())))
        for f in (tin, tout, wf):
            f.unlink(missing_ok=True)
    return np.stack([cache[_key(t)] for t in texts])
