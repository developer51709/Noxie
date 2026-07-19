"""
prefixes.py — Multi-prefix system for Noxie.

Rules:
  - Global prefix "noxie " is ALWAYS active in every guild. It cannot be removed.
  - Guilds may register additional custom prefixes in SQLite.
  - Prefix lookup is used as discord.py's command_prefix callable.
"""

import sqlite3
from typing import TYPE_CHECKING
import discord
from discord.ext import commands

from modules.utils import load_config
from modules import logger

if TYPE_CHECKING:
    from main import NoxieBot

CONFIG = load_config()
GLOBAL_PREFIX = CONFIG.get("global_prefix", "noxie ")


# ── Schema ──────────────────────────────────────────────────────────────────

def init_prefix_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_prefixes (
            guild_id  TEXT NOT NULL,
            prefix    TEXT NOT NULL,
            PRIMARY KEY (guild_id, prefix)
        )
    """)
    conn.commit()


# ── Helpers ─────────────────────────────────────────────────────────────────

def get_guild_prefixes(conn: sqlite3.Connection, guild_id: str) -> list[str]:
    """Return all stored custom prefixes for a guild (global prefix NOT included here)."""
    rows = conn.execute(
        "SELECT prefix FROM guild_prefixes WHERE guild_id=?",
        (guild_id,)
    ).fetchall()
    return [r["prefix"] for r in rows]


def add_prefix(conn: sqlite3.Connection, guild_id: str, prefix: str) -> bool:
    """Add a custom prefix. Returns False if it already exists or is the global prefix."""
    if prefix.lower() == GLOBAL_PREFIX.lower():
        return False
    try:
        conn.execute(
            "INSERT INTO guild_prefixes (guild_id, prefix) VALUES (?,?)",
            (guild_id, prefix)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def remove_prefix(conn: sqlite3.Connection, guild_id: str, prefix: str) -> bool:
    """
    Remove a custom prefix.
    Returns False if the prefix is the global prefix (blocked) or doesn't exist.
    """
    if prefix.lower() == GLOBAL_PREFIX.lower():
        return False
    cur = conn.execute(
        "DELETE FROM guild_prefixes WHERE guild_id=? AND prefix=?",
        (guild_id, prefix)
    )
    conn.commit()
    return cur.rowcount > 0


def all_prefixes_for_guild(conn: sqlite3.Connection, guild_id: str) -> list[str]:
    """Return ALL effective prefixes: global + guild custom."""
    custom = get_guild_prefixes(conn, guild_id)
    seen = {GLOBAL_PREFIX.lower()}
    result = [GLOBAL_PREFIX]
    for p in custom:
        if p.lower() not in seen:
            seen.add(p.lower())
            result.append(p)
    return result


# ── discord.py prefix callable ───────────────────────────────────────────────

def prefix_callable(bot: "NoxieBot", message: discord.Message) -> list[str]:
    """
    Called by discord.py for every incoming message.
    Always returns at least the global prefix.

    Uses the bot's shared DB connection to avoid opening a new connection per
    message (which was the previous source of silent failures when the table
    didn't yet exist on a fresh connection object).
    """
    if message.guild is None:
        # DMs: only the global prefix
        return [GLOBAL_PREFIX]

    try:
        # Use the bot's existing connection — tables are guaranteed to exist.
        conn: sqlite3.Connection = bot.db  # type: ignore[attr-defined]
        return all_prefixes_for_guild(conn, str(message.guild.id))
    except Exception as exc:
        # Never raise from the prefix callable — discord.py drops commands
        # silently if this function throws.
        logger.error(f"prefix_callable error for guild={message.guild.id}", exc=exc)
        return [GLOBAL_PREFIX]


# ── Cog ─────────────────────────────────────────────────────────────────────

class PrefixCog(commands.Cog, name="Prefixes"):
    """Manage per-guild command prefixes."""

    def __init__(self, bot: "NoxieBot") -> None:
        self.bot = bot
        init_prefix_table(self.bot.db)

    @commands.hybrid_group(name="prefix", invoke_without_command=True)
    @commands.guild_only()
    async def prefix_group(self, ctx: commands.Context) -> None:
        """List all active prefixes for this server."""
        try:
            prefixes = all_prefixes_for_guild(self.bot.db, str(ctx.guild.id))
            listed = "\n".join(f"• `{p}`" for p in prefixes)
            await ctx.send(
                f"**Active prefixes for this server:**\n{listed}\n\n"
                f"The prefix `{GLOBAL_PREFIX}` is always available and cannot be removed.",
                ephemeral=True,
            )
        except Exception as exc:
            logger.error("prefix list error", exc=exc)
            await ctx.send("⚠️ couldn't fetch prefixes. try again.", ephemeral=True)

    @prefix_group.command(name="add")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_add(self, ctx: commands.Context, *, new_prefix: str) -> None:
        """Add a custom prefix for this server."""
        try:
            added = add_prefix(self.bot.db, str(ctx.guild.id), new_prefix)
            if added:
                await ctx.send(f"✅ Prefix `{new_prefix}` added.", ephemeral=True)
            else:
                await ctx.send(
                    f"❌ `{new_prefix}` is already registered or cannot be added.",
                    ephemeral=True,
                )
        except Exception as exc:
            logger.error("prefix add error", exc=exc)
            await ctx.send("⚠️ couldn't add prefix. try again.", ephemeral=True)

    @prefix_group.command(name="remove")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def prefix_remove(self, ctx: commands.Context, *, prefix: str) -> None:
        """Remove a custom prefix from this server."""
        try:
            if prefix.lower() == GLOBAL_PREFIX.lower():
                await ctx.send(
                    f"❌ The global prefix `{GLOBAL_PREFIX}` is permanent and cannot be removed.",
                    ephemeral=True,
                )
                return
            removed = remove_prefix(self.bot.db, str(ctx.guild.id), prefix)
            if removed:
                await ctx.send(f"✅ Prefix `{prefix}` removed.", ephemeral=True)
            else:
                await ctx.send(f"❌ Prefix `{prefix}` was not found.", ephemeral=True)
        except Exception as exc:
            logger.error("prefix remove error", exc=exc)
            await ctx.send("⚠️ couldn't remove prefix. try again.", ephemeral=True)


async def setup(bot: "NoxieBot") -> None:
    await bot.add_cog(PrefixCog(bot))
    logger.success("PrefixCog loaded")
