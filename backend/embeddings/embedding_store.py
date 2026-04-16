"""
Semantic search over the FAQ corpus using pre-computed embeddings.

On first use for a service, FAQs are embedded and saved to a JSON cache
file alongside the datasets.  Subsequent requests load from cache instantly.
The cache is automatically invalidated when the source FAQ file is newer.

Cache location:  <project_root>/.embedding_cache/<service_name>.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.embeddings.embedder import Embedder

# Similarity threshold — results below this are ignored
SIMILARITY_THRESHOLD = 0.45


class EmbeddingStore:
    """
    Loads FAQ embeddings from disk (or builds them on first run)
    and provides fast cosine-similarity search.
    """

    def __init__(self, datasets_path: Path, cache_dir: Path) -> None:
        self.datasets_path = Path(datasets_path)
        self.cache_dir     = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.embedder      = Embedder()

        # service_name → list of FAQ dicts (each has an "embedding" key)
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    # ── Public ──────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        service_name: str,
        intent: Optional[str] = None,
        k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Return the top-k FAQ dicts most semantically similar to *query*.
        Each dict includes a "score" (cosine similarity, 0-1) field.
        Returns [] if embeddings are unavailable.
        """
        faqs = self._get_faqs(service_name)
        if not faqs:
            return []

        query_vec = self.embedder.embed(query)
        if not query_vec:
            return []

        scored: List[Dict[str, Any]] = []
        for faq in faqs:
            vec = faq.get("embedding", [])
            if not vec:
                continue
            score = self.embedder.cosine(query_vec, vec)
            if score >= SIMILARITY_THRESHOLD:
                scored.append({**faq, "score": score})

        # Optionally boost intent-matching results
        if intent:
            for item in scored:
                if item.get("intent") == intent:
                    item["score"] = min(1.0, item["score"] + 0.05)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def build_service_cache(self, service_name: str, force: bool = False) -> int:
        """
        Pre-build and save the embedding cache for a service.
        Returns the number of FAQs embedded.
        Call this from cache_builder.py or on first startup.
        """
        cache_path = self._cache_path(service_name)
        faq_paths  = self._find_faq_files(service_name)

        if not faq_paths:
            print(f"[EmbeddingStore] No FAQ files found for '{service_name}'")
            return 0

        if not force and self._cache_is_fresh(cache_path, faq_paths):
            print(f"[EmbeddingStore] Cache is up-to-date for '{service_name}', skipping.")
            return 0

        faqs = []
        for faq_path in faq_paths:
            faqs.extend(self._load_faq_file(faq_path))

        if not faqs:
            return 0

        # Build embedding text = question + keywords
        texts = [self._faq_embed_text(f) for f in faqs]
        vectors = self.embedder.embed_batch(texts)

        embedded = []
        for faq, vec in zip(faqs, vectors):
            if vec:
                embedded.append({**faq, "embedding": vec})

        # Save cache
        with open(cache_path, "w", encoding="utf-8") as fh:
            json.dump({"faqs": embedded}, fh)

        print(f"[EmbeddingStore] Built cache for '{service_name}': {len(embedded)} FAQs")
        self._cache[service_name] = embedded
        return len(embedded)

    # ── Private ─────────────────────────────────────────────────────────────────

    def _get_faqs(self, service_name: str) -> List[Dict[str, Any]]:
        """Return cached FAQs, loading from disk or building if needed."""
        if service_name in self._cache:
            return self._cache[service_name]

        cache_path = self._cache_path(service_name)
        faq_paths  = self._find_faq_files(service_name)

        if not faq_paths:
            return []

        if cache_path.exists() and self._cache_is_fresh(cache_path, faq_paths):
            try:
                with open(cache_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                faqs = data.get("faqs", [])
                self._cache[service_name] = faqs
                print(f"[EmbeddingStore] Loaded cache for '{service_name}': {len(faqs)} FAQs")
                return faqs
            except Exception as exc:
                print(f"[EmbeddingStore] Cache load failed for '{service_name}': {exc}")

        # Build cache on first use
        self.build_service_cache(service_name, force=True)
        return self._cache.get(service_name, [])

    def _cache_path(self, service_name: str) -> Path:
        return self.cache_dir / f"{service_name}.json"

    def _find_faq_files(self, service_name: str) -> List[Path]:
        """Locate all *_faq.json files for a service."""
        folder = self._resolve_service_folder(service_name)
        if not folder:
            return []
        return sorted(folder.glob("*_faq.json"))

    def _resolve_service_folder(self, service_name: str) -> Optional[Path]:
        if not self.datasets_path.exists():
            return None
        target = service_name.lower().replace(" ", "").replace("_", "")
        for folder in self.datasets_path.iterdir():
            if folder.is_dir():
                key = folder.name.lower().replace(" ", "").replace("_", "")
                if key == target:
                    return folder
        return None

    def _cache_is_fresh(self, cache_path: Path, faq_paths: List[Path]) -> bool:
        """True if the cache file is newer than all source FAQ files."""
        if not cache_path.exists():
            return False
        cache_mtime = cache_path.stat().st_mtime
        return all(cache_mtime >= p.stat().st_mtime for p in faq_paths)

    @staticmethod
    def _load_faq_file(path: Path) -> List[Dict[str, Any]]:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
            if isinstance(data, dict):
                return data.get("faqs", []) or data.get("data", [])
        except Exception as exc:
            print(f"[EmbeddingStore] Failed to load {path}: {exc}")
        return []

    @staticmethod
    def _faq_embed_text(faq: Dict[str, Any]) -> str:
        """
        Build the text that will be embedded for a FAQ entry.
        Including keywords gives richer signal for short queries.
        """
        parts = []
        if faq.get("question"):
            parts.append(faq["question"])
        if faq.get("keywords"):
            parts.append(" ".join(str(k) for k in faq["keywords"]))
        if faq.get("answer"):
            # Truncate answer to first 120 chars to keep embedding focused on topic
            parts.append(faq["answer"][:120])
        return " ".join(parts)
