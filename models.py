"""Data models for the Ashen Kingdom campaign state."""
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Item:
    name: str
    description: str
    quantity: int = 1
    item_type: str = "misc"
    damage: str = ""


@dataclass
class Character:
    name: str
    race: str
    character_class: str
    background: str
    custom_description: str = ""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    hp: int = 10
    max_hp: int = 10
    level: int = 1
    xp: int = 0
    gold: int = 20

    def stats(self) -> dict[str, int]:
        return {key.upper(): value for key, value in {"str": self.strength, "dex": self.dexterity,
                "con": self.constitution, "int": self.intelligence, "wis": self.wisdom,
                "cha": self.charisma}.items()}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        return cls(**data)


@dataclass
class Enemy:
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    damage: str = "1d6"
    description: str = ""


@dataclass
class Quest:
    name: str
    description: str
    status: str = "Unknown"
    objectives: list[str] = field(default_factory=list)
    rewards: str = ""


@dataclass
class NPC:
    name: str
    role: str
    personality: str
    location: str
    relationship: int = 0
    facts: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    alive: bool = True
