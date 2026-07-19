"""
utils/cv2_helpers.py — Shared Discord Components V2 primitives for Noxie.

Contains:
  - Low-level builder helpers (_media, _sep, _make_file)
  - RARITY_COLORS used by multiple cogs
  - build_face_reaction_container — generic reaction display used by
    the hunt cog, main.py error handlers, and the help command
  - send_cv2 — unified send for ctx / channel / interaction targets

Cog-specific containers live in their respective cog files.
"""

from __future__ import annotations

from typing import Optional

import discord


# ── Rarity color map ──────────────────────────────────────────────────────────

RARITY_COLORS: dict[str, int] = {
    "common":    0x829882,
    "uncommon":  0x4CAF50,
    "rare":      0x4A90E2,
    "epic":      0x9B59B6,
    "legendary": 0xFFD700,
    "mythic":    0xFF6BF6,
}


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _make_file(path: str, filename: str) -> discord.File:
    return discord.File(path, filename=filename)


def _media(attachment_name: str) -> discord.ui.MediaGallery:
    """One-image MediaGallery using the top-level discord.MediaGalleryItem."""
    return discord.ui.MediaGallery(
        discord.MediaGalleryItem(media=f"attachment://{attachment_name}")
    )


def _sep(visible: bool = False) -> discord.ui.Separator:
    return discord.ui.Separator(visible=visible)


# ── Shared container builder ──────────────────────────────────────────────────

def build_face_reaction_container(
    message: str,
    banner_path: Optional[str] = None,
    color: int = 0x7930A7,
) -> tuple[list, list[discord.File]]:
    """
    Generic face/mood reaction container used across multiple cogs and main.py.
    Mood banner at bottom if provided.
    """
    container = discord.ui.Container(
        discord.ui.TextDisplay(content=message),
        accent_color=discord.Color(color),
    )

    files: list[discord.File] = []

    if banner_path:
        container.add_item(_sep(visible=False))
        container.add_item(_media("face.jpeg"))
        files.append(_make_file(banner_path, "face.jpeg"))

    return [container], files


# ── Send helper ───────────────────────────────────────────────────────────────

async def send_cv2(
    target,  # ctx, channel, or interaction
    components: list,
    files: list[discord.File],
    ephemeral: bool = False,
) -> None:
    """
    Unified CV2 send for ctx, channel, and interaction targets.

    Uses discord.ui.LayoutView — the correct container for CV2 top-level
    components (Container, TextDisplay, MediaGallery, etc.). Each component
    in the list is added individually; the library sets the CV2 flag automatically.
    """
    view = discord.ui.LayoutView()
    for item in components:
        view.add_item(item)

    # Pass files only when there are any; MISSING skips the parameter entirely.
    send_files = files if files else discord.utils.MISSING

    if isinstance(target, discord.Interaction):
        if target.response.is_done():
            # Already responded (e.g. after a defer) — use followup.
            await target.followup.send(view=view, files=send_files, ephemeral=ephemeral)
        else:
            await target.response.send_message(view=view, files=send_files, ephemeral=ephemeral)
    elif hasattr(target, "send"):
        # commands.Context or any Messageable (channel, DM, etc.)
        await target.send(view=view, files=send_files)
    else:
        raise TypeError(f"Cannot send CV2 to target of type {type(target)}")
