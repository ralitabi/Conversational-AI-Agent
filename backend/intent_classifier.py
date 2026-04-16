from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""

    text = str(value).strip().lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(value: Optional[str]) -> List[str]:
    text = normalize_text(value)
    if not text:
        return []
    return re.findall(r"[a-z0-9]+", text)


class IntentClassifier:
    def __init__(self, datasets_root: Optional[str | Path] = None) -> None:
        if datasets_root is None:
            self.datasets_root = Path(__file__).resolve().parent.parent / "datasets"
        else:
            self.datasets_root = Path(datasets_root)

        self._intent_examples: List[Dict[str, Any]] = []
        self.refresh()

    # -------------------------------------------------------------------------
    # Compatibility methods
    # -------------------------------------------------------------------------

    def train(self, datasets_root: Optional[str | Path] = None) -> None:
        if datasets_root is not None:
            self.datasets_root = Path(datasets_root)
        self.refresh()

    def load(self, model_path: Optional[str | Path] = None) -> None:
        # Compatibility no-op for current lightweight classifier
        self.refresh()

    def save(self, model_path: Optional[str | Path] = None) -> None:
        # Compatibility no-op
        return None

    # -------------------------------------------------------------------------
    # Dataset loading
    # -------------------------------------------------------------------------

    def _load_json_file(self, file_path: Path) -> Any:
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _is_intent_file(self, file_path: Path) -> bool:
        return "intent" in file_path.stem.lower()

    def _normalize_service_name(self, value: Optional[str], fallback: str = "") -> str:
        text = normalize_text(value or fallback)
        return text.replace(" ", "_")

    def _build_example(
        self,
        *,
        item: Dict[str, Any],
        service_area: str,
        source_file: Path,
    ) -> Optional[Dict[str, Any]]:
        text = str(item.get("text", "")).strip()
        intent = str(item.get("intent", "")).strip()

        if not text or not intent:
            return None

        service = self._normalize_service_name(
            item.get("service"),
            fallback=service_area,
        )

        token_list = tokenize(text)
        return {
            "text": text,
            "normalized_text": normalize_text(text),
            "tokens": set(token_list) | set(self._stem(t) for t in token_list),
            "token_list": token_list,
            "intent": intent,
            "service": service,
            "needs_live_lookup": bool(item.get("needs_live_lookup", False)),
            "source_file": str(source_file),
        }

    def _load_all_intent_examples(self) -> List[Dict[str, Any]]:
        examples: List[Dict[str, Any]] = []

        if not self.datasets_root.exists():
            return examples

        for json_file in sorted(self.datasets_root.glob("*/*.json")):
            if not self._is_intent_file(json_file):
                continue

            try:
                data = self._load_json_file(json_file)
            except Exception:
                continue

            if not isinstance(data, list):
                continue

            service_area = self._normalize_service_name(json_file.parent.name)

            for item in data:
                if not isinstance(item, dict):
                    continue

                example = self._build_example(
                    item=item,
                    service_area=service_area,
                    source_file=json_file,
                )
                if example:
                    examples.append(example)

        return examples

    def refresh(self) -> None:
        self._intent_examples = self._load_all_intent_examples()

    # -------------------------------------------------------------------------
    # Scoring helpers
    # -------------------------------------------------------------------------

    def _score_service_match(
        self,
        example_service: str,
        selected_service: Optional[str],
    ) -> float:
        if not selected_service:
            return 0.0

        selected_norm = self._normalize_service_name(selected_service)
        if selected_norm == example_service:
            return 0.75

        return 0.0

    def _score_text_match(
        self,
        query_text: str,
        example_text: str,
    ) -> float:
        if not query_text or not example_text:
            return 0.0

        if query_text == example_text:
            return 10.0

        if example_text in query_text:
            return 6.5

        if query_text in example_text:
            return 4.5

        return 0.0

    @staticmethod
    def _tokenize_bigrams(tokens: List[str]) -> List[str]:
        """Return bigram strings like ['council_tax', 'tax_band'] from a token list."""
        return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]

    @staticmethod
    def _stem(token: str) -> str:
        """Strip common English suffixes for basic stemming."""
        if len(token) > 6 and token.endswith("ment"):
            return token[:-4]
        if len(token) > 6 and token.endswith("ness"):
            return token[:-4]
        if len(token) > 6 and token.endswith("tion"):
            return token[:-4]
        if len(token) > 5 and token.endswith("ing"):
            return token[:-3]
        if len(token) > 4 and token.endswith("ed"):
            return token[:-2]
        if len(token) > 4 and token.endswith("ly"):
            return token[:-2]
        if len(token) > 4 and token.endswith("er"):
            return token[:-2]
        return token

    def _score_token_overlap(
        self,
        query_tokens: set[str],
        example_tokens: set[str],
        query_token_list: Optional[List[str]] = None,
        example_token_list: Optional[List[str]] = None,
    ) -> float:
        if not query_tokens or not example_tokens:
            return 0.0

        overlap = len(query_tokens & example_tokens)
        if overlap <= 0:
            return 0.0

        precision = overlap / len(example_tokens)
        recall = overlap / len(query_tokens)
        f1 = 0.0

        if precision + recall > 0:
            f1 = 2 * precision * recall / (precision + recall)

        score = 0.0
        score += overlap * 0.9
        score += precision * 2.0
        score += recall * 1.5
        score += f1 * 1.5

        if len(example_tokens) <= 4 and precision >= 0.75:
            score += 1.5

        if len(query_tokens) <= 4 and recall >= 0.75:
            score += 1.0

        # Sequential bigram scoring — use original token order for meaningful phrase pairs
        if query_token_list and example_token_list:
            query_bigrams = set(self._tokenize_bigrams(query_token_list))
            example_bigrams = set(self._tokenize_bigrams(example_token_list))
            bigram_overlap = len(query_bigrams & example_bigrams)
            score += bigram_overlap * 2.5

        return score

    def _score_example(
        self,
        query: str,
        example: Dict[str, Any],
        selected_service: Optional[str] = None,
    ) -> float:
        query_text = normalize_text(query)
        query_token_list = tokenize(query)
        query_tokens = set(query_token_list) | set(self._stem(t) for t in query_token_list)

        example_text = str(example.get("normalized_text", ""))
        example_tokens = set(example.get("tokens", set()))
        example_token_list = example.get("token_list") or []
        example_service = str(example.get("service", ""))

        if not query_text or not example_text:
            return 0.0

        score = 0.0
        score += self._score_service_match(example_service, selected_service)
        score += self._score_text_match(query_text, example_text)
        score += self._score_token_overlap(
            query_tokens,
            example_tokens,
            query_token_list=query_token_list,
            example_token_list=example_token_list,
        )

        return round(score, 4)

    def _rank_examples(
        self,
        query: str,
        selected_service: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []

        for example in self._intent_examples:
            score = self._score_example(
                query,
                example,
                selected_service=selected_service,
            )
            if score <= 0:
                continue

            item = dict(example)
            item["score"] = score
            ranked.append(item)

        ranked.sort(
            key=lambda item: (
                float(item.get("score", 0.0)),
                len(str(item.get("text", ""))),
            ),
            reverse=True,
        )
        return ranked

    def _aggregate_intents(
        self,
        ranked_examples: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        aggregated: Dict[str, Dict[str, Any]] = {}

        for item in ranked_examples[:30]:
            intent_name = str(item.get("intent", "")).strip()
            if not intent_name:
                continue

            current_score = float(item.get("score", 0.0))

            if intent_name not in aggregated:
                aggregated[intent_name] = {
                    "intent": intent_name,
                    "service": item.get("service"),
                    "needs_live_lookup": bool(item.get("needs_live_lookup", False)),
                    "top_example": item.get("text", ""),
                    "top_score": current_score,
                    "support_score": current_score,
                    "match_count": 1,
                }
                continue

            aggregated[intent_name]["match_count"] += 1
            aggregated[intent_name]["support_score"] += current_score

            if current_score > float(aggregated[intent_name]["top_score"]):
                aggregated[intent_name]["top_score"] = current_score
                aggregated[intent_name]["top_example"] = item.get("text", "")
                aggregated[intent_name]["needs_live_lookup"] = bool(
                    item.get("needs_live_lookup", False)
                )
                aggregated[intent_name]["service"] = item.get("service")

        results = list(aggregated.values())

        for item in results:
            top_score = float(item.get("top_score", 0.0))
            support_score = float(item.get("support_score", 0.0))
            match_count = int(item.get("match_count", 0))

            confidence = 0.0
            confidence += min(top_score / 10.0, 0.75)
            confidence += min(max(support_score - top_score, 0.0) / 40.0, 0.15)
            confidence += min(match_count / 20.0, 0.10)

            item["confidence"] = round(min(confidence, 0.98), 4)

        results.sort(
            key=lambda item: (
                float(item.get("confidence", 0.0)),
                float(item.get("top_score", 0.0)),
                int(item.get("match_count", 0)),
            ),
            reverse=True,
        )
        return results

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def classify(
        self,
        text: str,
        selected_service: Optional[str] = None,
    ) -> Dict[str, Any]:
        ranked_examples = self._rank_examples(text, selected_service=selected_service)
        aggregated = self._aggregate_intents(ranked_examples)

        normalized_service = (
            self._normalize_service_name(selected_service)
            if selected_service
            else None
        )

        if not aggregated:
            return {
                "intent": None,
                "confidence": 0.0,
                "candidates": [],
                "needs_live_lookup": False,
                "service": normalized_service,
            }

        top = aggregated[0]

        candidates = [
            {
                "intent": item["intent"],
                "confidence": float(item["confidence"]),
                "needs_live_lookup": bool(item.get("needs_live_lookup", False)),
                "service": item.get("service"),
                "top_example": item.get("top_example", ""),
            }
            for item in aggregated[:5]
        ]

        return {
            "intent": top["intent"],
            "confidence": float(top["confidence"]),
            "candidates": candidates,
            "needs_live_lookup": bool(top.get("needs_live_lookup", False)),
            "service": top.get("service", normalized_service),
        }

    def predict(
        self,
        text: str,
        selected_service: Optional[str] = None,
    ) -> Tuple[str, float]:
        result = self.classify(text, selected_service=selected_service)
        predicted_intent = result.get("intent") or "unknown"
        confidence = float(result.get("confidence", 0.0))
        return predicted_intent, confidence

    def get_examples_for_intent(self, intent_name: str) -> List[Dict[str, Any]]:
        target = normalize_text(intent_name)
        return [
            item
            for item in self._intent_examples
            if normalize_text(item.get("intent")) == target
        ]


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    datasets_path = project_root / "datasets"

    classifier = IntentClassifier(datasets_root=datasets_path)

    print(f"Datasets root: {datasets_path}")
    print(f"Loaded examples: {len(classifier._intent_examples)}")

    test_queries = [
        "When is my next recycling collection?",
        "What day is my bin collected?",
        "My bin was missed",
        "Can I recycle foil?",
        "I need assisted collection",
        "What can I put in the green bin?",
        "What is my council tax band?",
        "How do I pay council tax?",
        "I live alone can I get a discount?",
    ]

    for query in test_queries:
        result = classifier.classify(query, selected_service="bin_collection")

        print(f"\nQuery: {query}")
        print(f"Predicted intent: {result['intent']}")
        print(f"Confidence: {result['confidence']:.3f}")
        print("Candidates:")
        for item in result["candidates"]:
            print(
                f"  - {item['intent']} | confidence={item['confidence']:.3f} "
                f"| live_lookup={item['needs_live_lookup']} | example={item['top_example']}"
            )