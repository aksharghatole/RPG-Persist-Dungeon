"""OpenAI-compatible narration provider with a safe local fallback."""
import json
import os
from typing import Any

from memory import build_ai_context
from prompts import SYSTEM_PROMPT


def _fallback(action: str, events: list[str], location: str) -> str:
    mechanical = " ".join(events)
    return (f"At {location}, your choice draws the world's attention. {mechanical} The storm presses close as the "
            f"consequences of '{action}' begin to take shape. What do you do next?").strip()


def narrate(state: dict[str, Any], action: str, events: list[str] | None = None) -> str:
    events = events or []
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _fallback(action, events, state.get("campaign", {}).get("location", "Blackthorn Village"))
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
        response = client.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.8,
            response_format={"type": "json_object"}, messages=[{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_ai_context(state, action) + "\nMechanical results: " + json.dumps(events)}])
        payload = json.loads(response.choices[0].message.content or "{}")
        narration = payload.get("narration")
        return narration if isinstance(narration, str) and narration.strip() else _fallback(action, events, "Blackthorn Village")
    except Exception:
        return _fallback(action, events, state.get("campaign", {}).get("location", "Blackthorn Village"))
