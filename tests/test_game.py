from pathlib import Path

from database import Database
from game_engine import ability_modifier, award_xp, default_inventory, resolve_action, starting_character
from models import NPC, Quest


def test_modifiers_and_character_creation():
    assert ability_modifier(9) == -1
    character = starting_character("Asha", "Elf", "Mage", "Scholar")
    assert character.intelligence == 13
    assert character.hp == character.max_hp


def test_potion_and_leveling():
    character = starting_character("Asha", "Human", "Warrior", "Adventurer")
    character.hp -= 8
    inventory = default_inventory("Warrior")
    result = resolve_action("I drink a health potion", character, inventory)
    assert character.hp == character.max_hp - 0
    assert inventory[1].quantity == 1
    assert award_xp(character, 300)
    assert character.level == 2


def test_campaign_round_trip(tmp_path: Path):
    db = Database(tmp_path / "campaign.db")
    character = starting_character("Asha", "Human", "Rogue", "Thief")
    campaign_id = db.create_campaign("Ashen Test", character, default_inventory("Rogue"),
                                     [NPC("Mira", "Innkeeper", "Careful", "Village")],
                                     [Quest("Test Quest", "Do the thing", "Active")])
    loaded = db.load(campaign_id)
    assert loaded is not None
    assert loaded["character"]["name"] == "Asha"
    assert loaded["quests"][0]["status"] == "Active"
