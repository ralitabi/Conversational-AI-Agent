from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class DialogueManager:
    """
    Dataset-driven dialogue manager.

    Supported dataset structure:
        datasets/
            <service_name>/
                *_dialogue.json

    Supported JSON format:
    {
      "intent_name": {
        "steps": [
          "Question 1",
          "Question 2"
        ],
        "completion_mode": "rag"
      }
    }

    This manager keeps a very simple contract so it stays compatible with
    the rest of the backend:
    - get_first_response(intent_name)
    - continue_flow(intent_name, current_step_id, user_input, slots)

    Returned payloads include:
    - current_step_id
    - message
    - slots
    - flow_complete
    - input_type
    - slot_name
    - allowed_values
    """

    def __init__(self, datasets_root: str | Path) -> None:
        self.datasets_root = Path(datasets_root)

    # -------------------------------------------------------------------------
    # File discovery and loading
    # -------------------------------------------------------------------------

    def _find_dialogue_file(self, intent_name: str) -> Optional[Path]:
        if not self.datasets_root.exists():
            return None

        for json_file in self.datasets_root.glob("*/*.json"):
            if "dialogue" not in json_file.stem.lower():
                continue

            try:
                data = self._load_json(json_file)
            except Exception:
                continue

            if not isinstance(data, dict):
                continue

            if intent_name in data:
                return json_file

        return None

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_dialogue_data(self, dialogue_file: Path) -> Dict[str, Any]:
        data = self._load_json(dialogue_file)
        if not isinstance(data, dict):
            return {}
        return data

    # -------------------------------------------------------------------------
    # Flow helpers
    # -------------------------------------------------------------------------

    def _get_flow_config(self, data: Dict[str, Any], intent_name: str) -> Dict[str, Any]:
        config = data.get(intent_name, {})
        if not isinstance(config, dict):
            return {}
        return config

    def _get_flow_steps(self, data: Dict[str, Any], intent_name: str) -> List[Dict[str, Any]]:
        """
        Converts simple string step lists into normalized internal step objects.
        """
        flow_config = self._get_flow_config(data, intent_name)
        raw_steps = flow_config.get("steps", [])

        if not isinstance(raw_steps, list):
            return []

        normalized_steps: List[Dict[str, Any]] = []

        for index, item in enumerate(raw_steps, start=1):
            step_id = f"{intent_name}_step_{index}"

            if isinstance(item, str):
                normalized_steps.append(
                    {
                        "step_id": step_id,
                        "type": "question",
                        "message": item,
                    }
                )
            elif isinstance(item, dict):
                normalized_steps.append(
                    {
                        "step_id": item.get("step_id", step_id),
                        "type": item.get("type", "question"),
                        "message": item.get("message", "No message found."),
                        "slot": item.get("slot"),
                        "input_type": item.get("input_type"),
                        "allowed_values": item.get("allowed_values"),
                    }
                )

        return normalized_steps

    def _get_completion_mode(self, data: Dict[str, Any], intent_name: str) -> str:
        flow_config = self._get_flow_config(data, intent_name)
        completion_mode = flow_config.get("completion_mode", "rag")
        if not isinstance(completion_mode, str) or not completion_mode.strip():
            return "rag"
        return completion_mode.strip()

    def _find_step_index_by_id(self, steps: List[Dict[str, Any]], step_id: str) -> int:
        for index, step in enumerate(steps):
            if step.get("step_id") == step_id:
                return index
        return -1

    # -------------------------------------------------------------------------
    # Response builders
    # -------------------------------------------------------------------------

    def _build_response(
        self,
        *,
        intent_name: str,
        dialogue_file: Path,
        step: Dict[str, Any],
        slots: Dict[str, Any],
        flow_complete: bool,
        completion_mode: str,
    ) -> Dict[str, Any]:
        return {
            "intent": intent_name,
            "status": "ok",
            "dialogue_file": str(dialogue_file),
            "current_step_id": step.get("step_id"),
            "step_type": step.get("type", "question"),
            "message": step.get("message", "No message found."),
            "full_step": step,
            "slots": slots,
            "flow_complete": flow_complete,
            "input_type": step.get("input_type"),
            "slot_name": step.get("slot"),
            "allowed_values": step.get("allowed_values"),
            "completion_mode": completion_mode,
        }

    def _build_error_response(
        self,
        *,
        intent_name: str,
        message: str,
        slots: Optional[Dict[str, Any]] = None,
        flow_complete: bool = True,
    ) -> Dict[str, Any]:
        return {
            "intent": intent_name,
            "status": "error",
            "message": message,
            "slots": slots or {},
            "flow_complete": flow_complete,
            "input_type": None,
            "slot_name": None,
            "allowed_values": None,
            "completion_mode": "rag",
        }

    def _build_complete_response(
        self,
        *,
        intent_name: str,
        dialogue_file: Path,
        current_step_id: str,
        slots: Dict[str, Any],
        completion_mode: str,
    ) -> Dict[str, Any]:
        return {
            "intent": intent_name,
            "status": "ok",
            "dialogue_file": str(dialogue_file),
            "current_step_id": current_step_id,
            "step_type": "complete",
            "message": "This request flow is complete.",
            "full_step": {},
            "slots": slots,
            "flow_complete": True,
            "input_type": None,
            "slot_name": None,
            "allowed_values": None,
            "completion_mode": completion_mode,
        }

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_first_response(self, intent_name: str) -> Dict[str, Any]:
        dialogue_file = self._find_dialogue_file(intent_name)
        if dialogue_file is None:
            return self._build_error_response(
                intent_name=intent_name,
                message="No dialogue flow found for this intent.",
            )

        data = self._load_dialogue_data(dialogue_file)
        steps = self._get_flow_steps(data, intent_name)
        completion_mode = self._get_completion_mode(data, intent_name)

        if not steps:
            return self._build_error_response(
                intent_name=intent_name,
                message="Dialogue flow exists but has no steps.",
            )

        first_step = steps[0]

        return self._build_response(
            intent_name=intent_name,
            dialogue_file=dialogue_file,
            step=first_step,
            slots={},
            flow_complete=False,
            completion_mode=completion_mode,
        )

    def continue_flow(
        self,
        intent_name: str,
        current_step_id: str,
        user_input: str,
        slots: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        slots = dict(slots or {})

        dialogue_file = self._find_dialogue_file(intent_name)
        if dialogue_file is None:
            return self._build_error_response(
                intent_name=intent_name,
                message="No dialogue flow found for this intent.",
                slots=slots,
            )

        data = self._load_dialogue_data(dialogue_file)
        steps = self._get_flow_steps(data, intent_name)
        completion_mode = self._get_completion_mode(data, intent_name)

        if not steps:
            return self._build_error_response(
                intent_name=intent_name,
                message="Dialogue flow exists but has no steps.",
                slots=slots,
            )

        current_index = self._find_step_index_by_id(steps, current_step_id)
        if current_index == -1:
            return self._build_error_response(
                intent_name=intent_name,
                message=f"Current step '{current_step_id}' not found in flow.",
                slots=slots,
            )

        current_step = steps[current_index]

        # Store answer in slots using step id, so downstream RAG can inspect them.
        slots[current_step_id] = user_input.strip()

        next_index = current_index + 1

        if next_index >= len(steps):
            return self._build_complete_response(
                intent_name=intent_name,
                dialogue_file=dialogue_file,
                current_step_id=current_step_id,
                slots=slots,
                completion_mode=completion_mode,
            )

        next_step = steps[next_index]

        return self._build_response(
            intent_name=intent_name,
            dialogue_file=dialogue_file,
            step=next_step,
            slots=slots,
            flow_complete=False,
            completion_mode=completion_mode,
        )


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    datasets_path = project_root / "datasets"

    manager = DialogueManager(datasets_path)

    test_intent = "report_bin_not_collected_info"

    first = manager.get_first_response(test_intent)
    print("\nFIRST STEP")
    print(first)

    if first["status"] == "ok":
        second = manager.continue_flow(
            intent_name=test_intent,
            current_step_id=first["current_step_id"],
            user_input="yes",
            slots=first["slots"],
        )
        print("\nSECOND STEP")
        print(second)