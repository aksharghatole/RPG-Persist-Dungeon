import os

import streamlit as st
from dotenv import load_dotenv

from ai_dm import narrate
from database import Database
from game_engine import award_xp, default_inventory, resolve_action, starting_character, xp_to_next_level
from models import Character, Item, NPC, Quest
from utils.helpers import hp_bar

load_dotenv()
st.set_page_config(page_title="AI Dungeon Master", page_icon="⚔", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Source+Sans+3:wght@400;600&display=swap');
:root { --ink:#e8e1d2; --muted:#a99f8c; --gold:#d2a85c; --panel:#171b20; --line:#343b43; }
.stApp { background: radial-gradient(circle at 80% 0%, #26323b 0, #0d1115 42%, #080a0c 100%); color:var(--ink); }
h1,h2,h3 { font-family:Cinzel, serif !important; letter-spacing:0 !important; }
[data-testid="stSidebar"] { background:#101419; border-right:1px solid var(--line); }
[data-testid="stChatMessage"] { border:1px solid #293139; background:rgba(23,27,32,.82); margin:.5rem 0; }
.eyebrow { color:var(--gold); font-size:.72rem; letter-spacing:.14em; font-weight:600; }
.hero { padding:3rem 1rem 2rem; border-bottom:1px solid var(--line); margin-bottom:2rem; }
.hero h1 { font-size:clamp(2.2rem, 6vw, 4.8rem); margin:.2rem 0; }
.hero p { color:var(--muted); font-size:1.15rem; }
.rule { border-top:1px solid var(--line); margin:1.4rem 0; }
.event { color:var(--gold); font-family:monospace; padding:.65rem .8rem; border-left:2px solid var(--gold); background:#1b1b18; }
</style>""", unsafe_allow_html=True)

db = Database()


def seed_npcs() -> list[NPC]:
    names = [("Mira", "Innkeeper", "Friendly but cautious"), ("Aldric", "Blacksmith", "Suspicious and terse"),
             ("Sister Elian", "Chapel keeper", "Patient and observant"), ("Tomas", "Ferryman", "Superstitious"),
             ("Veyra", "Traveling scholar", "Curious and secretive"), ("Orin", "Village elder", "Weary but proud"),
             ("The Ash Warden", "Unknown", "Implacable"), ("Nessa", "Hunter", "Direct and practical"),
             ("Corvin", "Merchant", "Charming and evasive"), ("Lio", "Stablehand", "Nervous and kind")]
    return [NPC(name, role, personality, "Blackthorn Village") for name, role, personality in names]


def seed_quests() -> list[Quest]:
    names = [("The Missing Children", "Find the children who vanished from Blackthorn Village.", "Active"),
             ("The Black Ring", "Learn what the strange ring is meant to unlock.", "Mystery"),
             ("Ashes on the Wind", "Trace the ash drifting down from the northern hills.", "Unknown"),
             ("A Debt of Iron", "Discover who has been stealing Aldric's ore.", "Unknown"),
             ("The Drowned Bell", "Find the source of a bell heard beneath the river.", "Unknown"),
             ("Letters Never Sent", "Deliver a packet of letters found in an abandoned cart.", "Unknown"),
             ("The Old Road", "Map a safe route beyond the village.", "Unknown"),
             ("A Quiet Chapel", "Investigate the chapel's sealed lower door.", "Unknown"),
             ("The Crow Market", "Find the next meeting place of a hidden faction.", "Unknown"),
             ("Stormwatch", "Learn why the storm refuses to move east.", "Unknown")]
    return [Quest(name, description, status) for name, description, status in names]


def opening(character: Character) -> str:
    return (f"Rain needles the road as {character.name} stands before Blackthorn Village. The wooden gate hangs open, "
            "its hinges groaning in the wind. No guards watch the muddy approach. Somewhere beyond the houses, a bell "
            "rings once, then falls silent. Strange black symbols have been carved into the gate, deep enough that rain "
            "has gathered in their grooves. The village beyond looks dark and still, though a faint amber light trembles "
            "behind one shutter. The road behind you is already dissolving into mist.\n\nWhat do you do?")


def set_campaign(campaign_id: int) -> None:
    loaded = db.load(campaign_id)
    if loaded:
        st.session_state.campaign_id = campaign_id
        st.session_state.state = loaded
        st.session_state.screen = "chat"


def show_sidebar() -> None:
    state = st.session_state.state
    character = Character.from_dict(state["character"])
    st.sidebar.markdown('<div class="eyebrow">CHARACTER</div>', unsafe_allow_html=True)
    st.sidebar.subheader(character.name)
    st.sidebar.caption(f"{character.race} {character.character_class} | Level {character.level}")
    st.sidebar.write(f"HP  {hp_bar(character.hp, character.max_hp)} {character.hp}/{character.max_hp}")
    st.sidebar.write(f"XP  {character.xp}/{xp_to_next_level(character.level)}")
    st.sidebar.write(f"Gold  {character.gold}")
    st.sidebar.markdown('<div class="eyebrow">STATS</div>', unsafe_allow_html=True)
    st.sidebar.write("  ".join(f"{key} {value}" for key, value in character.stats().items()))
    st.sidebar.markdown('<div class="eyebrow">INVENTORY</div>', unsafe_allow_html=True)
    for item in state["inventory"]:
        if item["quantity"] > 0:
            st.sidebar.write(f"{item['name']} x{item['quantity']}")
    st.sidebar.markdown('<div class="eyebrow">QUESTS</div>', unsafe_allow_html=True)
    for quest in state["quests"]:
        if quest["status"] in ("Active", "Mystery"):
            st.sidebar.write(f"**{quest['name']}**\n\n{quest['status']}")
    if st.sidebar.button("Save campaign", use_container_width=True):
        persist()
        st.sidebar.success("Saved")


def persist(event: str | None = None) -> None:
    state = st.session_state.state
    db.save(st.session_state.campaign_id, Character.from_dict(state["character"]),
            [Item(**item) for item in state["inventory"]], [NPC(**npc) for npc in state["npcs"]],
            [Quest(**quest) for quest in state["quests"]], state["campaign"]["location"], event)


def add_message(role: str, content: str) -> None:
    st.session_state.state["messages"].append({"role": role, "content": content})
    db.add_message(st.session_state.campaign_id, role, content)


def command(action: str) -> bool:
    if action == "/inventory":
        add_message("system", "Inventory: " + ", ".join(f"{item['name']} x{item['quantity']}" for item in st.session_state.state["inventory"] if item["quantity"] > 0))
    elif action == "/stats":
        character = Character.from_dict(st.session_state.state["character"])
        add_message("system", "Stats: " + ", ".join(f"{key} {value}" for key, value in character.stats().items()))
    elif action == "/quests":
        add_message("system", "Quests: " + "; ".join(f"{quest['name']} ({quest['status']})" for quest in st.session_state.state["quests"]))
    elif action == "/location":
        add_message("system", "Current location: " + st.session_state.state["campaign"]["location"])
    elif action == "/help":
        add_message("system", "Commands: /inventory, /stats, /quests, /location, /save, /help")
    elif action == "/save":
        persist()
        add_message("system", "Campaign saved.")
    else:
        return False
    return True


def create_screen() -> None:
    st.markdown('<div class="eyebrow">CHARACTER CREATION</div><h1>Who enters the storm?</h1>', unsafe_allow_html=True)
    with st.form("character_form"):
        name = st.text_input("Character name", placeholder="Kael")
        race = st.selectbox("Race", ["Human", "Elf", "Dwarf", "Orc", "Halfling", "Dragonborn", "Tiefling", "Custom"])
        character_class = st.selectbox("Class", ["Warrior", "Mage", "Rogue", "Ranger", "Paladin", "Cleric", "Warlock", "Custom"])
        background = st.selectbox("Background", ["Noble", "Mercenary", "Thief", "Scholar", "Outcast", "Merchant", "Royal Guard", "Adventurer", "Custom"])
        custom = st.text_area("Describe your character", placeholder="A disgraced prince who secretly practices forbidden magic.")
        submitted = st.form_submit_button("Enter the Ashen Kingdom", type="primary", use_container_width=True)
    if submitted:
        character = starting_character(name, race, character_class, background, custom)
        campaign_name = f"The Ashen Kingdom - {character.name}"
        campaign_id = db.create_campaign(campaign_name, character, default_inventory(character.character_class), seed_npcs(), seed_quests())
        st.session_state.campaign_id = campaign_id
        st.session_state.state = db.load(campaign_id)
        opening_text = opening(character)
        add_message("assistant", opening_text)
        st.session_state.screen = "chat"
        st.rerun()


def landing_screen() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">THE ASHEN KINGDOM</div><h1>AI DUNGEON MASTER</h1><p>Your story. Your choices. Your world.</p></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        if st.button("Create new campaign", type="primary", use_container_width=True):
            st.session_state.screen = "create"
            st.rerun()
    with right:
        st.subheader("Load campaign")
        campaigns = db.list_campaigns()
        if not campaigns:
            st.caption("No campaigns yet. Your first legend starts here.")
        for campaign in campaigns:
            loaded = db.load(campaign["id"])
            character = loaded["character"] if loaded else {"name": "Unknown", "level": 1}
            a, b = st.columns([4, 1])
            with a:
                if st.button(f"{campaign['name']} | {character['name']} | Level {character['level']}", key=f"load-{campaign['id']}", use_container_width=True):
                    set_campaign(campaign["id"])
                    st.rerun()
            with b:
                if st.button("Delete", key=f"delete-{campaign['id']}"):
                    db.delete(campaign["id"])
                    st.rerun()


def chat_screen() -> None:
    show_sidebar()
    state = st.session_state.state
    st.markdown('<div class="eyebrow">BLACKTHORN VILLAGE</div>', unsafe_allow_html=True)
    st.title("The road into darkness")
    for message in state["messages"]:
        role = "assistant" if message["role"] == "assistant" else "user"
        if message["role"] == "system":
            st.markdown(f'<div class="event">GAME EVENT<br>{message["content"]}</div>', unsafe_allow_html=True)
        else:
            with st.chat_message(role):
                st.markdown(message["content"])
    action = st.chat_input("What do you do?")
    if action and action.strip():
        action = action.strip()
        add_message("user", action)
        if not command(action.lower()):
            character = Character.from_dict(state["character"])
            result = resolve_action(action, character, [Item(**item) for item in state["inventory"]])
            state["character"] = character.to_dict()
            state["inventory"] = [item.__dict__ for item in result["inventory"]]
            for event in result["events"]:
                add_message("system", event)
            if result.get("xp_awarded"):
                for level_event in award_xp(character, result["xp_awarded"]):
                    add_message("system", level_event)
                state["character"] = character.to_dict()
            response = narrate(state, action, result["events"])
            add_message("assistant", response)
            persist("Player action: " + action)
        st.rerun()


if "screen" not in st.session_state:
    st.session_state.screen = "landing"
if st.session_state.screen == "landing":
    landing_screen()
elif st.session_state.screen == "create":
    create_screen()
else:
    chat_screen()
