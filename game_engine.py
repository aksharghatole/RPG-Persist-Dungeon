"""Deterministic RPG mechanics. AI output never mutates these values directly."""
import random
import re
from math import floor
from typing import Any

from models import Character, Enemy, Item


def roll_dice(sides: int, count: int = 1) -> int:
    if sides not in (4, 6, 8, 10, 12, 20) or count < 1:
        raise ValueError("Unsupported dice configuration")
    return sum(random.randint(1, sides) for _ in range(count))


def roll_d20() -> int:
    return roll_dice(20)


def ability_modifier(stat: int) -> int:
    return floor((stat - 10) / 2)


def xp_to_next_level(level: int) -> int:
    return level * 300


def award_xp(character: Character, amount: int) -> list[str]:
    messages = []
    character.xp += max(0, amount)
    while character.xp >= xp_to_next_level(character.level):
        character.xp -= xp_to_next_level(character.level)
        character.level += 1
        character.max_hp += 5
        character.hp = character.max_hp
        messages.append(f"Level up! You are now level {character.level}.")
    return messages


def starting_character(name: str, race: str, character_class: str, background: str, custom: str = "") -> Character:
    character = Character(name=name.strip() or "Unnamed Hero", race=race, character_class=character_class,
                          background=background, custom_description=custom)
    for stat, amount in {"Elf": {"dexterity": 2, "intelligence": 1}, "Dwarf": {"constitution": 2, "strength": 1},
        "Orc": {"strength": 2, "constitution": 1}, "Halfling": {"dexterity": 2, "charisma": 1},
        "Dragonborn": {"strength": 2, "charisma": 1}, "Tiefling": {"intelligence": 1, "charisma": 2}}.get(race, {}).items():
        setattr(character, stat, getattr(character, stat) + amount)
    for stat, amount in {"Warrior": {"strength": 2, "constitution": 1}, "Mage": {"intelligence": 2, "wisdom": 1},
        "Rogue": {"dexterity": 2, "charisma": 1}, "Ranger": {"dexterity": 2, "wisdom": 1},
        "Paladin": {"strength": 1, "charisma": 2}, "Cleric": {"wisdom": 2, "constitution": 1},
        "Warlock": {"charisma": 2, "intelligence": 1}}.get(character_class, {}).items():
        setattr(character, stat, getattr(character, stat) + amount)
    character.max_hp = 20 + character.constitution
    character.hp = character.max_hp
    character.gold = 30 if background in ("Noble", "Merchant") else 20
    return character


def default_inventory(character_class: str) -> list[Item]:
    weapon = "Spellbook" if character_class == "Mage" else "Iron Sword"
    damage = "1d6" if weapon == "Spellbook" else "1d8"
    return [Item(weapon, "A reliable starting weapon.", item_type="Weapon", damage=damage),
            Item("Health Potion", "Restores 10 HP.", 2, "Consumable"),
            Item("Old Map", "A weathered map marked with a black symbol.", 1, "Quest Item")]


def parse_damage(expression: str) -> int:
    match = re.fullmatch(r"(\d+)d(\d+)(?:\+(\d+))?", expression.lower().strip())
    if not match:
        return 0
    return roll_dice(int(match.group(2)), int(match.group(1))) + int(match.group(3) or 0)


def ability_for_action(action: str) -> tuple[str, str] | None:
    rules = (("persuad", "CHA"), ("convinc", "CHA"), ("intimidat", "STR"), ("sneak", "DEX"),
             ("hide", "DEX"), ("climb", "STR"), ("search", "WIS"), ("inspect", "WIS"),
             ("cast", "INT"), ("decipher", "INT"))
    for word, stat in rules:
        if word in action.lower():
            return word, stat
    return None


def resolve_action(action: str, character: Character, inventory: list[Item], enemy: Enemy | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"events": [], "enemy": enemy, "inventory": inventory, "character": character}
    lowered = action.lower()
    if enemy and any(word in lowered for word in ("attack", "strike", "hit", "swing", "fireball")):
        weapon = next((item for item in inventory if item.item_type.lower() == "weapon"), None)
        attack_roll = roll_d20()
        modifier = ability_modifier(character.strength if weapon and weapon.name != "Spellbook" else character.intelligence)
        total = attack_roll + modifier
        result["events"].append(f"Attack roll: {attack_roll} {modifier:+d} = {total} vs Defense {enemy.defense}")
        if total >= enemy.defense:
            damage = parse_damage(weapon.damage if weapon else "1d6") + max(0, modifier)
            enemy.hp = max(0, enemy.hp - damage)
            result["events"].append(f"Hit for {damage} damage. {enemy.name}: {enemy.hp}/{enemy.max_hp} HP.")
            if enemy.hp == 0:
                result["events"].append(f"{enemy.name} is defeated.")
                result["xp_awarded"] = 100
        else:
            result["events"].append("The attack misses.")
        return result
    if enemy and any(word in lowered for word in ("run", "flee", "escape")):
        roll = roll_d20() + ability_modifier(character.dexterity)
        result["events"].append(f"Escape check: {roll} vs 12. " + ("You escape." if roll >= 12 else "You fail to get away."))
        return result
    if any(word in lowered for word in ("drink", "use", "consume")) and "potion" in lowered:
        potion = next((item for item in inventory if "potion" in item.name.lower() and item.quantity > 0), None)
        if potion:
            healed = min(10, character.max_hp - character.hp)
            character.hp += healed
            potion.quantity -= 1
            result["events"].append(f"You use a Health Potion and recover {healed} HP.")
        else:
            result["events"].append("You have no health potion.")
        return result
    ability = ability_for_action(action)
    if ability:
        label, stat_name = ability
        stat = character.stats()[stat_name]
        roll = roll_d20()
        difficulty = 14
        total = roll + ability_modifier(stat)
        result["events"].append(f"{label.title()} check: {roll} {ability_modifier(stat):+d} = {total} vs {difficulty}. "
                                 + ("SUCCESS" if total >= difficulty else "FAILURE"))
    return result
