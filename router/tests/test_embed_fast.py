"""The in-process embedder (Kaggle option) gives the same classifier outputs as the cached/subprocess default, on dev prompts."""
import numpy as np
import pytest

from router.data import load_dev
from router.embeddings import embed


def test_inprocess_embeddings_give_identical_labels():
    from router.embed_fast import InProcessEmbedder
    from router.labeler import Labeler
    ps = [t["prompt"] for t in load_dev()[::24]]            # 10 prompts spread over the categories
    try:
        e = InProcessEmbedder()
        e.prepare(ps)
    except Exception as ex:  # noqa: BLE001 - no sentence-transformers / model offline
        pytest.skip(f"in-process MiniLM unavailable: {type(ex).__name__}")
    assert np.abs(np.stack([e(p) for p in ps]) - embed(ps)).max() < 1e-5
    a, b = Labeler(embed_fn=e), Labeler()
    for p in ps:
        x, y = a.label(p), b.label(p)
        assert (x["category"], x["difficulty"], x["path"]) == (y["category"], y["difficulty"], y["path"])
        assert x["confidence"] == pytest.approx(y["confidence"], abs=1e-5)
