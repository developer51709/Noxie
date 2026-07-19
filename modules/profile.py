"""
profile.py — /profile command for Noxie.

Shows a user's mood pulse container with stats, badges, and mood banner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from modules import economy, cv2_engine, face_manager, personality
from modules.economy import BADGE_DISPLAY

if TYPE_CHECKING:
    from main import NoxieBot


class ProfileCog(commands.Cog, name="Profile"):
    """User profile and mood pulse."""

    def __init__(self, bot: "NoxieBot") -> None:
        self.bot = bot

    # ── /profile slash ───────────────────────────────────────────────────────

    @app_commands.command(name="profile", description="View your Noxie profile and mood pulse.")
    @app_commands.guild_only()
    @app_commands.describe(user="Whose profile to view (defaults to yours)")
    async def profile_slash(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        await interaction.response.defer()
        target = user or interaction.user
        guild_id = str(interaction.guild_id)

        bal    = economy.get_balance(self.bot.db, str(target.id), guild_id)
        badges = economy.get_badges(self.bot.db, str(target.id))

        streak = bal["hunt_streak"]
        luck   = min(1.0, streak / 20.0)
        vibe   = personality.vibe_status(streak, luck)

        tone   = personality.active_tone(streak, luck)
        # Pick banner based on active tone
        tone_to_event = {
            "chaotic":   "reaction_evil",
            "cozy":      "reaction_cozy",
            "sarcastic": "hunt_fail",
            "deadpan":   "mood_neutral",
        }
        banner_path = face_manager.get_face_for_event(tone_to_event.get(tone, "mood_neutral"))

        comps, files = cv2_engine.build_mood_pulse_container(
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
        await cv2_engine.send_cv2(interaction, comps, files)

    # ── prefix profile ───────────────────────────────────────────────────────

    @commands.command(name="profile", aliases=["me", "p"])
    @commands.guild_only()
    async def profile_prefix(
        self, ctx: commands.Context, user: discord.Member | None = None
    ) -> None:
        """View your Noxie profile."""
        target = user or ctx.author
        guild_id = str(ctx.guild.id)

        bal    = economy.get_balance(self.bot.db, str(target.id), guild_id)
        badges = economy.get_badges(self.bot.db, str(target.id))

        streak = bal["hunt_streak"]
        luck   = min(1.0, streak / 20.0)
        vibe   = personality.vibe_status(streak, luck)

        tone   = personality.active_tone(streak, luck)
        tone_to_event = {
            "chaotic":   "reaction_evil",
            "cozy":      "reaction_cozy",
            "sarcastic": "hunt_fail",
            "deadpan":   "mood_neutral",
        }
        banner_path = face_manager.get_face_for_event(tone_to_event.get(tone, "mood_neutral"))

        comps, files = cv2_engine.build_mood_pulse_container(
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
        await cv2_engine.send_cv2(ctx, comps, files)


async def setup(bot: "NoxieBot") -> None:
    await bot.add_cog(ProfileCog(bot))
