from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


class SessionManager:
    def __init__(self, chat_logs_dir: str = "chat_logs", max_recent_messages: int = 10) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.lock = Lock()
        self.max_recent_messages = max_recent_messages

        self.chat_logs_dir = Path(chat_logs_dir)
        self.chat_logs_dir.mkdir(parents=True, exist_ok=True)

    # =========================================================
    # DEFAULT SESSION STATE
    # =========================================================
    def new_session_state(self) -> dict[str, Any]:
        return {
            # ---------------- EXISTING FLOW STATE ----------------
            "selected_service": None,
            "active_intent": None,
            "current_step_id": None,
            "collected_slots": {},
            "awaiting_intent_choice": False,
            "excluded_intent_choice": None,
            "skip_fallback_once": False,
            "awaiting_confirmation_type": None,
            "pending_predicted_intent": None,
            "last_question_text": None,
            "bin_flow_stage": None,
            "bin_postcode": None,
            "bin_addresses": [],
            "bin_selected_uprn": None,

            # ---------------- EXTRA FLAGS USED ELSEWHERE ----------------
            "awaiting_feedback": False,
            "bin_task_completed": False,

            # ---------------- COUNCIL TAX FLOW STATE ----------------
            "pending_action": None,
            "council_tax_addresses": [],
            "council_tax_postcode": None,
            "band": None,
            "balance": None,
            "selected_address": None,
            "postcode": None,

            # ---------------- NEW MEMORY STATE ----------------
            "memory": {
                "user_profile": {
                    "preferred_language": "English",
                    "preferred_format": "simple"
                },
                "current_task": {
                    "service": None,
                    "selected_address": None,
                    "uprn": None,
                    "last_council_link": None,
                    "feedback_requested": False
                },
                "conversation_summary": "",
                "recent_messages": []
            },

            # ---------------- FULL CHAT HISTORY ----------------
            "full_chat_history": []
        }

    # =========================================================
    # SESSION ACCESS
    # =========================================================
    def get_or_create_session(self, session_id: str) -> dict[str, Any]:
        if not session_id:
            raise ValueError("session_id is required")

        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = self.new_session_state()
                self.sessions[session_id]["session_id"] = session_id
            return self.sessions[session_id]

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self.get_or_create_session(session_id)

    def reset_session(self, session_id: str) -> None:
        with self.lock:
            self.sessions[session_id] = self.new_session_state()

    def clear_session(self, session_id: str) -> None:
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]

    # =========================================================
    # MEMORY ACCESS
    # =========================================================
    def get_memory(self, session_id: str) -> dict[str, Any]:
        session = self.get_or_create_session(session_id)
        return deepcopy(session["memory"])

    def update_task(self, session_id: str, **kwargs: Any) -> None:
        session = self.get_or_create_session(session_id)
        task = session["memory"]["current_task"]

        with self.lock:
            for key, value in kwargs.items():
                if key in task:
                    task[key] = value

            self._sync_memory_with_existing_state(session)
            self._update_summary(session)

    def update_user_profile(self, session_id: str, **kwargs: Any) -> None:
        session = self.get_or_create_session(session_id)
        profile = session["memory"]["user_profile"]

        with self.lock:
            for key, value in kwargs.items():
                if key in profile:
                    profile[key] = value

            self._update_summary(session)

    # =========================================================
    # CHAT STORAGE
    # =========================================================
    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self.get_or_create_session(session_id)

        cleaned_content = content.strip() if isinstance(content, str) else str(content)
        timestamp = datetime.utcnow().isoformat() + "Z"

        message = {
            "timestamp": timestamp,
            "role": role,
            "content": cleaned_content
        }

        with self.lock:
            # Store in short-term recent memory
            session["memory"]["recent_messages"].append(message)
            if len(session["memory"]["recent_messages"]) > self.max_recent_messages:
                session["memory"]["recent_messages"] = session["memory"]["recent_messages"][-self.max_recent_messages:]

            # Store full chat history in session
            session["full_chat_history"].append(message)

            self._update_summary(session)

        # Save full history entry to external file
        self._append_chat_log(session_id, message)

    def get_full_chat_history(self, session_id: str) -> list[dict[str, Any]]:
        session = self.get_or_create_session(session_id)
        return deepcopy(session["full_chat_history"])

    # =========================================================
    # FILE LOGGING
    # =========================================================
    def _get_chat_log_file(self, session_id: str) -> Path:
        safe_session_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        safe_session_id = safe_session_id or "default"
        return self.chat_logs_dir / f"{safe_session_id}.jsonl"

    def _append_chat_log(self, session_id: str, message: dict[str, Any]) -> None:
        log_file = self._get_chat_log_file(session_id)

        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

    def export_full_chat_history(self, session_id: str) -> str:
        """
        Optional helper to save the whole current in-memory history
        into a pretty JSON file as well.
        """
        session = self.get_or_create_session(session_id)
        export_path = self.chat_logs_dir / f"{session_id}_full_history.json"

        with export_path.open("w", encoding="utf-8") as f:
            json.dump(session["full_chat_history"], f, indent=2, ensure_ascii=False)

        return str(export_path)

    # =========================================================
    # STATE RESET HELPERS
    # =========================================================
    def clear_guidance_state(self, session: dict[str, Any]) -> None:
        session["awaiting_intent_choice"] = False
        session["excluded_intent_choice"] = None
        session["skip_fallback_once"] = False
        session["awaiting_confirmation_type"] = None
        session["pending_predicted_intent"] = None

    def reset_flow_state(self, session: dict[str, Any]) -> None:
        session["active_intent"] = None
        session["current_step_id"] = None
        session["collected_slots"] = {}

    def reset_bin_flow_state(self, session: dict[str, Any]) -> None:
        session["bin_flow_stage"] = None
        session["bin_postcode"] = None
        session["bin_addresses"] = []
        session["bin_selected_uprn"] = None

    def reset_service_context(self, session: dict[str, Any]) -> None:
        session["selected_service"] = None
        session["last_question_text"] = None
        self.reset_flow_state(session)
        self.reset_bin_flow_state(session)
        self.clear_guidance_state(session)

        # Also clear task memory related to active flow
        session["memory"]["current_task"]["service"] = None
        session["memory"]["current_task"]["selected_address"] = None
        session["memory"]["current_task"]["uprn"] = None
        session["memory"]["current_task"]["last_council_link"] = None
        session["memory"]["current_task"]["feedback_requested"] = False

        self._update_summary(session)

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================
    def _sync_memory_with_existing_state(self, session: dict[str, Any]) -> None:
        """
        Keeps new memory state aligned with your existing session fields.
        """
        current_task = session["memory"]["current_task"]

        if session.get("selected_service") and not current_task.get("service"):
            current_task["service"] = session["selected_service"]

        if session.get("bin_selected_uprn"):
            current_task["uprn"] = session["bin_selected_uprn"]

        if current_task.get("uprn") and session.get("bin_addresses"):
            selected = next(
                (
                    address for address in session["bin_addresses"]
                    if address.get("uprn") == current_task["uprn"]
                ),
                None,
            )
            if selected:
                current_task["selected_address"] = selected.get("label")

    def _update_summary(self, session: dict[str, Any]) -> None:
        memory = session["memory"]
        task = memory["current_task"]
        profile = memory["user_profile"]

        summary_parts: list[str] = [
            f"Language: {profile.get('preferred_language')}",
            f"Format: {profile.get('preferred_format')}",
        ]

        if task.get("service"):
            summary_parts.append(f"Service: {task['service']}")

        if task.get("selected_address"):
            summary_parts.append(f"Address: {task['selected_address']}")

        if task.get("uprn"):
            summary_parts.append(f"UPRN: {task['uprn']}")

        if task.get("last_council_link"):
            summary_parts.append("Council link already shared")

        if task.get("feedback_requested"):
            summary_parts.append("Feedback requested")

        if session.get("active_intent"):
            summary_parts.append(f"Active intent: {session['active_intent']}")

        if session.get("bin_flow_stage"):
            summary_parts.append(f"Bin stage: {session['bin_flow_stage']}")

        memory["conversation_summary"] = " | ".join(summary_parts)


# Shared instance
session_manager = SessionManager()