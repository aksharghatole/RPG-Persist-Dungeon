"""Compact, structured context for the Dungeon Master prompt."""
import json
import os
from typing import Any


def get_recent_messages(messages: list[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    return messages[-(limit or int(os.getenv("MAX_RECENT_MESSAGES", "20"))):]


def get_relevant_memories(state: dict[str, Any]) -> dict[str, Any]:
    return {"location": state.get("campaign", {}).get("location", "Blackthorn Village"),
            "npcs": state.get("npcs", []), "quests": state.get("quests", []), "events": state.get("events", [])[-12:]}


def build_ai_context(state: dict[str, Any], latest_action: str) -> str:
    return json.dumps({"character": state.get("character", {}), "world": get_relevant_memories(state),
                       "recent_conversation": get_recent_messages(state.get("messages", [])),
                       "player_action": latest_action}, indent=2)


def add_memory(state: dict[str, Any], text: str) -> None:
    state.setdefault("events", []).append({"text": text})


def update_memory(state: dict[str, Any], text: str) -> None:
    add_memory(state, text)
