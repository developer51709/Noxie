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

from utils.helpers import load_config, get_db_conn
from utils.economy import init_db as init_economy_db
from utils import face_manager, personality
from utils.cv2_helpers import build_face_reaction_container, send_cv2
from utils import logger
from cogs.prefixes import prefix_callable, init_prefix_table


CONFIG = load_config()


# ── Bot class ────────────────────────────────────────────────────────────────

class NoxieBot(commands.Bot):
    """The Noxie bot. Vibe engine. Character. Chaos."""

    db: sqlite3.Connection
    slash_ids: dict[str, int]   # populated after tree.sync() in setup_hook

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
        """Called before bot starts. Load cogs + sync slash commands."""
        # Connect DB
        self.db = get_db_conn(CONFIG)
        init_prefix_table(self.db)
        init_economy_db(self.db)

        # Load all cogs
        cogs = [
            "cogs.prefixes",
            "cogs.hunt",
            "cogs.donate",
            "cogs.profile",
            "cogs.help",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.success(f"loaded {cog}")
            except Exception as e:
                logger.error(f"failed to load {cog}", exc=e)

        # Sync application commands globally and store IDs for command links
        synced = await self.tree.sync()
        self.slash_ids = {cmd.name: cmd.id for cmd in synced}
        logger.success(f"slash commands synced ({len(synced)} registered)")

    async def on_ready(self) -> None:
        logger.info(f"🌑 Noxie is online — {self.user} ({self.user.id})")
        logger.info(f"   serving {len(self.guilds)} guild(s)")
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
        comps, files = build_face_reaction_container(
            message=f"## 👁️ noxie has arrived.\n\n{line}\n\n"
                    f"Use `noxie hunt` to start catching vibe creatures.\n"
                    f"Use `noxie help` for all commands.",
            banner_path=banner,
            color=0x7930A7,
        )
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await send_cv2(channel, comps, files)
                except Exception:
                    pass
                break

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info(f"left guild: {guild.name} ({guild.id})")

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Global prefix command error handler."""
        if isinstance(error, commands.CommandOnCooldown):
            line = personality.get_line("cooldown")
            banner = face_manager.get_face_for_event("cooldown")
            comps, files = build_face_reaction_container(
                message=f"⏳ **cooldown:** {error.retry_after:.1f}s\n*{line}*",
                banner_path=banner,
                color=0x4A4A4A,
            )
            await send_cv2(ctx, comps, files)

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
            comps, files = build_face_reaction_container(
                message=f"⚠️ something went wrong\n*{line}*",
                banner_path=banner,
                color=0xE74C3C,
            )
            await send_cv2(ctx, comps, files)
            logger.error(f"unhandled prefix command error: {error}", exc=error)

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        """Global slash command error handler."""
        line = personality.get_line("error")
        banner = face_manager.get_face_for_event("error")
        comps, files = build_face_reaction_container(
            message=f"⚠️ something broke\n*{line}*",
            banner_path=banner,
            color=0xE74C3C,
        )
        await send_cv2(interaction, comps, files, ephemeral=True)
        logger.error(f"unhandled slash command error: {error}", exc=error)


# ── Entry point ──────────────────────────────────────────────────────────────

async def main() -> None:
    logger.startup_banner()
    token = os.environ.get("NOXIE_TOKEN") or CONFIG.get("bot_token", "")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print(
            "❌ No bot token found.\n"
            "   Set NOXIE_TOKEN environment variable or add bot_token to config.json"
        )
        return

    bot = NoxieBot()

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
