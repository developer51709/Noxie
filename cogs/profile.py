"""
cogs/profile.py — /profile command for Noxie.

Shows a user's mood pulse container with stats, badges, and mood banner.

CV2 containers defined here:
  build_mood_pulse_container — profile card (only used by this cog)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import economy, face_manager, personality
from utils.economy import BADGE_DISPLAY
from utils.logger import log
from utils.cv2_helpers import _make_file, _media, _sep, send_cv2

if TYPE_CHECKING:
    from main import NoxieBot


# ── CV2 container ─────────────────────────────────────────────────────────────

def build_mood_pulse_container(
    user_name: str,
    vibe_status: str,
    streak: int,
    glow_shards: int,
    vibe_coins: int,
    total_hunts: int,
    badges: list[str],
    banner_path: Optional[str] = None,
    badge_display: Optional[dict] = None,
) -> tuple[list, list[discord.File]]:
    """Profile / mood pulse container. Mood banner at bottom."""
    badge_display = badge_display or {}
    badge_str = "  ".join(
        badge_display.get(b, f"[{b}]") for b in badges
    ) if badges else "*no badges yet*"

    container = discord.ui.Container(
        discord.ui.TextDisplay(content=f"## 👁️  {user_name}'s Vibe Profile"),
        _sep(visible=True),
        discord.ui.TextDisplay(
            content=(
                f"**Current Vibe** — {vibe_status}\n"
                f"**Hunt Streak**  — 🔥 {streak}\n"
                f"**Total Hunts**  — {total_hunts:,}"
            )
        ),
        _sep(visible=False),
        discord.ui.TextDisplay(
            content=(
                f"**Glow Shards** — `{glow_shards:,}` ✨\n"
                f"**Vibe Coins**  — `{vibe_coins:,}` 🪙"
            )
        ),
        _sep(visible=True),
        discord.ui.TextDisplay(content=f"**Badges**\n{badge_str}"),
        accent_color=discord.Color(0x7930A7),
    )

    files: list[discord.File] = []

    if banner_path:
        container.add_item(_sep(visible=False))
        container.add_item(_media("mood_pulse.jpeg"))
        files.append(_make_file(banner_path, "mood_pulse.jpeg"))

    return [container], files


# ── Cog ───────────────────────────────────────────────────────────────────────

class ProfileCog(commands.Cog, name="Profile"):
    """User profile and mood pulse."""

    def __init__(self, bot: "NoxieBot") -> None:
        self.bot = bot

    # ── /profile ─────────────────────────────────────────────────────────────

    @app_commands.command(name="profile", description="View your Noxie profile and mood pulse.")
    @app_commands.guild_only()
    @app_commands.describe(user="Whose profile to view (defaults to yours)")
    async def profile_slash(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        target = user or interaction.user
        guild_id = str(interaction.guild_id)
        log.info(f"profile: user={interaction.user.id} viewing={target.id} guild={guild_id}")

        try:
            bal    = economy.get_balance(self.bot.db, str(target.id), guild_id)
            badges = economy.get_badges(self.bot.db, str(target.id))

            streak = bal["hunt_streak"]
            luck   = min(1.0, streak / 20.0)
            vibe   = personality.vibe_status(streak, luck)

            tone = personality.active_tone(streak, luck)
            tone_to_event = {
                "chaotic":   "reaction_evil",
                "cozy":      "reaction_cozy",
                "sarcastic": "hunt_fail",
                "deadpan":   "mood_neutral",
            }
            banner_path = face_manager.get_face_for_event(tone_to_event.get(tone, "mood_neutral"))

            comps, files = build_mood_pulse_container(
                user_name=target.display_name,
                vibe_status=vibe,
                streak=streak,
                glow_shards=bal["glow_shards"],
                vibe_coins=bal["vibe_coins"],
                total_hunts=bal["total_hunts"],
                badges=badges,
                banner_path=banner_path,
                badge_display=BADGE_DISPLAY,
            )
            await send_cv2(interaction, comps, files)

        except Exception as e:
            log.error(f"profile_slash failed: user={target.id}", exc=e)
            try:
                await interaction.response.send_message("⚠️ couldn't load profile. try again?", ephemeral=True)
            except Exception:
                pass

    # ── prefix profile ───────────────────────────────────────────────────────

    @commands.command(name="profile", aliases=["me", "p"])
    @commands.guild_only()
    async def profile_prefix(
        self, ctx: commands.Context, user: discord.Member | None = None
    ) -> None:
        """View your Noxie profile."""
        target = user or ctx.author
        guild_id = str(ctx.guild.id)
        log.info(f"profile: user={ctx.author.id} viewing={target.id} guild={guild_id}")

        try:
            bal    = economy.get_balance(self.bot.db, str(target.id), guild_id)
            badges = economy.get_badges(self.bot.db, str(target.id))

            streak = bal["hunt_streak"]
            luck   = min(1.0, streak / 20.0)
            vibe   = personality.vibe_status(streak, luck)

            tone = personality.active_tone(streak, luck)
            tone_to_event = {
                "chaotic":   "reaction_evil",
                "cozy":      "reaction_cozy",
                "sarcastic": "hunt_fail",
                "deadpan":   "mood_neutral",
            }
            banner_path = face_manager.get_face_for_event(tone_to_event.get(tone, "mood_neutral"))

            comps, files = build_mood_pulse_container(
                user_name=target.display_name,
                vibe_status=vibe,
                streak=streak,
                glow_shards=bal["glow_shards"],
                vibe_coins=bal["vibe_coins"],
                total_hunts=bal["total_hunts"],
                badges=badges,
                banner_path=banner_path,
                badge_display=BADGE_DISPLAY,
            )
            await send_cv2(ctx, comps, files)

        except Exception as e:
            log.error(f"profile_prefix failed: user={target.id}", exc=e)
            try:
                await ctx.send("⚠️ couldn't load profile. try again?")
            except Exception:
                pass


async def setup(bot: "NoxieBot") -> None:
    await bot.add_cog(ProfileCog(bot))
