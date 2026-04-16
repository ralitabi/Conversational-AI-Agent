"""
Thin wrapper around OpenAI's embeddings API.

Uses text-embedding-3-small — cheap, fast, and 1536-dimensional.
All returned vectors are already L2-normalised by OpenAI, so
dot-product == cosine-similarity.
"""
from __future__ import annotations

import math
from typing import List

from backend.openai_client import client

_MODEL = "text-embedding-3-small"
_MAX_BATCH = 100          # OpenAI allows up to 2048 inputs per call


def _clean(text: str) -> str:
    return " ".join(str(text or "").split())


class Embedder:
    """Generates text embeddings via the OpenAI API."""

    model: str = _MODEL

    # ── Public API ─────────────────────────────────────────────────────────────

    def embed(self, text: str) -> List[float]:
        """Return the embedding vector for a single string, or [] on failure."""
        cleaned = _clean(text)
        if not cleaned:
            return []
        try:
            response = client.embeddings.create(input=[cleaned], model=self.model)
            return response.data[0].embedding
        except Exception as exc:
            print(f"[Embedder] embed failed: {exc}")
            return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Return embeddings for a list of strings.
        Splits into batches of _MAX_BATCH to stay within API limits.
        Returns [] for any text that could not be embedded.
        """
        cleaned = [_clean(t) for t in texts]
        results: List[List[float]] = [[] for _ in cleaned]

        # Process in chunks
        for start in range(0, len(cleaned), _MAX_BATCH):
            chunk = cleaned[start : start + _MAX_BATCH]
            valid_indices = [i for i, t in enumerate(chunk) if t]
            valid_texts   = [chunk[i] for i in valid_indices]

            if not valid_texts:
                continue

            try:
                response = client.embeddings.create(input=valid_texts, model=self.model)
                for local_i, item in enumerate(response.data):
                    global_i = start + valid_indices[local_i]
                    results[global_i] = item.embedding
            except Exception as exc:
                print(f"[Embedder] embed_batch chunk failed: {exc}")

        return results

    # ── Utility ────────────────────────────────────────────────────────────────

    @staticmethod
    def cosine(a: List[float], b: List[float]) -> float:
        """
        Cosine similarity between two vectors.
        OpenAI embeddings are unit-normalised, so this equals the dot product,
        but we compute it properly for safety.
        """
        if not a or not b or len(a) != len(b):
            return 0.0
        dot  = sum(x * y for x, y in zip(a, b))
        na   = math.sqrt(sum(x * x for x in a))
        nb   = math.sqrt(sum(x * x for x in b))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)
