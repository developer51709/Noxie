"""
face_manager.py — Manages Noxie's face assets and banner selection.

Maps events to the correct face image (mood banner) file path.
"""

from pathlib import Path
from modules.utils import ROOT, mood_banner_path

# ── Event → mood key mapping ────────────────────────────────────────────────

EVENT_MOOD: dict[str, str] = {
    # Hunt events
    "hunt_common":    "neutral",
    "hunt_uncommon":  "cozy",
    "hunt_rare":      "rare",
    "hunt_epic":      "excited",
    "hunt_legendary": "love",
    "hunt_mythic":    "evil",
    "hunt_fail":      "melancholy",

    # Pull events
    "pull_success":   "happy",
    "pull_fail":      "deadpan",

    # Errors and cooldowns
    "error":          "dizzy",
    "cooldown":       "sleepy",

    # Server events
    "guild_join":     "love",
    "guild_leave":    "melancholy",

    # Creature moods
    "mood_cozy":      "cozy",
    "mood_chaotic":   "chaotic",
    "mood_melancholy":"melancholy",
    "mood_sarcastic": "sarcastic",
    "mood_neutral":   "neutral",

    # Economy / donation
    "donate_start":   "excited",
    "donate_done":    "love",
    "donate_fail":    "dizzy",

    # Reactions
    "reaction_uwu":   "love",
    "reaction_evil":  "evil",
    "reaction_cozy":  "cozy",
}


def get_face_for_event(event: str) -> str | None:
    """
    Return the absolute file path for the mood banner matching the event.
    Falls back to 'neutral' if the event key is unknown.
    """
    mood = EVENT_MOOD.get(event, "neutral")
    return mood_banner_path(mood)


def get_face_for_rarity(rarity: str) -> str | None:
    """Return the banner path for a hunt result based on rarity."""
    rarity_event = f"hunt_{rarity.lower()}"
    return get_face_for_event(rarity_event)


def get_face_for_creature_mood(creature_mood: str) -> str | None:
    """Return banner for a creature's native mood."""
    event = f"mood_{creature_mood.lower()}"
    return get_face_for_event(event)


def all_faces() -> dict[str, str | None]:
    """Return all event → file-path mappings (for debug/listing)."""
    return {event: get_face_for_event(event) for event in EVENT_MOOD}
