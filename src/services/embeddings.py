"""
Embeddings Service.

Generates text embeddings locally with sentence-transformers.

Why local rather than an API: embeddings are on the hot path of every cache
lookup, and the threshold sweep in eval/ re-embeds the whole prompt corpus on
every run. A network round-trip per prompt would make that analysis slow and
rate-limited. all-MiniLM-L6-v2 is 384-dim, ~80MB, and runs fine on CPU.

The model is loaded lazily on first use so that importing this module (which
the FastAPI app does at startup) stays cheap.
"""

import asyncio
from typing import Optional

import numpy as np

from src.config import get_settings


class EmbeddingsService:
    """
    Generates normalized sentence embeddings on the local CPU.

    Vectors are L2-normalized at encode time, which means cosine similarity
    between any two of them is just a dot product. The semantic cache and the
    threshold sweep both rely on that.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embeddings service.

        Args:
            model_name: sentence-transformers model id (defaults to settings)
        """
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._model = None

    def _load_model(self):
        """Load the transformer model, once, on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        """Embedding dimensionality of the loaded model."""
        return self._load_model().get_sentence_embedding_dimension()

    def embed_sync(self, text: str) -> list[float]:
        """
        Synchronous single-text embedding.

        Used directly by offline analysis scripts, which have no event loop
        and no reason to pay for one.
        """
        model = self._load_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch_sync(self, texts: list[str]) -> np.ndarray:
        """
        Synchronous batch embedding.

        Returns:
            (n_texts, dim) float32 array of L2-normalized row vectors, so that
            `matrix @ matrix.T` is the full pairwise cosine similarity matrix.
        """
        model = self._load_model()
        return model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=len(texts) > 100,
        )

    async def embed(self, text: str) -> list[float]:
        """
        Generate an embedding without blocking the event loop.

        Encoding is CPU-bound, so it runs in a worker thread; awaiting it
        directly on the loop would stall every other in-flight request.
        """
        return await asyncio.to_thread(self.embed_sync, text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts off the event loop."""
        result = await asyncio.to_thread(self.embed_batch_sync, texts)
        return result.tolist()

    async def health_check(self) -> bool:
        """Check that the model loads and produces a non-empty vector."""
        try:
            embedding = await self.embed("test")
            return len(embedding) > 0
        except Exception:
            return False

    async def close(self):
        """No network resources to release; kept for interface symmetry."""
        return None


# Singleton instance
_embeddings: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """Get the singleton embeddings service."""
    global _embeddings
    if _embeddings is None:
        _embeddings = EmbeddingsService()
    return _embeddings
