"""
Retrieval-Augmented Generation service.

Retrieval strategy (in order):
  1. Semantic search via OpenAI embeddings (EmbeddingStore)
  2. Keyword / token-overlap scoring (fallback when embeddings unavailable)

Every matched answer is passed through ResponseEnhancer (GPT-4o-mini)
which rewrites it as a clear, detailed, well-structured council response
without adding new facts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Project root → cache directory ──────────────────────────────────────────
_BACKEND    = Path(__file__).resolve().parent
_PROJECT    = _BACKEND.parent
_CACHE_DIR  = _PROJECT / ".embedding_cache"


def _normalize(value: Optional[str]) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text)


def _tokenize(value: Optional[str]) -> List[str]:
    return re.findall(r"[a-z0-9]+", _normalize(value))


class RAGService:
    def __init__(self, datasets_path: Path) -> None:
        self.datasets_path = Path(datasets_path)

        # ── Semantic search (optional — graceful fallback on failure) ─────
        self._embedding_store = None
        try:
            from backend.embeddings.embedding_store import EmbeddingStore
            self._embedding_store = EmbeddingStore(self.datasets_path, _CACHE_DIR)
            print("[RAGService] EmbeddingStore ready.")
        except Exception as exc:
            print(f"[RAGService] EmbeddingStore unavailable, using keyword fallback: {exc}")

        # ── LLM response enhancer (optional) ─────────────────────────────
        self._enhancer = None
        try:
            from backend.llm.response_enhancer import ResponseEnhancer
            self._enhancer = ResponseEnhancer()
            print("[RAGService] ResponseEnhancer ready.")
        except Exception as exc:
            print(f"[RAGService] ResponseEnhancer unavailable: {exc}")

    # ── Public API ───────────────────────────────────────────────────────────

    def answer_query(
        self,
        query: str,
        service_name: Optional[str] = None,
        intent: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        k: int = 1,
    ) -> Dict[str, Any]:
        """
        Return the best FAQ answer for *query* within *service_name*.
        The answer is enhanced by the LLM before returning.
        """
        if not service_name:
            return {"answer": "Sorry, no service selected.", "matched": False}

        # When the intent classifier already pinpointed the intent, jump straight
        # to keyword search (filtered by that intent).  This avoids an extra
        # OpenAI Embeddings API call and typically returns the same answer.
        if intent:
            best_faq = (
                self._keyword_search(query, service_name, intent)
                or self._semantic_search(query, service_name, None)
            )
        else:
            best_faq = (
                self._semantic_search(query, service_name, None)
                or self._keyword_search(query, service_name, None)
            )

        if not best_faq:
            return {
                "answer": "Sorry, I could not find a relevant answer for that.",
                "matched": False,
            }

        raw_answer = str(best_faq.get("answer", "")).strip()
        if not raw_answer:
            return {"answer": "Sorry, I could not find a relevant answer.", "matched": False}

        # Inject structured session context (band, balance, etc.)
        raw_answer = self._inject_context(raw_answer, context or {})

        # Enhance with LLM
        final_answer = self._enhance(
            raw_answer=raw_answer,
            user_query=query,
            service=service_name,
            intent=intent or best_faq.get("intent"),
            context=context,
        )

        return {
            "answer":     final_answer,
            "matched":    True,
            "intent":     best_faq.get("intent"),
            "topic":      best_faq.get("topic"),
            "source_url": best_faq.get("source_url"),
        }

    # ── Retrieval ────────────────────────────────────────────────────────────

    def _semantic_search(
        self,
        query: str,
        service_name: str,
        intent: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Return the top FAQ via cosine similarity, or None."""
        if not self._embedding_store:
            return None
        try:
            results = self._embedding_store.search(query, service_name, intent, k=5)
            return results[0] if results else None
        except Exception as exc:
            print(f"[RAGService] Semantic search error: {exc}")
            return None

    def _keyword_search(
        self,
        query: str,
        service_name: str,
        intent: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Token-overlap keyword scoring — used when embeddings are unavailable."""
        faqs = self._load_service_faqs(service_name)
        if not faqs:
            return None

        if intent:
            intent_faqs = [f for f in faqs if f.get("intent") == intent]
            if intent_faqs:
                faqs = intent_faqs

        scored = sorted(faqs, key=lambda f: self._keyword_score(query, f), reverse=True)
        best   = scored[0]
        return best if self._keyword_score(query, best) > 0 else None

    def _keyword_score(self, query: str, faq: Dict[str, Any]) -> int:
        q_tokens = set(_tokenize(query))
        score    = len(q_tokens & set(_tokenize(faq.get("question", "")))) * 4
        for kw in faq.get("keywords", []):
            score += len(q_tokens & set(_tokenize(kw))) * 4
        return score

    # ── Enhancement ──────────────────────────────────────────────────────────

    def _enhance(
        self,
        raw_answer: str,
        user_query: str,
        service: Optional[str],
        intent: Optional[str],
        context: Optional[Dict[str, Any]],
    ) -> str:
        if not self._enhancer:
            return raw_answer
        try:
            return self._enhancer.enhance(
                raw_answer=raw_answer,
                user_query=user_query,
                service=service,
                intent=intent,
                context=context,
            ) or raw_answer
        except Exception as exc:
            print(f"[RAGService] Enhancement error: {exc}")
            return raw_answer

    # ── Context injection ────────────────────────────────────────────────────

    @staticmethod
    def _inject_context(answer: str, context: Dict[str, Any]) -> str:
        """Prepend known structured facts so the LLM can reference them."""
        if not context:
            return answer
        prefix_parts = []
        if context.get("band"):
            prefix_parts.append(f"The resident's Council Tax band is {context['band']}.")
        if context.get("balance"):
            prefix_parts.append(f"Their current outstanding balance is £{context['balance']}.")
        if context.get("selected_address"):
            prefix_parts.append(f"Their registered address is: {context['selected_address']}.")
        return (" ".join(prefix_parts) + " " + answer).strip() if prefix_parts else answer

    # ── FAQ loaders ──────────────────────────────────────────────────────────

    def _load_service_faqs(self, service_name: str) -> List[Dict[str, Any]]:
        folder = self._resolve_service_folder(service_name)
        if not folder:
            return []
        faqs: List[Dict[str, Any]] = []
        for faq_path in folder.glob("*_faq.json"):
            faqs.extend(self._load_json_file(faq_path))
        return faqs

    def _resolve_service_folder(self, service_name: str) -> Optional[Path]:
        if not self.datasets_path.exists():
            return None
        target = _normalize(service_name).replace(" ", "").replace("_", "")
        for folder in self.datasets_path.iterdir():
            if folder.is_dir():
                key = _normalize(folder.name).replace(" ", "").replace("_", "")
                if key == target:
                    return folder
        return None

    @staticmethod
    def _load_json_file(file_path: Path) -> List[Dict[str, Any]]:
        try:
            with open(file_path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
            if isinstance(data, dict):
                return data.get("faqs", []) or data.get("data", [])
        except Exception as exc:
            print(f"[RAGService] Failed to load {file_path}: {exc}")
        return []
