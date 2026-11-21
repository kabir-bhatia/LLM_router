"""MiniLM embeddings loaded ONCE in-process (for Kaggle / servers), as an alternative to router/embeddings.py (laptop default: on-disk cache,
subprocess per unseen prompt because importing torch in the main process can hang on the dev laptop).

    emb = InProcessEmbedder()            # loads all-MiniLM-L6-v2 on first use
    emb.prepare(all_prompts)             # optional: one batched encode of every prompt up front
    Labeler(embed_fn=emb)                # emb(prompt) -> L2-normalised float32 vector, memoised

Same model, device (cpu) and settings (normalize_embeddings=True, batch 32) as router/embeddings.py, so classifier outputs are identical;
tests/CLI check that on dev prompts.
"""
from __future__ import annotations

import threading

import numpy as np

MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class InProcessEmbedder:
    def __init__(self, model_name: str = MODEL, device: str = "cpu", batch_size: int = 32):
        self.model_name, self.device, self.batch_size = model_name, device, batch_size
        self._model = None
        self._memo = {}
        self._lock = threading.Lock()

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def prepare(self, prompts) -> int:
        """Embed every not-yet-seen prompt in batches; returns how many were computed."""
        with self._lock:
            new = [p for p in dict.fromkeys(prompts) if p not in self._memo]
            if new:
                vecs = self._load().encode(new, batch_size=self.batch_size, normalize_embeddings=True, show_progress_bar=False)
                for p, v in zip(new, vecs):
                    self._memo[p] = np.asarray(v, dtype="float32")
            return len(new)

    def __call__(self, prompt: str):
        if prompt not in self._memo:
            self.prepare([prompt])
        return self._memo[prompt]
