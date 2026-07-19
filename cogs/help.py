"""
cogs/help.py — Noxie help command.

Renders a structured CV2 card with one section per command category.
Slash command links use the proper </name:id> format so Discord renders
them as clickable mentions. IDs come from bot.slash_ids, populated after
tree.sync() in setup_hook.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import face_manager
from utils.cv2_helpers import _make_file, _media, _sep, send_cv2
from utils.logger import log

if TYPE_CHECKING:
    from main import NoxieBot


# ── CV2 container ─────────────────────────────────────────────────────────────

def build_help_container(
    slash_ids: dict[str, int],
    banner_path: str | None = None,
) -> tuple[list, list[discord.File]]:
    """
    Structured help card.
    Uses </name:id> links for registered slash commands so Discord renders
    them as interactive mentions. Falls back to `/name` if an ID is missing.
    """

    def sl(name: str) -> str:
        """Return a slash command mention or a plain fallback."""
        cmd_id = slash_ids.get(name)
        return f"</{name}:{cmd_id}>" if cmd_id else f"`/{name}`"

    container = discord.ui.Container(
        # ── Header ────────────────────────────────────────────────────────
        discord.ui.TextDisplay(content="## 👁️  noxie — command guide"),
        _sep(visible=True),

        # ── Hunting ───────────────────────────────────────────────────────
        discord.ui.TextDisplay(
            content=(
                "**🌿  Hunting**\n"
                f"{sl('hunt')}  ·  `noxie hunt` — catch a vibe creature\n"
                f"{sl('inventory')}  ·  `noxie inventory [page]` — browse your collection\n"
                f"{sl('vibe')}  ·  `noxie vibe` — check your current vibe energy"
            )
        ),
        _sep(visible=False),

        # ── Profile ───────────────────────────────────────────────────────
        discord.ui.TextDisplay(
            content=(
                "**👁️  Profile**\n"
                f"{sl('profile')}  ·  `noxie profile [@user]` — view your mood pulse"
            )
        ),
        _sep(visible=False),

        # ── Donations ─────────────────────────────────────────────────────
        discord.ui.TextDisplay(
            content=(
                "**💎  Donations**\n"
                f"{sl('donate')}  ·  `noxie donate <amount> [currency]`\n"
                "-# sends crypto payment instructions to your DMs via OxaPay\n"
                "-# supported: USDT · BTC · ETH · LTC · BNB · DOGE · TRX"
            )
        ),
        _sep(visible=True),

        # ── Prefixes ──────────────────────────────────────────────────────
        discord.ui.TextDisplay(
            content=(
                "**⚙️  Prefixes**\n"
                "`noxie prefix` — list active prefixes for this server\n"
                "`noxie prefix add <prefix>` — add a custom prefix\n"
                "`noxie prefix remove <prefix>` — remove a custom prefix\n"
                "-# the global prefix `noxie ` is always active and cannot be removed"
            )
        ),

        accent_color=discord.Color(0x7930A7),
    )

    files: list[discord.File] = []

    if banner_path:
        container.add_item(_sep(visible=False))
        container.add_item(_media("help_banner.jpeg"))
        files.append(_make_file(banner_path, "help_banner.jpeg"))

    return [container], files


# ── Cog ───────────────────────────────────────────────────────────────────────

class HelpCog(commands.Cog, name="Help"):
    """Noxie help command."""

    def __init__(self, bot: "NoxieBot") -> None:
        self.bot = bot

    @commands.command(name="help", aliases=["commands", "cmds"])
    async def help_cmd(self, ctx: commands.Context) -> None:
        """Show all Noxie commands."""
        log.info(f"help: user={ctx.author.id} guild={ctx.guild.id if ctx.guild else 'DM'}")
        banner = face_manager.get_face_for_event("mood_neutral")
        comps, files = build_help_container(
            slash_ids=self.bot.slash_ids,
            banner_path=banner,
        )
        await send_cv2(ctx, comps, files)


async def setup(bot: "NoxieBot") -> None:
    await bot.add_cog(HelpCog(bot))
