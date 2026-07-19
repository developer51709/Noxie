"""
utils/economy.py — Noxie economy system.

Currencies:
  - Glow Shards  (primary, earned from hunts and donations)
  - Vibe Coins   (premium-ish, earned less frequently)

Tables:
  - economy(user_id, guild_id, glow_shards, vibe_coins, total_hunts, hunt_streak)
  - badges(user_id, badge_name, awarded_at)
  - donations(user_id, amount_usd, currency, tx_id, awarded_at)
"""

import sqlite3
import time

from utils.helpers import get_db_conn, load_config

CONFIG = load_config()


# ── Schema ──────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS economy (
            user_id     TEXT NOT NULL,
            guild_id    TEXT NOT NULL,
            glow_shards INTEGER NOT NULL DEFAULT 0,
            vibe_coins  INTEGER NOT NULL DEFAULT 0,
            total_hunts INTEGER NOT NULL DEFAULT 0,
            hunt_streak INTEGER NOT NULL DEFAULT 0,
            last_hunt   REAL    NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        );

        CREATE TABLE IF NOT EXISTS badges (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT    NOT NULL,
            badge_name  TEXT    NOT NULL,
            awarded_at  REAL    NOT NULL DEFAULT 0,
            UNIQUE(user_id, badge_name)
        );

        CREATE TABLE IF NOT EXISTS donations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT    NOT NULL,
            amount_usd  REAL    NOT NULL,
            currency    TEXT    NOT NULL DEFAULT 'USDT',
            tx_id       TEXT    NOT NULL,
            awarded_at  REAL    NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT    NOT NULL,
            guild_id    TEXT    NOT NULL,
            creature_id TEXT    NOT NULL,
            caught_at   REAL    NOT NULL DEFAULT 0,
            fused       INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()


# ── Economy helpers ──────────────────────────────────────────────────────────

def _ensure_row(conn: sqlite3.Connection, user_id: str, guild_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO economy (user_id, guild_id) VALUES (?, ?)",
        (user_id, guild_id)
    )
    conn.commit()


def get_balance(conn: sqlite3.Connection, user_id: str, guild_id: str) -> dict:
    _ensure_row(conn, user_id, guild_id)
    row = conn.execute(
        "SELECT glow_shards, vibe_coins, total_hunts, hunt_streak, last_hunt "
        "FROM economy WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    return dict(row)


def add_currency(
    conn: sqlite3.Connection,
    user_id: str,
    guild_id: str,
    glow_shards: int = 0,
    vibe_coins: int = 0,
) -> None:
    _ensure_row(conn, user_id, guild_id)
    conn.execute(
        """UPDATE economy
           SET glow_shards = glow_shards + ?,
               vibe_coins  = vibe_coins  + ?
           WHERE user_id=? AND guild_id=?""",
        (glow_shards, vibe_coins, user_id, guild_id)
    )
    conn.commit()


def spend_currency(
    conn: sqlite3.Connection,
    user_id: str,
    guild_id: str,
    glow_shards: int = 0,
    vibe_coins: int = 0,
) -> bool:
    """Returns False if the user can't afford it."""
    bal = get_balance(conn, user_id, guild_id)
    if bal["glow_shards"] < glow_shards or bal["vibe_coins"] < vibe_coins:
        return False
    conn.execute(
        """UPDATE economy
           SET glow_shards = glow_shards - ?,
               vibe_coins  = vibe_coins  - ?
           WHERE user_id=? AND guild_id=?""",
        (glow_shards, vibe_coins, user_id, guild_id)
    )
    conn.commit()
    return True


def record_hunt(
    conn: sqlite3.Connection,
    user_id: str,
    guild_id: str,
    glow_earned: int,
    coins_earned: int,
) -> dict:
    """Increment hunt count, update streak, credit earnings. Returns new balance."""
    _ensure_row(conn, user_id, guild_id)
    now = time.time()
    conn.execute(
        """UPDATE economy
           SET glow_shards = glow_shards + ?,
               vibe_coins  = vibe_coins  + ?,
               total_hunts = total_hunts + 1,
               hunt_streak = hunt_streak + 1,
               last_hunt   = ?
           WHERE user_id=? AND guild_id=?""",
        (glow_earned, coins_earned, now, user_id, guild_id)
    )
    conn.commit()
    return get_balance(conn, user_id, guild_id)


def check_hunt_cooldown(
    conn: sqlite3.Connection,
    user_id: str,
    guild_id: str,
) -> float:
    """Returns seconds remaining on cooldown (0 if ready)."""
    _ensure_row(conn, user_id, guild_id)
    row = conn.execute(
        "SELECT last_hunt FROM economy WHERE user_id=? AND guild_id=?",
        (user_id, guild_id)
    ).fetchone()
    cooldown = CONFIG.get("hunt_cooldown", 30)
    elapsed = time.time() - (row["last_hunt"] or 0)
    remaining = cooldown - elapsed
    return max(0.0, remaining)


# ── Inventory helpers ────────────────────────────────────────────────────────

def add_to_inventory(
    conn: sqlite3.Connection,
    user_id: str,
    guild_id: str,
    creature_id: str,
) -> None:
    conn.execute(
        "INSERT INTO inventory (user_id, guild_id, creature_id, caught_at) VALUES (?,?,?,?)",
        (user_id, guild_id, creature_id, time.time())
    )
    conn.commit()


def get_inventory(
    conn: sqlite3.Connection,
    user_id: str,
    guild_id: str,
) -> list[dict]:
    rows = conn.execute(
        "SELECT creature_id, caught_at, fused FROM inventory "
        "WHERE user_id=? AND guild_id=? ORDER BY caught_at DESC",
        (user_id, guild_id)
    ).fetchall()
    return [dict(r) for r in rows]


def count_creature(
    conn: sqlite3.Connection,
    user_id: str,
    guild_id: str,
    creature_id: str,
) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM inventory "
        "WHERE user_id=? AND guild_id=? AND creature_id=? AND fused=0",
        (user_id, guild_id, creature_id)
    ).fetchone()
    return row["cnt"]


# ── Badge helpers ────────────────────────────────────────────────────────────

def award_badge(conn: sqlite3.Connection, user_id: str, badge_name: str) -> bool:
    """Awards a badge. Returns True if it's new."""
    try:
        conn.execute(
            "INSERT INTO badges (user_id, badge_name, awarded_at) VALUES (?,?,?)",
            (user_id, badge_name, time.time())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_badges(conn: sqlite3.Connection, user_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT badge_name FROM badges WHERE user_id=? ORDER BY awarded_at ASC",
        (user_id,)
    ).fetchall()
    return [r["badge_name"] for r in rows]


# ── Donation log ─────────────────────────────────────────────────────────────

def log_donation(
    conn: sqlite3.Connection,
    user_id: str,
    amount_usd: float,
    currency: str,
    tx_id: str,
) -> None:
    conn.execute(
        "INSERT INTO donations (user_id, amount_usd, currency, tx_id, awarded_at) "
        "VALUES (?,?,?,?,?)",
        (user_id, amount_usd, currency, tx_id, time.time())
    )
    conn.commit()


def get_donation_total(conn: sqlite3.Connection, user_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_usd), 0) AS total FROM donations WHERE user_id=?",
        (user_id,)
    ).fetchone()
    return row["total"]


# ── Badge display map ────────────────────────────────────────────────────────

BADGE_DISPLAY: dict[str, str] = {
    "donor":       "💎 Donor",
    "hunter_10":   "🏹 Hunter I",
    "hunter_50":   "🏹 Hunter II",
    "hunter_100":  "🏹 Hunter III",
    "legendary":   "🌟 Legendary Finder",
    "mythic":      "🌌 Mythic Witness",
    "streak_25":   "🔥 Hot Streak",
}
