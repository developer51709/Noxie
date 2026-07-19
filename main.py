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
from modules import cv2_engine, face_manager, personality


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
            help_command=None,          # we'll add a custom one or just skip it
            case_insensitive=True,
            strip_after_prefix=True,
        )

    async def setup_hook(self) -> None:
        """Called before bot starts. Load cogs + sync slash commands."""
        # Connect DB
        self.db = get_db_conn(CONFIG)
        init_prefix_table(self.db)
        init_economy_db(self.db)

        # Load all cogs
        cogs = [
            "modules.prefixes",
            "modules.hunt_system",
            "modules.donate",
            "modules.profile",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"  ✓ loaded {cog}")
            except Exception as e:
                print(f"  ✗ failed to load {cog}: {e}")
                traceback.print_exc()

        # Sync application commands globally
        await self.tree.sync()
        print("  ✓ slash commands synced")

    async def on_ready(self) -> None:
        print(f"\n🌑 Noxie is online — {self.user} ({self.user.id})")
        print(f"   Serving {len(self.guilds)} guild(s)\n")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the vibe"
            )
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Greet a new server with a face reaction."""
        line = personality.get_line("greeting")
        banner = face_manager.get_face_for_event("guild_join")
        comps, files = cv2_engine.build_face_reaction_container(
            message=f"## 👁️ noxie has arrived.\n\n{line}\n\n"
                    f"Use `noxie hunt` to start catching vibe creatures.\n"
                    f"Use `noxie help` for all commands.",
            banner_path=banner,
            color=0x7930A7,
        )
        # Try to find a suitable channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await cv2_engine.send_cv2(channel, comps, files)
                except Exception:
                    pass
                break

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        print(f"Left guild: {guild.name} ({guild.id})")

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Global prefix command error handler."""
        if isinstance(error, commands.CommandOnCooldown):
            line = personality.get_line("cooldown")
            banner = face_manager.get_face_for_event("cooldown")
            comps, files = cv2_engine.build_face_reaction_container(
                message=f"⏳ **cooldown:** {error.retry_after:.1f}s\n*{line}*",
                banner_path=banner,
                color=0x4A4A4A,
            )
            await cv2_engine.send_cv2(ctx, comps, files)

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
        else:
            line = personality.get_line("error")
            banner = face_manager.get_face_for_event("error")
            comps, files = cv2_engine.build_face_reaction_container(
                message=f"⚠️ something went wrong\n*{line}*",
                banner_path=banner,
                color=0xE74C3C,
            )
            await cv2_engine.send_cv2(ctx, comps, files)
            # Log it
            traceback.print_exception(type(error), error, error.__traceback__)

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        """Global slash command error handler."""
        line = personality.get_line("error")
        banner = face_manager.get_face_for_event("error")
        comps, files = cv2_engine.build_face_reaction_container(
            message=f"⚠️ something broke\n*{line}*",
            banner_path=banner,
            color=0xE74C3C,
        )
        await cv2_engine.send_cv2(interaction, comps, files, ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)


# ── Custom help command (prefix) ─────────────────────────────────────────────

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
    await cv2_engine.send_cv2(ctx, comps, files)


# ── Entry point ──────────────────────────────────────────────────────────────

async def main() -> None:
    token = os.environ.get("NOXIE_TOKEN") or CONFIG.get("bot_token", "")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print(
            "❌ No bot token found.\n"
            "   Set NOXIE_TOKEN environment variable or add bot_token to config.json"
        )
        return

    bot = NoxieBot()

    # Register a simple help command directly on the bot
    @bot.command(name="help", aliases=["commands", "cmds"])
    async def help_cmd(ctx: commands.Context) -> None:
        await _send_help(ctx)

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
