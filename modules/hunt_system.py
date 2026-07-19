"""
hunt_system.py — Vibe creature hunt system.

Commands:
  /hunt          (slash)
  noxie hunt     (prefix)
  /inventory     (slash)
  noxie inventory (prefix)
  /vibe          (slash)
  noxie vibe     (prefix)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from discord import app_commands

from modules import economy, cv2_engine, face_manager, personality, logger
from modules.utils import load_creatures, load_config, RARITY_MOOD, CREATURE_MOOD_BANNER, ROOT

if TYPE_CHECKING:
    from main import NoxieBot

CONFIG = load_config()
_creatures_data = load_creatures()
CREATURES: list[dict] = _creatures_data["creatures"]
RARITY_WEIGHTS: dict[str, int] = _creatures_data["rarity_weights"]
CREATURE_MAP: dict[str, dict] = {c["id"]: c for c in CREATURES}


# ── Rarity roll ──────────────────────────────────────────────────────────────

def roll_rarity() -> str:
    rarities = list(RARITY_WEIGHTS.keys())
    weights  = list(RARITY_WEIGHTS.values())
    return random.choices(rarities, weights=weights, k=1)[0]


def roll_creature(rarity: str) -> dict:
    pool = [c for c in CREATURES if c["rarity"] == rarity]
    return random.choice(pool) if pool else random.choice(CREATURES)


def roll_rewards(rarity: str) -> tuple[int, int]:
    """Return (glow_shards, vibe_coins) based on rarity."""
    multipliers = {
        "common":    (1.0, 1.0),
        "uncommon":  (2.0, 1.5),
        "rare":      (4.0, 3.0),
        "epic":      (8.0, 6.0),
        "legendary": (20.0, 15.0),
        "mythic":    (50.0, 40.0),
    }
    gs_range = CONFIG["economy"]["glow_shards_per_hunt"]
    vc_range = CONFIG["economy"]["vibe_coins_per_hunt"]
    mult = multipliers.get(rarity, (1.0, 1.0))
    glow  = int(random.randint(*gs_range) * mult[0])
    coins = int(random.randint(*vc_range) * mult[1])
    return glow, coins


# ── Luck value (0.0–1.0) from rarity ────────────────────────────────────────

RARITY_LUCK = {
    "common": 0.3, "uncommon": 0.5, "rare": 0.65,
    "epic": 0.8, "legendary": 0.93, "mythic": 1.0,
}


# ── Core hunt logic ──────────────────────────────────────────────────────────

async def do_hunt(
    bot: "NoxieBot",
    user_id: str,
    guild_id: str,
    target,  # ctx or interaction — passed to send_cv2
) -> None:
    """
    Run a full hunt flow: cooldown check → roll → record → build CV2 → send.
    """
    # Cooldown check
    remaining = economy.check_hunt_cooldown(bot.db, user_id, guild_id)
    if remaining > 0:
        line = personality.get_line("cooldown")
        banner_path = face_manager.get_face_for_event("cooldown")
        comps, files = cv2_engine.build_face_reaction_container(
            message=f"⏳ **cooldown:** {remaining:.1f}s remaining\n*{line}*",
            banner_path=banner_path,
            color=0x4A4A4A,
        )
        await cv2_engine.send_cv2(target, comps, files)
        return

    # Roll rarity + creature
    rarity   = roll_rarity()
    creature = roll_creature(rarity)
    glow, coins = roll_rewards(rarity)
    luck = RARITY_LUCK.get(rarity, 0.3)

    # Record to DB
    bal = economy.record_hunt(bot.db, user_id, guild_id, glow, coins)
    economy.add_to_inventory(bot.db, user_id, guild_id, creature["id"])

    # Award milestone badges
    total = bal["total_hunts"]
    if total >= 100:
        economy.award_badge(bot.db, user_id, "hunter_100")
    elif total >= 50:
        economy.award_badge(bot.db, user_id, "hunter_50")
    elif total >= 10:
        economy.award_badge(bot.db, user_id, "hunter_10")
    if rarity == "legendary":
        economy.award_badge(bot.db, user_id, "legendary")
    if rarity == "mythic":
        economy.award_badge(bot.db, user_id, "mythic")

    logger.debug(
        f"hunt: user={user_id} guild={guild_id} rarity={rarity} "
        f"creature={creature['name']} glow={glow} coins={coins}"
    )

    # Personality line
    event = "hunt_rare" if rarity in ("legendary", "mythic", "epic") else "hunt_success"
    line = personality.get_line(event, streak=bal["hunt_streak"], luck=luck)

    # Face/banner selection
    banner_path = face_manager.get_face_for_rarity(rarity)
    creature_mood_banner = face_manager.get_face_for_creature_mood(creature.get("mood", "neutral"))
    final_banner = creature_mood_banner or banner_path

    # Creature artwork path
    art_file = creature.get("art_file", "")
    art_path = str(ROOT / "vibe_creatures" / art_file) if art_file else None
    if art_path and not __import__("os").path.exists(art_path):
        art_path = None

    # Build and send CV2
    comps, files = cv2_engine.build_hunt_container(
        creature=creature,
        glow_earned=glow,
        coins_earned=coins,
        total_hunts=total,
        personality_line=line,
        art_path=art_path,
        banner_path=final_banner,
    )
    await cv2_engine.send_cv2(target, comps, files)


# ── Cog ──────────────────────────────────────────────────────────────────────

class HuntCog(commands.Cog, name="Hunt"):
    """Vibe creature hunting system."""

    def __init__(self, bot: "NoxieBot") -> None:
        self.bot = bot

    # ── /hunt slash ──────────────────────────────────────────────────────────

    @app_commands.command(name="hunt", description="Hunt for a vibe creature!")
    @app_commands.guild_only()
    async def hunt_slash(self, interaction: discord.Interaction) -> None:
        # Do NOT defer — send_cv2 uses response.send_message() directly,
        # which is the reliable path for CV2 flags.
        try:
            await do_hunt(
                self.bot,
                str(interaction.user.id),
                str(interaction.guild_id),
                interaction,
            )
        except Exception as exc:
            logger.error(f"hunt slash error for user={interaction.user.id}", exc=exc)
            await _slash_error_response(interaction)

    # ── prefix hunt ──────────────────────────────────────────────────────────

    @commands.command(name="hunt", aliases=["h"])
    @commands.guild_only()
    async def hunt_prefix(self, ctx: commands.Context) -> None:
        """Hunt for a vibe creature."""
        try:
            await do_hunt(
                self.bot,
                str(ctx.author.id),
                str(ctx.guild.id),
                ctx,
            )
        except Exception as exc:
            logger.error(f"hunt prefix error for user={ctx.author.id}", exc=exc)
            await ctx.send("⚠️ something went sideways with that hunt. try again.")

    # ── /inventory slash ──────────────────────────────────────────────────────

    @app_commands.command(name="inventory", description="View your vibe creature collection.")
    @app_commands.guild_only()
    @app_commands.describe(page="Page number")
    async def inventory_slash(
        self, interaction: discord.Interaction, page: int = 1
    ) -> None:
        try:
            inv = economy.get_inventory(
                self.bot.db, str(interaction.user.id), str(interaction.guild_id)
            )
            if not inv:
                line = personality.get_line("inventory_empty")
                banner_path = face_manager.get_face_for_event("hunt_fail")
                comps, files = cv2_engine.build_face_reaction_container(
                    message=f"*{line}*", banner_path=banner_path, color=0x4A4A4A
                )
                await cv2_engine.send_cv2(interaction, comps, files)
                return

            counts: dict[str, int] = {}
            for row in inv:
                cid = row["creature_id"]
                counts[cid] = counts.get(cid, 0) + 1

            comps, files = cv2_engine.build_inventory_container(
                user_name=interaction.user.display_name,
                creature_counts=counts,
                all_creatures=CREATURE_MAP,
                page=page,
            )
            await cv2_engine.send_cv2(interaction, comps, files)
        except Exception as exc:
            logger.error(f"inventory slash error for user={interaction.user.id}", exc=exc)
            await _slash_error_response(interaction)

    # ── prefix inventory ──────────────────────────────────────────────────────

    @commands.command(name="inventory", aliases=["inv", "bag"])
    @commands.guild_only()
    async def inventory_prefix(self, ctx: commands.Context, page: int = 1) -> None:
        """View your vibe creature collection."""
        try:
            inv = economy.get_inventory(self.bot.db, str(ctx.author.id), str(ctx.guild.id))
            if not inv:
                line = personality.get_line("inventory_empty")
                banner_path = face_manager.get_face_for_event("hunt_fail")
                comps, files = cv2_engine.build_face_reaction_container(
                    message=f"*{line}*", banner_path=banner_path, color=0x4A4A4A
                )
                await cv2_engine.send_cv2(ctx, comps, files)
                return

            counts: dict[str, int] = {}
            for row in inv:
                cid = row["creature_id"]
                counts[cid] = counts.get(cid, 0) + 1

            comps, files = cv2_engine.build_inventory_container(
                user_name=ctx.author.display_name,
                creature_counts=counts,
                all_creatures=CREATURE_MAP,
                page=page,
            )
            await cv2_engine.send_cv2(ctx, comps, files)
        except Exception as exc:
            logger.error(f"inventory prefix error for user={ctx.author.id}", exc=exc)
            await ctx.send("⚠️ couldn't fetch your inventory. try again.")

    # ── /vibe slash ───────────────────────────────────────────────────────────

    @app_commands.command(name="vibe", description="Check your current vibe energy.")
    @app_commands.guild_only()
    async def vibe_slash(self, interaction: discord.Interaction) -> None:
        try:
            bal = economy.get_balance(
                self.bot.db, str(interaction.user.id), str(interaction.guild_id)
            )
            streak = bal["hunt_streak"]
            luck   = min(1.0, streak / 20.0)
            vibe   = personality.vibe_status(streak, luck)
            line   = personality.get_line("hunt_success", streak=streak, luck=luck)
            banner_path = face_manager.get_face_for_event(
                "reaction_uwu" if luck > 0.7 else "mood_neutral"
            )
            comps, files = cv2_engine.build_face_reaction_container(
                message=(
                    f"## ✨ Vibe Check — {interaction.user.display_name}\n"
                    f"**Status:** {vibe}\n"
                    f"**Streak:** 🔥 {streak}\n\n"
                    f"*{line}*"
                ),
                banner_path=banner_path,
                color=0x9B59B6,
            )
            await cv2_engine.send_cv2(interaction, comps, files)
        except Exception as exc:
            logger.error(f"vibe slash error for user={interaction.user.id}", exc=exc)
            await _slash_error_response(interaction)

    # ── prefix vibe ───────────────────────────────────────────────────────────

    @commands.command(name="vibe")
    @commands.guild_only()
    async def vibe_prefix(self, ctx: commands.Context) -> None:
        """Check your current vibe energy."""
        try:
            bal = economy.get_balance(self.bot.db, str(ctx.author.id), str(ctx.guild.id))
            streak = bal["hunt_streak"]
            luck   = min(1.0, streak / 20.0)
            vibe   = personality.vibe_status(streak, luck)
            line   = personality.get_line("hunt_success", streak=streak, luck=luck)
            banner_path = face_manager.get_face_for_event(
                "reaction_uwu" if luck > 0.7 else "mood_neutral"
            )
            comps, files = cv2_engine.build_face_reaction_container(
                message=(
                    f"## ✨ Vibe Check — {ctx.author.display_name}\n"
                    f"**Status:** {vibe}\n"
                    f"**Streak:** 🔥 {streak}\n\n"
                    f"*{line}*"
                ),
                banner_path=banner_path,
                color=0x9B59B6,
            )
            await cv2_engine.send_cv2(ctx, comps, files)
        except Exception as exc:
            logger.error(f"vibe prefix error for user={ctx.author.id}", exc=exc)
            await ctx.send("⚠️ vibe check failed. the vibe itself is broken.")


# ── Slash error fallback ──────────────────────────────────────────────────────

async def _slash_error_response(interaction: discord.Interaction) -> None:
    """Send a plain-text error ack when CV2 building itself fails."""
    try:
        msg = "⚠️ something went sideways. try again."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass  # nothing left to do


async def setup(bot: "NoxieBot") -> None:
    await bot.add_cog(HuntCog(bot))
    logger.success("HuntCog loaded")
