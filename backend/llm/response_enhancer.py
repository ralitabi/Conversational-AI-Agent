"""
LLM-powered response enhancement.

Takes a raw FAQ answer (verified, factually correct) and asks GPT-4o-mini
to present it as a clear, well-structured, helpful council response —
without adding new facts or changing any figures.

A separate prompt template is used for each service area so the tone
and structure are right for that context.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.openai_client import client
from backend.llm.prompts import (
    BRADFORD_SYSTEM_PROMPT,
    BENEFITS_PROMPT_TEMPLATE,
    BIN_GUIDANCE_PROMPT_TEMPLATE,
    BLUE_BADGE_PROMPT_TEMPLATE,
    COUNCIL_TAX_PROMPT_TEMPLATE,
    ENHANCEMENT_PROMPT_TEMPLATE,
    LIBRARY_PROMPT_TEMPLATE,
    SCHOOL_ADMISSIONS_PROMPT_TEMPLATE,
    INTENT_DISPLAY_NAMES,
    SERVICE_DISPLAY_NAMES,
)

_MODEL       = "gpt-4o-mini"
_TEMPERATURE = 0.0           # Deterministic — fastest + most consistent
_MAX_TOKENS  = 220           # Tight cap for fast responses (< 1s generation)


class ResponseEnhancer:
    """
    Enhances a raw FAQ answer using a targeted LLM prompt.
    Falls back silently to the original answer if the API call fails.
    """

    def enhance(
        self,
        raw_answer: str,
        user_query: str,
        service: Optional[str] = None,
        intent: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Return an enhanced version of *raw_answer*, or the original if enhancement fails.

        Args:
            raw_answer:  The verified answer from the FAQ / knowledge base.
            user_query:  The exact question the resident asked.
            service:     Service key (e.g. "council_tax", "benefits_support").
            intent:      Detected intent key (e.g. "council_tax_payment").
            context:     Session context dict (band, balance, postcode, etc.).
        """
        raw_answer = (raw_answer or "").strip()
        if not raw_answer:
            return raw_answer

        try:
            user_prompt = self._build_user_prompt(
                raw_answer=raw_answer,
                user_query=user_query or "",
                service=service or "",
                intent=intent or "",
                context=context or {},
            )

            response = client.chat.completions.create(
                model=_MODEL,
                temperature=_TEMPERATURE,
                max_tokens=_MAX_TOKENS,
                messages=[
                    {"role": "system", "content": BRADFORD_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
            )

            enhanced = (response.choices[0].message.content or "").strip()
            return enhanced if enhanced else raw_answer

        except Exception as exc:
            print(f"[ResponseEnhancer] Enhancement failed, using original: {exc}")
            return raw_answer

    # ── Private ────────────────────────────────────────────────────────────────

    def _build_user_prompt(
        self,
        raw_answer: str,
        user_query: str,
        service: str,
        intent: str,
        context: Dict[str, Any],
    ) -> str:
        service_display  = SERVICE_DISPLAY_NAMES.get(service, service.replace("_", " ").title())
        intent_display   = INTENT_DISPLAY_NAMES.get(intent, intent.replace("_", " ").title())
        intent_line      = f"Topic: {intent_display}\n" if intent_display else ""
        context_line     = self._format_context(context)

        # Pick the most specific template for the service
        if service == "blue_badge":
            return BLUE_BADGE_PROMPT_TEMPLATE.format(
                user_query=user_query,
                raw_answer=raw_answer,
                intent_display=intent_display,
            )

        if service in {"bin_collection", "bins"}:
            return BIN_GUIDANCE_PROMPT_TEMPLATE.format(
                user_query=user_query,
                raw_answer=raw_answer,
            )

        if service == "council_tax":
            return COUNCIL_TAX_PROMPT_TEMPLATE.format(
                user_query=user_query,
                raw_answer=raw_answer,
                intent_display=intent_display,
                context_line=context_line,
            )

        if service == "benefits_support":
            return BENEFITS_PROMPT_TEMPLATE.format(
                user_query=user_query,
                raw_answer=raw_answer,
                intent_display=intent_display,
                context_line=context_line,
            )

        if service == "school_admissions":
            return SCHOOL_ADMISSIONS_PROMPT_TEMPLATE.format(
                user_query=user_query,
                raw_answer=raw_answer,
                intent_display=intent_display,
            )

        if service == "libraries":
            return LIBRARY_PROMPT_TEMPLATE.format(
                user_query=user_query,
                raw_answer=raw_answer,
                intent_display=intent_display,
            )

        # Generic fallback template
        return ENHANCEMENT_PROMPT_TEMPLATE.format(
            user_query=user_query,
            raw_answer=raw_answer,
            service_display=service_display,
            intent_line=intent_line,
            context_line=context_line,
        )

    @staticmethod
    def _format_context(context: Dict[str, Any]) -> str:
        """Build a short plain-English context line from session data."""
        parts = []
        if context.get("band"):
            parts.append(f"Council Tax band: {context['band']}")
        if context.get("balance"):
            parts.append(f"Outstanding balance: £{context['balance']}")
        if context.get("postcode"):
            parts.append(f"Postcode: {context['postcode']}")
        if context.get("selected_address"):
            parts.append(f"Address: {context['selected_address']}")
        if not parts:
            return ""
        return "Resident context: " + ", ".join(parts) + ".\n"
