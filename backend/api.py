import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.services.chat_engine import ChatEngine


app = FastAPI()


def _prebuild_embedding_caches() -> None:
    """
    Pre-build embedding caches for all service datasets in the background.
    Runs once at startup so first queries don't pay the embedding generation cost.
    Silently skips any service that has no FAQ files.
    """
    try:
        from backend.embeddings.cache_builder import build_all_caches
        _datasets = Path(__file__).resolve().parent.parent / "datasets"
        _cache_dir = Path(__file__).resolve().parent.parent / ".embedding_cache"
        build_all_caches(datasets_path=_datasets, cache_dir=_cache_dir, force=False)
    except Exception as exc:
        print(f"[Startup] Embedding pre-build failed (non-fatal): {exc}")


# Trigger cache build in a daemon thread — does not block server startup
threading.Thread(target=_prebuild_embedding_caches, daemon=True).start()

# Allow all origins in production (Railway domain + any friends' browsers).
# In dev, restrict to localhost only.
_IS_PROD = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER") or os.getenv("FLY_APP_NAME")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _IS_PROD else [],
    allow_origin_regex=None if _IS_PROD else r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent
engine = ChatEngine(BACKEND_ROOT)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    input_type: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    messages: Optional[List[Dict[str, Any]]] = None


@app.get("/")
def root():
    return {"message": "API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


def _normalize_options(result: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    raw_options = result.get("options")

    if raw_options is None:
        raw_addresses = result.get("addresses")
        if isinstance(raw_addresses, list):
            raw_options = raw_addresses

    if raw_options is None:
        raw_allowed_values = result.get("allowed_values")
        if isinstance(raw_allowed_values, list):
            raw_options = raw_allowed_values

    if not isinstance(raw_options, list):
        return None

    options: List[Dict[str, Any]] = []

    for item in raw_options:
        if isinstance(item, dict):
            option_id = str(
                item.get("id")
                or item.get("uprn")
                or item.get("value")
                or ""
            ).strip()

            option_label = str(
                item.get("label")
                or item.get("text")
                or option_id
            ).strip()

            if not option_id and not option_label:
                continue

            normalized_item: Dict[str, Any] = {
                "id": option_id or option_label,
                "uprn": str(item.get("uprn") or option_id or option_label).strip(),
                "label": option_label or option_id,
                "value": str(item.get("value") or option_id or option_label).strip(),
            }

            if "band" in item:
                normalized_item["band"] = item.get("band")
            if "url" in item:
                normalized_item["url"] = item.get("url")
            if "display_index" in item:
                normalized_item["display_index"] = item.get("display_index")

            options.append(normalized_item)
        else:
            value = str(item).strip()
            if not value:
                continue

            options.append(
                {
                    "id": value,
                    "uprn": value,
                    "label": value,
                    "value": value,
                }
            )

    return options or None


def _normalize_input_type(result: Dict[str, Any]) -> Optional[str]:
    input_type = result.get("input_type")
    if input_type:
        return str(input_type)

    response_type = result.get("response_type")
    if response_type:
        return str(response_type)

    if isinstance(result.get("addresses"), list) and result.get("addresses"):
        return "options"

    if isinstance(result.get("options"), list) and result.get("options"):
        return "options"

    if isinstance(result.get("allowed_values"), list) and result.get("allowed_values"):
        return "options"

    return None


def _normalize_messages(result: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    raw_messages = result.get("messages")
    if not isinstance(raw_messages, list):
        return None

    messages: List[Dict[str, Any]] = []

    for item in raw_messages:
        if isinstance(item, dict):
            messages.append(
                {
                    "reply": str(item.get("reply", "")).strip(),
                    "input_type": item.get("input_type"),
                    "options": item.get("options"),
                    "isHtml": bool(item.get("isHtml", False)),
                }
            )
        else:
            messages.append(
                {
                    "reply": str(item).strip(),
                    "input_type": None,
                    "options": None,
                    "isHtml": False,
                }
            )

    return messages or None


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    user_message = request.message.strip()

    result = engine.process_message(
        user_input=user_message,
        session_id=request.session_id,
    )

    input_type = _normalize_input_type(result)
    options = _normalize_options(result)
    messages = _normalize_messages(result)

    reply_text = str(result.get("reply", "")).strip()
    if not reply_text and messages:
        reply_text = str(messages[0].get("reply", "")).strip()

    print("USER MESSAGE:", user_message)
    print("API RESULT:", result)
    print("API INPUT TYPE SENT TO FRONTEND:", input_type)
    print("API OPTIONS SENT TO FRONTEND:", options)
    print("API MESSAGES SENT TO FRONTEND:", messages)

    return ChatResponse(
        reply=reply_text,
        session_id=request.session_id,
        input_type=input_type,
        options=options,
        messages=messages,
    )


# ── Serve React frontend (production) ────────────────────────────────────────
# Must come AFTER all API routes so /chat, /health etc. still hit the API.
_FRONTEND_BUILD = PROJECT_ROOT / "frontend" / "build"
if _FRONTEND_BUILD.exists():
    # Serve JS/CSS/media assets at /static/*
    app.mount(
        "/static",
        StaticFiles(directory=_FRONTEND_BUILD / "static"),
        name="frontend-static",
    )

    @app.get("/{full_path:path}")
    def serve_react(full_path: str):
        """Catch-all: return index.html so React Router handles navigation."""
        return FileResponse(_FRONTEND_BUILD / "index.html")