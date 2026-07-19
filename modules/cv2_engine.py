"""
cv2_engine.py — Discord Components V2 container builder for Noxie.

Send path:
    send_cv2() wraps all components in a discord.ui.LayoutView and sends
    via response.send_message() or ctx.send() — the library sets the CV2
    message flag automatically.

Container builder conventions (must match the working profile pattern):
    - discord.ui.Container(*items, accent_color=color)   ← unpack, NOT children=
    - discord.ui.Separator(visible=True/False)           ← NOT divider=
    - discord.ui.MediaGallery(discord.MediaGalleryItem(media="attachment://..."))
                                                         ← positional, top-level class
    - container.add_item(…) for conditional banner rows  ← appended after construction

Mood banners are ALWAYS placed at the BOTTOM of containers that need them.
"""

from __future__ import annotations

import discord
from typing import Optional


# ── Rarity color map ──────────────────────────────────────────────────────────

RARITY_COLORS: dict[str, int] = {
    "common":    0x829882,
    "uncommon":  0x4CAF50,
    "rare":      0x4A90E2,
    "epic":      0x9B59B6,
    "legendary": 0xFFD700,
    "mythic":    0xFF6BF6,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_file(path: str, filename: str) -> discord.File:
    return discord.File(path, filename=filename)


def _media(attachment_name: str) -> discord.ui.MediaGallery:
    """One-image MediaGallery using the top-level discord.MediaGalleryItem."""
    return discord.ui.MediaGallery(
        discord.MediaGalleryItem(media=f"attachment://{attachment_name}")
    )


def _sep(visible: bool = False) -> discord.ui.Separator:
    return discord.ui.Separator(visible=visible)


# ── HUNT RESULT container ─────────────────────────────────────────────────────

def build_hunt_container(
    creature: dict,
    glow_earned: int,
    coins_earned: int,
    total_hunts: int,
    personality_line: str,
    art_path: Optional[str] = None,
    banner_path: Optional[str] = None,
) -> tuple[list, list[discord.File]]:
    """
    Hunt result container.
    Layout: creature art (top) → stats → rewards → personality line → mood banner (bottom)
    """
    rarity = creature.get("rarity", "common")
    color  = RARITY_COLORS.get(rarity, RARITY_COLORS["common"])

    rarity_labels = {
        "common":    "◽ Common",
        "uncommon":  "🟩 Uncommon",
        "rare":      "🔷 Rare",
        "epic":      "🟣 Epic",
        "legendary": "⭐ Legendary",
        "mythic":    "🌌 Mythic",
    }
    mood_emojis = {
        "melancholy": "🌧️", "chaotic": "⚡", "cozy": "🌿",
        "neutral": "🫧", "sarcastic": "🌑",
    }

    rarity_label = rarity_labels.get(rarity, rarity.capitalize())
    mood_emoji   = mood_emojis.get(creature.get("mood", "neutral"), "✨")

    files: list[discord.File] = []
    inner: list = []

    # Creature artwork — top
    if art_path:
        art_filename = f"art_{creature['id']}.png"
        inner.append(_media(art_filename))
        files.append(_make_file(art_path, art_filename))
        inner.append(_sep(visible=False))

    inner += [
        discord.ui.TextDisplay(
            content=f"## {creature['emoji']}  {creature['name']}\n{creature['description']}"
        ),
        _sep(visible=True),
        discord.ui.TextDisplay(
            content=(
                f"**Rarity** — {rarity_label}\n"
                f"**Mood**   — {mood_emoji} {creature.get('mood', 'neutral').capitalize()}\n"
                f"**Vibe**   — 〔 {creature.get('vibe', '???').upper()} 〕\n"
                f"**Power**  — `{creature.get('power', 0):,}`"
            )
        ),
        _sep(visible=False),
        discord.ui.TextDisplay(
            content=(
                f"**Rewards:** +{glow_earned} Glow Shards  ·  +{coins_earned} Vibe Coins\n"
                f"*Total hunts: {total_hunts}*"
            )
        ),
        _sep(visible=True),
        discord.ui.TextDisplay(content=f"*{personality_line}*"),
    ]

    container = discord.ui.Container(*inner, accent_color=discord.Color(color))

    # Mood banner — bottom
    if banner_path:
        banner_filename = f"banner_{rarity}.jpeg"
        container.add_item(_sep(visible=False))
        container.add_item(_media(banner_filename))
        files.append(_make_file(banner_path, banner_filename))

    return [container], files


# ── CREATURE DISPLAY container ────────────────────────────────────────────────

def build_creature_container(
    creature: dict,
    count: int,
    art_path: Optional[str] = None,
    banner_path: Optional[str] = None,
) -> tuple[list, list[discord.File]]:
    """
    Single creature display for inventory/profile detail.
    Layout: art (top) → stats → mood banner (bottom)
    """
    rarity = creature.get("rarity", "common")
    color  = RARITY_COLORS.get(rarity, RARITY_COLORS["common"])

    files: list[discord.File] = []
    inner: list = []

    if art_path:
        art_filename = f"art_{creature['id']}.png"
        inner.append(_media(art_filename))
        files.append(_make_file(art_path, art_filename))
        inner.append(_sep(visible=False))

    inner += [
        discord.ui.TextDisplay(
            content=f"## {creature['emoji']}  {creature['name']}  ×{count}\n"
                    f"> {creature['description']}"
        ),
        _sep(visible=True),
        discord.ui.TextDisplay(
            content=(
                f"**Rarity** — {rarity.capitalize()}\n"
                f"**Mood**   — {creature.get('mood', 'neutral').capitalize()}\n"
                f"**Vibe**   — {creature.get('vibe', '???').upper()}\n"
                f"**Power**  — `{creature.get('power', 0):,}`"
            )
        ),
    ]

    container = discord.ui.Container(*inner, accent_color=discord.Color(color))

    if banner_path:
        container.add_item(_sep(visible=False))
        container.add_item(_media("creature_banner.jpeg"))
        files.append(_make_file(banner_path, "creature_banner.jpeg"))

    return [container], files


# ── MOOD PULSE / PROFILE container ────────────────────────────────────────────

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
    """
    Profile / mood pulse container. Mood banner at bottom.
    """
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


# ── INVENTORY container ───────────────────────────────────────────────────────

def build_inventory_container(
    user_name: str,
    creature_counts: dict[str, int],
    all_creatures: dict[str, dict],
    page: int = 1,
    per_page: int = 6,
) -> tuple[list, list[discord.File]]:
    """Paged creature collection list. No mood banner."""
    items = list(creature_counts.items())
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    page_items = items[start:start + per_page]

    if not page_items:
        lines = "*your collection is empty — go hunt something*"
    else:
        lines = ""
        for cid, cnt in page_items:
            c = all_creatures.get(cid, {})
            lines += (
                f"{c.get('emoji', '❓')} **{c.get('name', cid)}** ×{cnt} "
                f"— {c.get('rarity', '?').capitalize()} · {c.get('mood', '?').capitalize()}\n"
            )

    container = discord.ui.Container(
        discord.ui.TextDisplay(
            content=f"## 🎒  {user_name}'s Collection  (page {page}/{total_pages})"
        ),
        _sep(visible=True),
        discord.ui.TextDisplay(content=lines),
        accent_color=discord.Color(0x4A4A6A),
    )
    return [container], []


# ── DONATION FLOW containers ──────────────────────────────────────────────────

def build_donate_start_container(
    amount_usd: float,
    currency: str,
    crypto_address: str,
    crypto_amount: str,
    payment_id: str,
    banner_path: Optional[str] = None,
) -> tuple[list, list[discord.File]]:
    """Donation initiation container sent in DMs. Mood banner at bottom."""
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 💎  Support Noxie"),
        _sep(visible=True),
        discord.ui.TextDisplay(
            content=(
                f"**Amount:**    `${amount_usd:.2f} USD`\n"
                f"**Currency:**  `{currency}`\n"
                f"**Send to:**\n```\n{crypto_address}\n```\n"
                f"**Exact amount:** `{crypto_amount} {currency}`\n"
                f"**Payment ID:** `{payment_id}`"
            )
        ),
        _sep(visible=False),
        discord.ui.TextDisplay(
            content=(
                "⏳ Send the exact amount shown above.\n"
                "Noxie will confirm automatically once payment is detected.\n"
                "*Powered by OxaPay*"
            )
        ),
        accent_color=discord.Color(0xF0B429),
    )

    files: list[discord.File] = []

    if banner_path:
        container.add_item(_sep(visible=False))
        container.add_item(_media("donate_start.jpeg"))
        files.append(_make_file(banner_path, "donate_start.jpeg"))

    return [container], files


def build_donate_confirm_container(
    amount_usd: float,
    currency: str,
    glow_reward: int,
    coin_reward: int,
    is_new_donor: bool,
    personality_line: str,
    banner_path: Optional[str] = None,
) -> tuple[list, list[discord.File]]:
    """Donation confirmation container sent in DMs. Mood banner at bottom."""
    badge_note = "\n🏅 **Donor Badge** unlocked!" if is_new_donor else ""

    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## 💖  Payment Confirmed!"),
        _sep(visible=True),
        discord.ui.TextDisplay(
            content=(
                f"**Amount received:** `${amount_usd:.2f}` in `{currency}`\n\n"
                f"**Rewards granted:**\n"
                f"  +`{glow_reward:,}` Glow Shards ✨\n"
                f"  +`{coin_reward:,}` Vibe Coins 🪙"
                f"{badge_note}"
            )
        ),
        _sep(visible=True),
        discord.ui.TextDisplay(content=f"*{personality_line}*"),
        accent_color=discord.Color(0x2ECC71),
    )

    files: list[discord.File] = []

    if banner_path:
        container.add_item(_sep(visible=False))
        container.add_item(_media("donate_confirm.jpeg"))
        files.append(_make_file(banner_path, "donate_confirm.jpeg"))

    return [container], files


def build_donate_failed_container(
    reason: str = "payment not confirmed",
    banner_path: Optional[str] = None,
) -> tuple[list, list[discord.File]]:
    """Donation failure container sent in DMs. Mood banner at bottom."""
    container = discord.ui.Container(
        discord.ui.TextDisplay(content="## ❌  Donation Issue"),
        _sep(visible=True),
        discord.ui.TextDisplay(
            content=(
                f"Something went wrong: *{reason}*\n\n"
                "Please try again or contact a server admin."
            )
        ),
        accent_color=discord.Color(0xE74C3C),
    )

    files: list[discord.File] = []

    if banner_path:
        container.add_item(_sep(visible=False))
        container.add_item(_media("donate_fail.jpeg"))
        files.append(_make_file(banner_path, "donate_fail.jpeg"))

    return [container], files


# ── FACE REACTION container ───────────────────────────────────────────────────

def build_face_reaction_container(
    message: str,
    banner_path: Optional[str] = None,
    color: int = 0x7930A7,
) -> tuple[list, list[discord.File]]:
    """Generic face/mood reaction container. Mood banner at bottom if provided."""
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
            # Already responded (e.g. after an ephemeral ack) — use followup.
            await target.followup.send(view=view, files=send_files, ephemeral=ephemeral)
        else:
            await target.response.send_message(view=view, files=send_files, ephemeral=ephemeral)
    elif hasattr(target, "send"):
        # commands.Context or any Messageable (channel, DM, etc.)
        await target.send(view=view, files=send_files)
    else:
        raise TypeError(f"Cannot send CV2 to target of type {type(target)}")
