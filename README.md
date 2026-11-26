# AI Dungeon Master

[Play locally](#installation-and-running) · [Features](#features) · [Tests](#tests)

AI Dungeon Master is a local, chat-based fantasy RPG set in **The Ashen Kingdom**. You create a character, enter the storm outside Blackthorn Village, and describe any action in natural language. SQLite remembers your character, inventory, NPCs, quests, events, messages, and current location between sessions.

## Features

- Streamlit chat interface with a focused fantasy UI
- Character creation with race, class, background, stats, HP, gold, and level progression
- Deterministic d4/d6/d8/d10/d12/d20 checks, combat foundations, damage, XP, leveling, and potion use
- Structured campaign persistence in SQLite
- Bounded AI context with recent conversation and relevant world state
- OpenAI-compatible provider with a useful no-key local fallback
- Campaign create, load, save, and delete
- `/inventory`, `/stats`, `/quests`, `/location`, `/save`, and `/help` commands

## Architecture

`app.py` owns the Streamlit workflow. `game_engine.py` owns mechanics. `database.py` owns SQLite records. `memory.py` composes compact AI context. `ai_dm.py` owns the OpenAI-compatible provider. `models.py` contains state types and `prompts.py` contains DM instructions.

## Installation and running

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Set `OPENAI_API_KEY` in `.env` for AI narration. `OPENAI_BASE_URL` supports compatible providers and `OPENAI_MODEL` selects the model. Without a key, the app remains playable using its local narrator and mechanics.

## GitHub Codespaces

Open the repository in Codespaces, run the installation commands above, add the key to `.env`, and run `streamlit run app.py`. No Docker, GPU, or local model is required. Streamlit will offer its forwarded port in the Codespaces panel.

## How memory works

Each campaign has normalized SQLite tables for campaigns, characters, inventory, NPCs, quests, locations, events, and messages. The AI receives the character, current location, relevant records, the last `MAX_RECENT_MESSAGES` messages, and the latest action instead of unbounded history. Python validates and applies all mechanical state changes.

## Tests

```bash
pytest -q
```

## Future features

Interactive maps, AI character portraits, voice narration, music, procedural world generation, multiplayer, faction system, advanced combat, richer relationship system, and campaign sharing.
