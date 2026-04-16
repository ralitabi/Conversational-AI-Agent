"""
Pre-builds embedding caches for all service FAQ datasets.

Run once (or after updating FAQ JSON files) to populate the cache so the
first user request doesn't have to wait for embedding generation.

Usage:
    python -m backend.embeddings.cache_builder
    python -m backend.embeddings.cache_builder --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Resolve project root ────────────────────────────────────────────────────
_HERE        = Path(__file__).resolve().parent          # backend/embeddings/
_BACKEND     = _HERE.parent                             # backend/
_PROJECT     = _BACKEND.parent                          # project root
_DATASETS    = _PROJECT / "datasets"
_CACHE_DIR   = _PROJECT / ".embedding_cache"

# Make sure backend package is importable when running as a script
if str(_PROJECT) not in sys.path:
    sys.path.insert(0, str(_PROJECT))


def build_all_caches(
    datasets_path: Path = _DATASETS,
    cache_dir: Path = _CACHE_DIR,
    force: bool = False,
) -> None:
    """
    Iterate over every service folder in *datasets_path* and build
    (or refresh) its embedding cache.
    """
    from backend.embeddings.embedding_store import EmbeddingStore

    store = EmbeddingStore(datasets_path, cache_dir)

    service_folders = [
        f.name for f in datasets_path.iterdir()
        if f.is_dir() and not f.name.startswith(".")
    ]

    if not service_folders:
        print("[CacheBuilder] No service folders found.")
        return

    total = 0
    for service in sorted(service_folders):
        count = store.build_service_cache(service, force=force)
        total += count

    print(f"\n[CacheBuilder] Done. {total} FAQs embedded across {len(service_folders)} services.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build FAQ embedding caches.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild caches even if they are already up-to-date.",
    )
    args = parser.parse_args()
    build_all_caches(force=args.force)
