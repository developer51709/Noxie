"""
main.py — Noxie bot entry point.

Noxie is a vibe-based expressive companion bot using discord.py 2.3+
and Discord Components V2 (CV2).

Run:
    python main.py

Requires:
    - BOT_TOKEN in config.json or NOXIE_TOKEN environment variable
    - discord.py >= 2.3.0
    - aiohttp >= 3.9.0
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import traceback
from pathlib import Path

import discord
from discord.ext import commands

from modules.utils import load_config, get_db_conn, ROOT
from modules.prefixes import prefix_callable, init_prefix_table
from modules.economy import init_db as init_economy_db
from modules import cv2_engine, face_manager, personality, logger


CONFIG = load_config()


# ── Bot class ────────────────────────────────────────────────────────────────

class NoxieBot(commands.Bot):
    """The Noxie bot. Vibe engine. Character. Chaos."""

    db: sqlite3.Connection

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=prefix_callable,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
        )

    async def setup_hook(self) -> None:
        """Called before bot starts. Initialise DB, load cogs, sync slash commands."""
        # ── Database ──────────────────────────────────────────────────────────
        self.db = get_db_conn(CONFIG)
        init_prefix_table(self.db)
        init_economy_db(self.db)
        logger.success("database initialised")

        # ── Cogs ──────────────────────────────────────────────────────────────
        cogs = [
            "modules.prefixes",
            "modules.hunt_system",
            "modules.donate",
            "modules.profile",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                # Individual cog setup() functions log their own success lines
            except Exception as exc:
                logger.error(f"failed to load cog: {cog}", exc=exc)

        # ── Sync slash commands ───────────────────────────────────────────────
        try:
            synced = await self.tree.sync()
            logger.success(f"slash commands synced ({len(synced)} commands)")
        except Exception as exc:
            logger.error("slash command sync failed", exc=exc)

    async def on_ready(self) -> None:
        logger.divider()
        logger.info(f"logged in as  {self.user}  ({self.user.id})")
        logger.info(f"serving       {len(self.guilds)} guild(s)")
        logger.divider()

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the vibe"
            )
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Greet a new server with a face reaction."""
        logger.info(f"joined guild: {guild.name} ({guild.id})")
        line = personality.get_line("greeting")
        banner = face_manager.get_face_for_event("guild_join")
        comps, files = cv2_engine.build_face_reaction_container(
            message=(
                f"## 👁️ noxie has arrived.\n\n{line}\n\n"
                f"Use `noxie hunt` to start catching vibe creatures.\n"
                f"Use `noxie help` for all commands."
            ),
            banner_path=banner,
            color=0x7930A7,
        )
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await cv2_engine.send_cv2(channel, comps, files)
                except Exception as exc:
                    logger.warn(f"guild_join greeting failed in #{channel.name}: {exc}")
                break

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info(f"left guild: {guild.name} ({guild.id})")

    # ── Global prefix command error handler ───────────────────────────────────

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Catch-all for prefix command errors."""

        # Unwrap CheckFailure chains
        original = getattr(error, "original", error)

        if isinstance(error, commands.CommandOnCooldown):
            line = personality.get_line("cooldown")
            banner = face_manager.get_face_for_event("cooldown")
            comps, files = cv2_engine.build_face_reaction_container(
                message=f"⏳ **cooldown:** {error.retry_after:.1f}s\n*{line}*",
                banner_path=banner,
                color=0x4A4A4A,
            )
            try:
                await cv2_engine.send_cv2(ctx, comps, files)
            except Exception as exc:
                logger.error("cooldown response send failed", exc=exc)

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to do that.", delete_after=5)

        elif isinstance(error, commands.CommandNotFound):
            pass  # silently ignore unknown commands

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"❌ Missing argument: `{error.param.name}`.\n"
                f"Use `noxie help` for usage details.",
                delete_after=8,
            )

        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                f"❌ Bad argument — {error}\nUse `noxie help` for usage details.",
                delete_after=8,
            )

        else:
            logger.error(
                f"unhandled prefix command error in {ctx.command!r} "
                f"for user={ctx.author.id}",
                exc=original,
            )
            line = personality.get_line("error")
            banner = face_manager.get_face_for_event("error")
            comps, files = cv2_engine.build_face_reaction_container(
                message=f"⚠️ something went wrong\n*{line}*",
                banner_path=banner,
                color=0xE74C3C,
            )
            try:
                await cv2_engine.send_cv2(ctx, comps, files)
            except Exception as exc:
                logger.error("error response send failed", exc=exc)
                await ctx.send("⚠️ something went wrong. check the logs.")

    # ── Global slash command error handler ────────────────────────────────────

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        """Catch-all for slash command errors."""
        original = getattr(error, "original", error)
        logger.error(
            f"unhandled slash command error "
            f"cmd={getattr(interaction.command, 'name', '?')} "
            f"user={interaction.user.id}",
            exc=original,
        )

        line = personality.get_line("error")
        banner = face_manager.get_face_for_event("error")
        comps, files = cv2_engine.build_face_reaction_container(
            message=f"⚠️ something broke\n*{line}*",
            banner_path=banner,
            color=0xE74C3C,
        )
        try:
            await cv2_engine.send_cv2(interaction, comps, files, ephemeral=True)
        except Exception as exc:
            logger.error("slash error response send failed", exc=exc)
            # Last-resort plain-text fallback
            try:
                msg = "⚠️ something broke. try again."
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
            except Exception:
                pass


# ── Custom help command ───────────────────────────────────────────────────────

async def _send_help(ctx: commands.Context) -> None:
    bot: NoxieBot = ctx.bot
    banner = face_manager.get_face_for_event("mood_neutral")
    comps, files = cv2_engine.build_face_reaction_container(
        message=(
            "## 👁️  noxie commands\n\n"
            "**Hunting**\n"
            "`noxie hunt` / `/hunt` — catch a vibe creature\n"
            "`noxie inventory` / `/inventory` — view your collection\n"
            "`noxie vibe` / `/vibe` — check your vibe status\n\n"
            "**Profile**\n"
            "`noxie profile` / `/profile` — your mood pulse\n\n"
            "**Donation**\n"
            "`noxie donate <amount> [currency]` / `/donate` — support Noxie via crypto\n\n"
            "**Prefixes**\n"
            "`noxie prefix` — list active prefixes\n"
            "`noxie prefix add <prefix>` — add a custom prefix\n"
            "`noxie prefix remove <prefix>` — remove a custom prefix\n\n"
            "*The global prefix `noxie ` is always active.*"
        ),
        banner_path=banner,
        color=0x7930A7,
    )
    try:
        await cv2_engine.send_cv2(ctx, comps, files)
    except Exception as exc:
        logger.error("help send failed", exc=exc)
        await ctx.send("⚠️ couldn't load help. try again.")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    logger.startup_banner()

    token = os.environ.get("NOXIE_TOKEN") or CONFIG.get("bot_token", "")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "No bot token found. "
            "Set NOXIE_TOKEN environment variable or add bot_token to config.json"
        )
        return

    logger.info("starting Noxie …")

    bot = NoxieBot()

    @bot.command(name="help", aliases=["commands", "cmds"])
    async def help_cmd(ctx: commands.Context) -> None:
        await _send_help(ctx)

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
