"""
Train / refresh the intent classifier.

Usage (from project root):
    python scripts/train_model.py

The classifier is a token-overlap model that loads training data
directly from the datasets/ folder — no heavy ML training required.
Running this script re-reads all *_intents.json files and saves a
lightweight .joblib checkpoint to models/.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow imports from the project root (backend package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.intent_classifier import IntentClassifier  # noqa: E402

DATASETS_PATH = PROJECT_ROOT / "datasets"
MODEL_PATH    = PROJECT_ROOT / "models" / "intent_classifier.joblib"


def main() -> None:
    print("=" * 60)
    print("Bradford Council AI - Intent Classifier Training")
    print("=" * 60)
    print(f"Datasets : {DATASETS_PATH}")
    print(f"Model out: {MODEL_PATH}")
    print()

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    classifier = IntentClassifier(DATASETS_PATH)
    classifier.train(DATASETS_PATH)
    classifier.save(MODEL_PATH)

    examples = classifier._intent_examples

    # Group by service and intent for summary
    from collections import defaultdict
    by_service: dict = defaultdict(set)
    by_intent:  dict = defaultdict(int)

    for ex in examples:
        svc    = ex.get("service", "unknown")
        intent = ex.get("intent", "unknown")
        by_service[svc].add(intent)
        by_intent[intent] += 1

    total_examples = sum(by_intent.values())
    print(f"Services loaded : {len(by_service)}")
    print(f"Intents loaded  : {len(by_intent)}")
    print(f"Total examples  : {total_examples}")
    print()

    for service in sorted(by_service):
        print(f"  {service}:")
        for intent in sorted(by_service[service]):
            count  = by_intent.get(intent, 0)
            status = "OK" if count > 0 else "NO EXAMPLES"
            print(f"    [{status:11s}] {intent} ({count} examples)")

    print()
    print("Training complete. Model saved to:", MODEL_PATH)
    print("=" * 60)


if __name__ == "__main__":
    main()
