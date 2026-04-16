"""
Backwards-compatible paraphrase entry point.

The real enhancement logic now lives in backend.llm.response_enhancer.
This module delegates to it so existing call sites keep working unchanged.
"""
from __future__ import annotations


def paraphrase_answer(answer: str) -> str:
    """
    Enhance *answer* using the LLM ResponseEnhancer.
    Falls back to the original string if enhancement fails.
    """
    clean = (answer or "").strip()
    if not clean:
        return answer

    try:
        from backend.llm.response_enhancer import ResponseEnhancer
        enhanced = ResponseEnhancer().enhance(raw_answer=clean, user_query="")
        return enhanced if enhanced else clean
    except Exception as exc:
        print(f"[paraphrase_service] Enhancement failed, using original: {exc}")
        return clean
