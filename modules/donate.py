"""
donate.py — OxaPay donation system for Noxie.

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
"""

from __future__ import annotations

import asyncio
import math
from typing import TYPE_CHECKING, Optional

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands

from modules import economy, cv2_engine, face_manager, personality, logger
from modules.utils import load_config

if TYPE_CHECKING:
    from main import NoxieBot

CONFIG = load_config()

OXAPAY_KEY  = CONFIG.get("oxapay_merchant_key", "")
OXAPAY_BASE = CONFIG.get("oxapay_base_url", "https://api.oxapay.com")
ECON_CFG    = CONFIG.get("economy", {})

GS_PER_USD = ECON_CFG.get("donation_glow_shards_per_usd", 500)
VC_PER_USD = ECON_CFG.get("donation_vibe_coins_per_usd", 50)

POLL_INTERVAL = 15   # seconds between status checks
POLL_MAX      = 40   # max polls (~10 min)

SUPPORTED_CURRENCIES = ["USDT", "BTC", "ETH", "LTC", "BNB", "DOGE", "TRX"]


# ── OxaPay API wrappers ───────────────────────────────────────────────────────

async def create_invoice(
    session: aiohttp.ClientSession,
    amount_usd: float,
    currency: str,
    order_id: str,
    description: str = "Noxie donation",
) -> dict:
    """
    POST /merchants/request to create a payment invoice.
    Returns the parsed JSON or raises on error.
    """
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
    """
    POST /merchants/inquiry to check payment status.
    Returns the parsed JSON.
    """
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
    """
    Full async donation flow. Runs in background after initial ack.
    All CV2 messages are sent to user DMs.
    """
    order_id = f"noxie-{user.id}-{int(asyncio.get_event_loop().time())}"
    logger.info(f"donation flow started: user={user.id} amount={amount_usd} {currency}")

    try:
        dm = await user.create_dm()
    except discord.Forbidden:
        logger.warn(f"cannot DM user={user.id} — DMs closed")
        return

    async with aiohttp.ClientSession() as session:
        # ── Step 1: create invoice ────────────────────────────────────────────
        try:
            data = await create_invoice(session, amount_usd, currency, order_id)
            logger.success(f"invoice created: user={user.id} track={data.get('trackId')}")
        except Exception as exc:
            logger.error(f"invoice creation failed for user={user.id}", exc=exc)
            banner = face_manager.get_face_for_event("donate_fail")
            comps, files = cv2_engine.build_donate_failed_container(
                reason=str(exc), banner_path=banner
            )
            await cv2_engine.send_cv2(dm, comps, files)
            return

        track_id    = data.get("trackId", "")
        pay_address = data.get("payAddress", "N/A")
        pay_amount  = str(data.get("payAmount", "?"))

        # ── Step 2: send payment instructions in DMs ──────────────────────────
        banner_start = face_manager.get_face_for_event("donate_start")
        comps, files = cv2_engine.build_donate_start_container(
            amount_usd=amount_usd,
            currency=currency,
            crypto_address=pay_address,
            crypto_amount=pay_amount,
            payment_id=track_id,
            banner_path=banner_start,
        )
        await cv2_engine.send_cv2(dm, comps, files)

        # ── Step 3: poll for confirmation ─────────────────────────────────────
        confirmed = False
        tx_id     = track_id

        for i in range(POLL_MAX):
            await asyncio.sleep(POLL_INTERVAL)
            try:
                status_data = await check_invoice(session, track_id)
            except Exception as exc:
                logger.warn(f"poll {i+1}/{POLL_MAX} failed for user={user.id}: {exc}")
                continue

            status = status_data.get("status", "").lower()
            logger.debug(f"poll {i+1}/{POLL_MAX} user={user.id} status={status!r}")

            if status in ("paid", "confirmed", "complete"):
                confirmed = True
                break
            if status in ("expired", "cancelled", "failed"):
                logger.info(f"donation terminal status={status!r} for user={user.id}")
                break

        # ── Step 4: handle result ─────────────────────────────────────────────
        if confirmed:
            glow, coins = calc_rewards(amount_usd)
            gid = guild_id or "DM"

            economy.log_donation(bot.db, str(user.id), amount_usd, currency, tx_id)
            economy.add_currency(bot.db, str(user.id), gid, glow, coins)
            is_new_donor = economy.award_badge(bot.db, str(user.id), "donor")

            logger.success(
                f"donation confirmed: user={user.id} glow={glow} coins={coins}"
                + (" NEW_DONOR" if is_new_donor else "")
            )

            line = personality.get_line("donate_thanks")
            banner_done = face_manager.get_face_for_event("donate_done")
            comps, files = cv2_engine.build_donate_confirm_container(
                amount_usd=amount_usd,
                currency=currency,
                glow_reward=glow,
                coin_reward=coins,
                is_new_donor=is_new_donor,
                personality_line=line,
                banner_path=banner_done,
            )
            await cv2_engine.send_cv2(dm, comps, files)

        else:
            logger.warn(f"donation not confirmed for user={user.id} — sending failure msg")
            banner_fail = face_manager.get_face_for_event("donate_fail")
            comps, files = cv2_engine.build_donate_failed_container(
                reason="payment expired or was not received",
                banner_path=banner_fail,
            )
            await cv2_engine.send_cv2(dm, comps, files)


# ── Cog ──────────────────────────────────────────────────────────────────────

class DonateCog(commands.Cog, name="Donate"):
    """OxaPay donation commands."""

    def __init__(self, bot: "NoxieBot") -> None:
        self.bot = bot

    # ── /donate slash ────────────────────────────────────────────────────────

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

        # Acknowledge immediately — DM flow is async
        await interaction.response.send_message(
            "💌 Check your DMs! The donation flow is being set up.",
            ephemeral=True,
        )

        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        asyncio.create_task(
            run_donation_flow(self.bot, interaction.user, guild_id, amount, currency)
        )

    # ── prefix donate ────────────────────────────────────────────────────────

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
    logger.success("DonateCog loaded")
