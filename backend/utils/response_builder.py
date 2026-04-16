from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_messages_reply(
    messages: List[Dict[str, Any]],
    input_type: Optional[str] = None,
    allowed_values: Optional[List[str]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Return a response with a ``messages`` array for sequential multi-bubble rendering."""
    response: Dict[str, Any] = {
        "messages": messages,
        "reply": messages[0].get("reply", "") if messages else "",
        "input_type": input_type,
        "allowed_values": allowed_values,
    }
    response.update(extra)
    return response


def build_response(
    reply: str,
    input_type: Optional[str] = None,
    allowed_values: Optional[List[str]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "reply": reply,
        "input_type": input_type,
        "allowed_values": allowed_values,
    }

    response.update(extra)
    return response


def build_reply(
    reply: str,
    input_type: Optional[str] = None,
    allowed_values: Optional[List[str]] = None,
    **extra: Any,
) -> Dict[str, Any]:
    return build_response(
        reply=reply,
        input_type=input_type,
        allowed_values=allowed_values,
        **extra,
    )