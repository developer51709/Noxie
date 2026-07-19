"""
utils.py — Shared helpers for Noxie bot.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    """Load config.json from the project root."""
    config_path = ROOT / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_db_conn(config: dict) -> sqlite3.Connection:
    """Return a SQLite connection (creates file if missing)."""
    db_path = ROOT / config["db_path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def load_creatures() -> dict:
    """Load vibe_creatures/data.json."""
    data_path = ROOT / "vibe_creatures" / "data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def mood_banner_path(mood: str) -> str | None:
    """
    Return the file path of a mood banner image for a given mood key.
    Mood keys map to filenames in mood_banners/.
    """
    banner_dir = ROOT / "mood_banners"
    mapping = {
        "neutral":    "neutral.jpeg",
        "happy":      "happy.jpeg",
        "evil":       "evil.jpeg",
        "dizzy":      "dizzy.jpeg",
        "deadpan":    "deadpan.jpeg",
        "cozy":       "cozy.jpeg",
        "chaotic":    "chaotic.jpeg",
        "sarcastic":  "sarcastic.jpeg",
        "carinha":    "carinha.jpeg",
        "melancholy": "melancholy.jpeg",
        "sleepy":     "sleepy.jpeg",
        "excited":    "excited.jpeg",
        "love":       "love.jpeg",
        "rare":       "rare.jpeg",
    }
    filename = mapping.get(mood)
    if filename:
        full = banner_dir / filename
        if full.exists():
            return str(full)
    return None


# Rarity -> mood mapping for hunt banners
RARITY_MOOD = {
    "common":    "neutral",
    "uncommon":  "cozy",
    "rare":      "rare",
    "epic":      "excited",
    "legendary": "love",
    "mythic":    "evil",
}

CREATURE_MOOD_BANNER = {
    "melancholy": "melancholy",
    "chaotic":    "chaotic",
    "cozy":       "cozy",
    "neutral":    "neutral",
    "sarcastic":  "sarcastic",
}
