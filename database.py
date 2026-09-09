"""SQLite persistence for complete campaign state."""
import json
import sqlite3
from pathlib import Path
from typing import Any

from models import Character, Item, NPC, Quest

DB_PATH = Path(__file__).parent / "data" / "campaigns.db"


class Database:
    def __init__(self, path: str | Path = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY, name TEXT NOT NULL, location TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS characters (campaign_id INTEGER PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS npcs (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS quests (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)

    def list_campaigns(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM campaigns ORDER BY updated_at DESC")]

    def create_campaign(self, name: str, character: Character, inventory: list[Item], npcs: list[NPC],
                        quests: list[Quest], location: str = "Blackthorn Village") -> int:
        with self.connect() as db:
            campaign_id = db.execute("INSERT INTO campaigns(name, location) VALUES (?, ?)", (name, location)).lastrowid
            db.execute("INSERT INTO characters(campaign_id, data) VALUES (?, ?)", (campaign_id, json.dumps(character.to_dict())))
            for table, values in (("inventory", inventory), ("npcs", npcs), ("quests", quests)):
                for value in values:
                    db.execute(f"INSERT INTO {table}(campaign_id, data) VALUES (?, ?)", (campaign_id, json.dumps(value.__dict__)))
            db.execute("INSERT INTO locations(campaign_id, name, data) VALUES (?, ?, ?)", (campaign_id, location, json.dumps({"name": location})))
            return int(campaign_id)

    def save(self, campaign_id: int, character: Character, inventory: list[Item], npcs: list[NPC], quests: list[Quest],
             location: str, event: str | None = None) -> None:
        with self.connect() as db:
            db.execute("UPDATE campaigns SET location = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (location, campaign_id))
            db.execute("UPDATE characters SET data = ? WHERE campaign_id = ?", (json.dumps(character.to_dict()), campaign_id))
            for table, values in (("inventory", inventory), ("npcs", npcs), ("quests", quests)):
                db.execute(f"DELETE FROM {table} WHERE campaign_id = ?", (campaign_id,))
                for value in values:
                    db.execute(f"INSERT INTO {table}(campaign_id, data) VALUES (?, ?)", (campaign_id, json.dumps(value.__dict__)))
            if event:
                db.execute("INSERT INTO events(campaign_id, data) VALUES (?, ?)", (campaign_id, json.dumps({"text": event})))

    def add_message(self, campaign_id: int, role: str, content: str) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO messages(campaign_id, role, content) VALUES (?, ?, ?)", (campaign_id, role, content))
            db.execute("UPDATE campaigns SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))

    def load(self, campaign_id: int) -> dict[str, Any] | None:
        with self.connect() as db:
            campaign = db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
            if not campaign:
                return None
            def rows(table: str) -> list[dict[str, Any]]:
                return [json.loads(row["data"]) for row in db.execute(f"SELECT data FROM {table} WHERE campaign_id = ?", (campaign_id,))]
            character = db.execute("SELECT data FROM characters WHERE campaign_id = ?", (campaign_id,)).fetchone()
            messages = [dict(row) for row in db.execute("SELECT role, content FROM messages WHERE campaign_id = ? ORDER BY id", (campaign_id,))]
            return {"campaign": dict(campaign), "character": json.loads(character[0]), "inventory": rows("inventory"),
                    "npcs": rows("npcs"), "quests": rows("quests"), "messages": messages, "events": rows("events")}

    def delete(self, campaign_id: int) -> None:
        with self.connect() as db:
            for table in ("characters", "inventory", "npcs", "quests", "locations", "events", "messages"):
                db.execute(f"DELETE FROM {table} WHERE campaign_id = ?", (campaign_id,))
            db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
