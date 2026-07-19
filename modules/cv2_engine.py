"""
cv2_engine.py — Discord Components V2 container builder for Noxie.

All CV2 messages are sent with:
    flags=discord.MessageFlags(is_components_v2=True)
    components=[container]
    files=[...]     ← attached mood banner image

Mood banners are ALWAYS placed at the BOTTOM of containers that require them:
  - hunt results
  - donation flow containers
  - vibe creature displays
  - mood pulse containers
"""

from __future__ import annotations

import discord
from pathlib import Path
from typing import Optional


# ── Rarity color map (decimal) ────────────────────────────────────────────────

RARITY_COLORS: dict[str, int] = {
    "common":    0x829882,
    "uncommon":  0x4CAF50,
    "rare":      0x4A90E2,
    "epic":      0x9B59B6,
    "legendary": 0xFFD700,
    "mythic":    0xFF6BF6,
}


# ── Small helpers ─────────────────────────────────────────────────────────────

def _accent(color_int: int) -> discord.Color:
    return discord.Color(color_int)


def _make_file(path: str, filename: str) -> discord.File:
    return discord.File(path, filename=filename)


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
    Build a CV2 container for a hunt result.
    Returns (components_list, files_list).

    Layout:
      TOP    — creature artwork (MediaGallery)
      MIDDLE — stats, rewards, personality line
      BOTTOM — mood banner (MediaGallery)
    """
    rarity = creature.get("rarity", "common")
    color = RARITY_COLORS.get(rarity, RARITY_COLORS["common"])

    rarity_labels = {
        "common":    "◽ Common",
        "uncommon":  "🟩 Uncommon",
        "rare":      "🔷 Rare",
        "epic":      "🟣 Epic",
        "legendary": "⭐ Legendary",
        "mythic":    "🌌 Mythic",
    }
    rarity_label = rarity_labels.get(rarity, rarity.capitalize())

    mood_emoji_map = {
        "melancholy": "🌧️",
        "chaotic":    "⚡",
        "cozy":       "🌿",
        "neutral":    "🫧",
        "sarcastic":  "🌑",
    }
    mood_emoji = mood_emoji_map.get(creature.get("mood", "neutral"), "✨")

    files: list[discord.File] = []
    inner: list = []

    # ── Creature artwork at the TOP ────────────────────────────────────────────
    if art_path:
        art_filename = f"art_{creature['id']}.png"
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media=f"attachment://{art_filename}")]
            )
        )
        files.append(_make_file(art_path, art_filename))
        inner.append(discord.ui.Separator(divider=False))

    # ── Stats and info ─────────────────────────────────────────────────────────
    inner += [
        discord.ui.TextDisplay(
            content=f"## {creature['emoji']}  {creature['name']}\n"
                    f"{creature['description']}"
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(
            content=(
                f"**Rarity** — {rarity_label}\n"
                f"**Mood**   — {mood_emoji} {creature.get('mood', 'neutral').capitalize()}\n"
                f"**Vibe**   — 〔 {creature.get('vibe', '???').upper()} 〕\n"
                f"**Power**  — `{creature.get('power', 0):,}`"
            )
        ),
        discord.ui.Separator(divider=False),
        discord.ui.TextDisplay(
            content=(
                f"**Rewards:** +{glow_earned} Glow Shards  ·  +{coins_earned} Vibe Coins\n"
                f"*Total hunts: {total_hunts}*"
            )
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(content=f"*{personality_line}*"),
    ]

    # ── Mood banner at the BOTTOM ──────────────────────────────────────────────
    if banner_path:
        banner_filename = f"banner_{rarity}.jpeg"
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media=f"attachment://{banner_filename}")]
            )
        )
        files.append(_make_file(banner_path, banner_filename))

    container = discord.ui.Container(
        children=inner,
        accent_color=discord.Color(color),
    )
    return [container], files


# ── CREATURE DISPLAY container ────────────────────────────────────────────────

def build_creature_container(
    creature: dict,
    count: int,
    art_path: Optional[str] = None,
    banner_path: Optional[str] = None,
) -> tuple[list, list[discord.File]]:
    """
    Build a CV2 container for displaying a vibe creature in inventory/profile.

    Layout:
      TOP    — creature artwork (MediaGallery)
      MIDDLE — stats
      BOTTOM — mood banner (MediaGallery)
    """
    rarity = creature.get("rarity", "common")
    color = RARITY_COLORS.get(rarity, RARITY_COLORS["common"])

    files: list[discord.File] = []
    inner: list = []

    # ── Creature artwork at the TOP ────────────────────────────────────────────
    if art_path:
        art_filename = f"art_{creature['id']}.png"
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media=f"attachment://{art_filename}")]
            )
        )
        files.append(_make_file(art_path, art_filename))
        inner.append(discord.ui.Separator(divider=False))

    # ── Stats ──────────────────────────────────────────────────────────────────
    inner += [
        discord.ui.TextDisplay(
            content=f"## {creature['emoji']}  {creature['name']}  ×{count}\n"
                    f"> {creature['description']}"
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(
            content=(
                f"**Rarity** — {rarity.capitalize()}\n"
                f"**Mood**   — {creature.get('mood', 'neutral').capitalize()}\n"
                f"**Vibe**   — {creature.get('vibe', '???').upper()}\n"
                f"**Power**  — `{creature.get('power', 0):,}`"
            )
        ),
    ]

    # ── Mood banner at BOTTOM ──────────────────────────────────────────────────
    if banner_path:
        inner.append(discord.ui.Separator(divider=False))
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media="attachment://creature_banner.jpeg")]
            )
        )
        files.append(_make_file(banner_path, "creature_banner.jpeg"))

    container = discord.ui.Container(
        children=inner,
        accent_color=discord.Color(color),
    )
    return [container], files


# ── MOOD PULSE container ──────────────────────────────────────────────────────

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
    Build a mood pulse / profile CV2 container.
    Mood banner at BOTTOM.
    """
    badge_display = badge_display or {}
    badge_str = "  ".join(
        badge_display.get(b, f"[{b}]") for b in badges
    ) if badges else "*no badges yet*"

    inner: list = [
        discord.ui.TextDisplay(
            content=f"## 👁️  {user_name}'s Vibe Profile"
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(
            content=(
                f"**Current Vibe** — {vibe_status}\n"
                f"**Hunt Streak**  — 🔥 {streak}\n"
                f"**Total Hunts**  — {total_hunts:,}"
            )
        ),
        discord.ui.Separator(divider=False),
        discord.ui.TextDisplay(
            content=(
                f"**Glow Shards** — `{glow_shards:,}` ✨\n"
                f"**Vibe Coins**  — `{vibe_coins:,}` 🪙"
            )
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(content=f"**Badges**\n{badge_str}"),
    ]

    files: list[discord.File] = []

    # ── Mood banner at BOTTOM ──────────────────────────────────────────────────
    if banner_path:
        inner.append(discord.ui.Separator(divider=False))
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media="attachment://mood_pulse.jpeg")]
            )
        )
        files.append(_make_file(banner_path, "mood_pulse.jpeg"))

    container = discord.ui.Container(
        children=inner,
        accent_color=discord.Color(0x7930A7),
    )
    return [container], files


# ── INVENTORY container ───────────────────────────────────────────────────────

def build_inventory_container(
    user_name: str,
    creature_counts: dict[str, int],
    all_creatures: dict[str, dict],
    page: int = 1,
    per_page: int = 6,
) -> tuple[list, list[discord.File]]:
    """
    Build an inventory listing container.  No mood banner (space saving).
    """
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
                f"{c.get('emoji','❓')} **{c.get('name', cid)}** ×{cnt} "
                f"— {c.get('rarity','?').capitalize()} · {c.get('mood','?').capitalize()}\n"
            )

    inner: list = [
        discord.ui.TextDisplay(
            content=f"## 🎒  {user_name}'s Collection  (page {page}/{total_pages})"
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(content=lines),
    ]

    container = discord.ui.Container(
        children=inner,
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
    """
    Build the donation initiation CV2 container (sent in DMs).
    Mood banner at BOTTOM.
    """
    inner: list = [
        discord.ui.TextDisplay(
            content="## 💎  Support Noxie"
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(
            content=(
                f"**Amount:**    `${amount_usd:.2f} USD`\n"
                f"**Currency:**  `{currency}`\n"
                f"**Send to:**\n```\n{crypto_address}\n```\n"
                f"**Exact amount:** `{crypto_amount} {currency}`\n"
                f"**Payment ID:** `{payment_id}`"
            )
        ),
        discord.ui.Separator(divider=False),
        discord.ui.TextDisplay(
            content=(
                "⏳ Send the exact amount shown above.\n"
                "Noxie will confirm automatically once payment is detected.\n"
                "*Powered by OxaPay*"
            )
        ),
    ]

    files: list[discord.File] = []

    # ── Mood banner at BOTTOM ──────────────────────────────────────────────────
    if banner_path:
        inner.append(discord.ui.Separator(divider=False))
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media="attachment://donate_start.jpeg")]
            )
        )
        files.append(_make_file(banner_path, "donate_start.jpeg"))

    container = discord.ui.Container(
        children=inner,
        accent_color=discord.Color(0xF0B429),
    )
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
    """
    Build the donation confirmation CV2 container (sent in DMs).
    Mood banner at BOTTOM.
    """
    badge_note = "\n🏅 **Donor Badge** unlocked!" if is_new_donor else ""

    inner: list = [
        discord.ui.TextDisplay(
            content="## 💖  Payment Confirmed!"
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(
            content=(
                f"**Amount received:** `${amount_usd:.2f}` in `{currency}`\n\n"
                f"**Rewards granted:**\n"
                f"  +`{glow_reward:,}` Glow Shards ✨\n"
                f"  +`{coin_reward:,}` Vibe Coins 🪙"
                f"{badge_note}"
            )
        ),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(content=f"*{personality_line}*"),
    ]

    files: list[discord.File] = []

    # ── Mood banner at BOTTOM ──────────────────────────────────────────────────
    if banner_path:
        inner.append(discord.ui.Separator(divider=False))
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media="attachment://donate_confirm.jpeg")]
            )
        )
        files.append(_make_file(banner_path, "donate_confirm.jpeg"))

    container = discord.ui.Container(
        children=inner,
        accent_color=discord.Color(0x2ECC71),
    )
    return [container], files


def build_donate_failed_container(
    reason: str = "payment not confirmed",
    banner_path: Optional[str] = None,
) -> tuple[list, list[discord.File]]:
    """
    Build a donation failure container (sent in DMs).
    Mood banner at BOTTOM.
    """
    inner: list = [
        discord.ui.TextDisplay(content="## ❌  Donation Issue"),
        discord.ui.Separator(divider=True),
        discord.ui.TextDisplay(
            content=(
                f"Something went wrong: *{reason}*\n\n"
                "Please try again or contact a server admin."
            )
        ),
    ]

    files: list[discord.File] = []

    if banner_path:
        inner.append(discord.ui.Separator(divider=False))
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media="attachment://donate_fail.jpeg")]
            )
        )
        files.append(_make_file(banner_path, "donate_fail.jpeg"))

    container = discord.ui.Container(
        children=inner,
        accent_color=discord.Color(0xE74C3C),
    )
    return [container], files


# ── FACE REACTION (standalone) ────────────────────────────────────────────────

def build_face_reaction_container(
    message: str,
    banner_path: Optional[str] = None,
    color: int = 0x7930A7,
) -> tuple[list, list[discord.File]]:
    """
    Generic Noxie face reaction container. Mood banner at bottom if provided.
    """
    inner: list = [
        discord.ui.TextDisplay(content=message),
    ]

    files: list[discord.File] = []

    if banner_path:
        inner.append(discord.ui.Separator(divider=False))
        inner.append(
            discord.ui.MediaGallery(
                items=[discord.ui.MediaGalleryItem(media="attachment://face.jpeg")]
            )
        )
        files.append(_make_file(banner_path, "face.jpeg"))

    container = discord.ui.Container(
        children=inner,
        accent_color=discord.Color(color),
    )
    return [container], files


# ── Send helper ───────────────────────────────────────────────────────────────

async def send_cv2(
    target,  # ctx, channel, or interaction
    components: list,
    files: list[discord.File],
    ephemeral: bool = False,
) -> None:
    """
    Unified send for CV2 messages across ctx, channel, and interaction.
    """
    flags = discord.MessageFlags(is_components_v2=True)
    kwargs = dict(components=components, files=files, flags=flags)

    if isinstance(target, discord.Interaction):
        if ephemeral:
            kwargs["ephemeral"] = True
        if target.response.is_done():
            await target.followup.send(**kwargs)
        else:
            await target.response.send_message(**kwargs)
    elif hasattr(target, "send"):
        await target.send(**kwargs)
    else:
        raise TypeError(f"Cannot send to target of type {type(target)}")
