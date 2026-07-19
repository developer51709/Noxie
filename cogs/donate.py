"""
cogs/donate.py — OxaPay donation system for Noxie.

Flow:
  1. User runs /donate <amount> or "noxie donate <amount>"
  2. Bot creates an OxaPay invoice via their REST API
  3. Bot DMs the user a CV2 container with payment details + mood banner at bottom
  4. Bot polls OxaPay for payment status (up to ~10 minutes)
  5. On confirmation:
     - Economy rewards granted (Glow Shards + Vibe Coins)
     - Donor badge awarded
     - Donation logged in SQLite
     - CV2 "thank you" container sent in DMs with mood banner at bottom
  6. On failure/timeout: CV2 error container sent in DMs with mood banner at bottom

CV2 containers defined here:
  build_donate_start_container   — payment instructions card
  build_donate_confirm_container — success/thank-you card
  build_donate_failed_container  — failure card
"""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils import economy, face_manager, personality
from utils.helpers import load_config
from utils.cv2_helpers import _make_file, _media, _sep, send_cv2

if TYPE_CHECKING:
    from main import NoxieBot

CONFIG = load_config()

OXAPAY_KEY      = CONFIG.get("oxapay_merchant_key", "")
OXAPAY_BASE     = CONFIG.get("oxapay_base_url", "https://api.oxapay.com")
ECON_CFG        = CONFIG.get("economy", {})
GS_PER_USD      = ECON_CFG.get("donation_glow_shards_per_usd", 500)
VC_PER_USD      = ECON_CFG.get("donation_vibe_coins_per_usd", 50)

POLL_INTERVAL   = 15   # seconds between status checks
POLL_MAX        = 40   # max polls (~10 min)

SUPPORTED_CURRENCIES = ["USDT", "BTC", "ETH", "LTC", "BNB", "DOGE", "TRX"]


# ── CV2 containers ────────────────────────────────────────────────────────────

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


# ── OxaPay API wrappers ───────────────────────────────────────────────────────

async def create_invoice(
    session: aiohttp.ClientSession,
    amount_usd: float,
    currency: str,
    order_id: str,
    description: str = "Noxie donation",
) -> dict:
    """POST /merchants/request to create a payment invoice."""
    url = f"{OXAPAY_BASE}/merchants/request"
    payload = {
        "merchant":    OXAPAY_KEY,
        "amount":      amount_usd,
        "currency":    "USD",
        "payCurrency": currency,
        "lifeTime":    600,
        "orderId":     order_id,
        "description": description,
        "returnUrl":   "",
        "callbackUrl": "",
    }
    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as r:
        data = await r.json()
        if data.get("result") != 100:
            raise RuntimeError(f"OxaPay error: {data.get('message', data)}")
        return data


async def check_invoice(
    session: aiohttp.ClientSession,
    track_id: str,
) -> dict:
    """POST /merchants/inquiry to check payment status."""
    url = f"{OXAPAY_BASE}/merchants/inquiry"
    payload = {"merchant": OXAPAY_KEY, "trackId": track_id}
    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
        return await r.json()


# ── Reward calculation ────────────────────────────────────────────────────────

def calc_rewards(amount_usd: float) -> tuple[int, int]:
    glow  = math.ceil(amount_usd * GS_PER_USD)
    coins = math.ceil(amount_usd * VC_PER_USD)
    return glow, coins


# ── Main donation flow ────────────────────────────────────────────────────────

async def run_donation_flow(
    bot: "NoxieBot",
    user: discord.User,
    guild_id: Optional[str],
    amount_usd: float,
    currency: str,
) -> None:
    """Full async donation flow. Runs in background after initial ack."""
    order_id = f"noxie-{user.id}-{int(asyncio.get_event_loop().time())}"

    try:
        dm = await user.create_dm()
    except discord.Forbidden:
        return

    async with aiohttp.ClientSession() as session:
        # Step 1: create invoice
        try:
            data = await create_invoice(session, amount_usd, currency, order_id)
        except Exception as e:
            banner = face_manager.get_face_for_event("donate_fail")
            comps, files = build_donate_failed_container(reason=str(e), banner_path=banner)
            await send_cv2(dm, comps, files)
            return

        track_id    = data.get("trackId", "")
        pay_address = data.get("payAddress", "N/A")
        pay_amount  = str(data.get("payAmount", "?"))

        # Step 2: send payment instructions in DMs
        banner_start = face_manager.get_face_for_event("donate_start")
        comps, files = build_donate_start_container(
            amount_usd=amount_usd,
            currency=currency,
            crypto_address=pay_address,
            crypto_amount=pay_amount,
            payment_id=track_id,
            banner_path=banner_start,
        )
        await send_cv2(dm, comps, files)

        # Step 3: poll for confirmation
        confirmed = False
        tx_id     = track_id

        for _ in range(POLL_MAX):
            await asyncio.sleep(POLL_INTERVAL)
            try:
                status_data = await check_invoice(session, track_id)
            except Exception:
                continue

            status = status_data.get("status", "").lower()

            if status in ("paid", "confirmed", "complete"):
                confirmed = True
                break
            if status in ("expired", "cancelled", "failed"):
                break

        # Step 4: handle result
        if confirmed:
            glow, coins = calc_rewards(amount_usd)
            gid = guild_id or "DM"

            economy.log_donation(bot.db, str(user.id), amount_usd, currency, tx_id)
            economy.add_currency(bot.db, str(user.id), gid, glow, coins)
            is_new_donor = economy.award_badge(bot.db, str(user.id), "donor")

            line = personality.get_line("donate_thanks")
            banner_done = face_manager.get_face_for_event("donate_done")
            comps, files = build_donate_confirm_container(
                amount_usd=amount_usd,
                currency=currency,
                glow_reward=glow,
                coin_reward=coins,
                is_new_donor=is_new_donor,
                personality_line=line,
                banner_path=banner_done,
            )
            await send_cv2(dm, comps, files)

        else:
            banner_fail = face_manager.get_face_for_event("donate_fail")
            comps, files = build_donate_failed_container(
                reason="payment expired or was not received",
                banner_path=banner_fail,
            )
            await send_cv2(dm, comps, files)


# ── Cog ───────────────────────────────────────────────────────────────────────

class DonateCog(commands.Cog, name="Donate"):
    """OxaPay donation commands."""

    def __init__(self, bot: "NoxieBot") -> None:
        self.bot = bot

    # ── /donate ──────────────────────────────────────────────────────────────

    @app_commands.command(name="donate", description="Support Noxie with a crypto donation!")
    @app_commands.describe(
        amount="Amount in USD (e.g. 5.00)",
        currency="Crypto currency (USDT, BTC, ETH, LTC, BNB, DOGE, TRX)"
    )
    async def donate_slash(
        self,
        interaction: discord.Interaction,
        amount: float,
        currency: str = "USDT",
    ) -> None:
        currency = currency.upper()
        if currency not in SUPPORTED_CURRENCIES:
            await interaction.response.send_message(
                f"❌ Unsupported currency. Choose from: {', '.join(SUPPORTED_CURRENCIES)}",
                ephemeral=True,
            )
            return
        if amount < 1.0:
            await interaction.response.send_message(
                "❌ Minimum donation is $1.00 USD.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "💌 Check your DMs! The donation flow is being set up.",
            ephemeral=True,
        )

        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        asyncio.create_task(
            run_donation_flow(self.bot, interaction.user, guild_id, amount, currency)
        )

    # ── prefix donate ─────────────────────────────────────────────────────────

    @commands.command(name="donate")
    async def donate_prefix(
        self,
        ctx: commands.Context,
        amount: float = 5.0,
        currency: str = "USDT",
    ) -> None:
        """Donate to support Noxie. Usage: noxie donate <amount> [currency]"""
        currency = currency.upper()
        if currency not in SUPPORTED_CURRENCIES:
            await ctx.send(
                f"❌ Unsupported currency. Choose from: {', '.join(SUPPORTED_CURRENCIES)}"
            )
            return
        if amount < 1.0:
            await ctx.send("❌ Minimum donation is $1.00 USD.")
            return

        await ctx.send("💌 Check your DMs! The donation flow is being set up.")
        guild_id = str(ctx.guild.id) if ctx.guild else None
        asyncio.create_task(
            run_donation_flow(self.bot, ctx.author, guild_id, amount, currency)
        )


async def setup(bot: "NoxieBot") -> None:
    await bot.add_cog(DonateCog(bot))
