# 🌑 Noxie — Vibe Engine Discord Bot

Noxie is a character-driven, mood-based Discord companion bot built on **discord.py 2.3+** with full **Discord Components V2 (CV2)** support. Hunt vibe creatures, build your collection, and let Noxie react to everything with deadpan sarcasm, cozy warmth, and pure chaos.

---

## Features

| Feature | Description |
|---|---|
| 🎴 CV2 Containers | Rich interactive message layouts with mood banners |
| 🦊 Vibe Creatures | 36 collectible creatures across 6 rarities |
| ⚡ Economy | Glow Shards + Vibe Coins earned from hunting |
| 💎 Donations | OxaPay crypto donation flow in DMs with CV2 |
| 👁️ Personality Engine | Sarcastic · Cozy · Chaotic · Deadpan responses |
| 🔑 Multi-Prefix | Per-guild custom prefixes + permanent `noxie ` global prefix |
| ⚡ Slash Commands | Full slash command support alongside prefix commands |

---

## Project Structure

```
noxie/
├── main.py                  ← Bot entry point
├── config.json              ← Configuration (token, keys, economy settings)
├── requirements.txt         ← Python dependencies
├── README.md
│
├── mood_banners/            ← All uploaded face/mood banner images
│   ├── evil_*.jpeg          → evil mood
│   ├── dizzy_*.jpeg         → dizzy / error mood
│   ├── OuO_💖_*.jpeg        → love / donation done mood
│   └── ... (14 total)
│
├── vibe_creatures/
│   └── data.json            ← 36 creatures with rarities, moods, vibes
│
├── db/
│   └── noxie.db             ← SQLite database (auto-created on first run)
│
└── modules/
    ├── __init__.py
    ├── utils.py             ← Shared helpers, config loader, banner path resolver
    ├── cv2_engine.py        ← All CV2 container builders + send helper
    ├── face_manager.py      ← Event → mood banner file path mapping
    ├── personality.py       ← Tone engine + line banks (sarcastic/cozy/chaotic/deadpan)
    ├── economy.py           ← SQLite economy: shards, coins, inventory, badges
    ├── prefixes.py          ← Multi-prefix system + PrefixCog
    ├── hunt_system.py       ← Hunt + inventory + vibe commands
    ├── donate.py            ← OxaPay donation flow
    └── profile.py           ← /profile mood pulse
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the bot

Edit `config.json`:

```json
{
  "bot_token": "YOUR_DISCORD_BOT_TOKEN",
  "global_prefix": "noxie ",
  "oxapay_api_key": "YOUR_OXAPAY_API_KEY",
  "oxapay_merchant": "YOUR_OXAPAY_MERCHANT_ID"
}
```

Or set the environment variable instead of editing the file:
```bash
export NOXIE_TOKEN="your_bot_token_here"
```

### 3. Discord Developer Portal settings

In your bot application settings:
- **Privileged Gateway Intents:** enable `MESSAGE CONTENT INTENT` and `SERVER MEMBERS INTENT`
- **Bot Permissions:** `Send Messages`, `Embed Links`, `Attach Files`, `Use Slash Commands`, `Read Message History`

### 4. OxaPay setup

1. Create a merchant account at [oxapay.com](https://oxapay.com)
2. Get your **Merchant Key** from the dashboard
3. Add it to `config.json` → `oxapay_merchant_key`

### 5. Run

```bash
cd noxie
python main.py
```

On first run, Noxie will:
- Create `db/noxie.db` automatically
- Initialize all database tables
- Sync slash commands globally (may take up to 1 hour to propagate)

---

## Termux (Android) Setup

```bash
pkg update && pkg upgrade
pkg install python
pip install discord.py aiohttp
cd /path/to/noxie
python main.py
```

To keep it running after closing Termux:
```bash
nohup python main.py &
```

---

## Commands

### Hunt & Collect

| Command | Description |
|---|---|
| `/hunt` · `noxie hunt` | Hunt a random vibe creature |
| `/inventory` · `noxie inventory [page]` | View your creature collection |
| `/vibe` · `noxie vibe` | Check your current vibe energy and streak |

### Profile

| Command | Description |
|---|---|
| `/profile [@user]` · `noxie profile [@user]` | View mood pulse (stats, badges, vibe status) |

### Donation

| Command | Description |
|---|---|
| `/donate <amount> [currency]` | Donate via crypto (DM-based flow) |
| `noxie donate <amount> [currency]` | Same as above, prefix version |

Supported currencies: `USDT`, `BTC`, `ETH`, `LTC`, `BNB`, `DOGE`, `TRX`

### Prefix Management *(requires Manage Server)*

| Command | Description |
|---|---|
| `noxie prefix` · `/prefix` | List all active prefixes |
| `noxie prefix add <prefix>` | Add a custom prefix for this server |
| `noxie prefix remove <prefix>` | Remove a custom prefix |

> **Note:** The global prefix `noxie ` is permanent and cannot be removed or overridden.

### Help

```
noxie help
```

---

## CV2 Container Reference

Noxie uses Discord Components V2 for all rich displays. Mood banners are always embedded at the **bottom** of the following container types:

| Container | Banner Mood |
|---|---|
| Hunt result | Based on rarity (neutral → love → evil for mythic) |
| Vibe creature display | Creature's native mood |
| Mood pulse / profile | Based on current personality tone |
| Donation start | `excited` face |
| Donation confirmed | `love` face |
| Donation failed | `dizzy` face |

---

## Vibe Creatures

36 unique creatures across 6 rarities:

| Rarity | Weight | Examples |
|---|---|---|
| 🔲 Common | 45% | Gloomfox, Sparkitty, Mossling, Blobette |
| 🟩 Uncommon | 28% | Driftling, Neonmoth, Plaguerat, Echogolem |
| 🔷 Rare | 15% | Tidewyrm, Lunarfawn, Emberstag, Hazebird |
| 🟣 Epic | 8% | Prismhawk, Nullbear, Ashphoenix, Bloomwitch |
| ⭐ Legendary | 3% | Cosmoscat, Chronowolf, Glitchsprite |
| 🌌 Mythic | 1% | Voidmatriarch, Solarlion, Nightweaver |

Creature moods: `melancholy` · `chaotic` · `cozy` · `neutral` · `sarcastic`

---

## Economy

### Currencies

- **Glow Shards** ✨ — primary currency, earned from every hunt
- **Vibe Coins** 🪙 — rarer currency, earned from hunts and donations

### Earning rates per hunt

| Rarity | Glow Shards | Vibe Coins |
|---|---|---|
| Common | 5–25 | 1–5 |
| Uncommon | 10–50 | 2–8 |
| Rare | 20–100 | 4–15 |
| Epic | 40–200 | 8–30 |
| Legendary | 100–500 | 20–75 |
| Mythic | 250–1250 | 50–200 |

### Donation rewards

- **500 Glow Shards** per $1 USD donated
- **50 Vibe Coins** per $1 USD donated
- **Donor Badge** awarded permanently on first donation

### Badges

| Badge | Requirement |
|---|---|
| 💎 Donor | First successful donation |
| 🏹 Hunter I | 10 total hunts |
| 🏹 Hunter II | 50 total hunts |
| 🏹 Hunter III | 100 total hunts |
| 🌟 Legendary Finder | Catch a legendary creature |
| 🌌 Mythic Witness | Catch a mythic creature |
| 🔥 Hot Streak | 25-hunt streak |

---

## Personality Engine

Noxie's responses shift based on context:

| Tone | Triggers |
|---|---|
| **Deadpan** | Default, low streak |
| **Cozy** | High luck rolls, warm events |
| **Chaotic** | Long streaks (15+), rare finds |
| **Sarcastic** | Low luck, empty inventory |

---

## Mood Banners

The 14 uploaded face assets are mapped to moods:

| File | Mood Key | Used For |
|---|---|---|
| `e204dc35...` | `neutral` | Default / common hunts |
| `d1e57551...` | `happy` | Pull success |
| `evil_...` | `evil` | Mythic hunts, chaos reactions |
| `dizzy_...` | `dizzy` | Errors, donation failure |
| `c03ad0db...` | `deadpan` | Sarcastic personality |
| `0e44b531...` | `cozy` | Uncommon hunts, cozy tone |
| `80dcaeb5...` | `chaotic` | Chaotic personality |
| `ee04e2ef...` | `sarcastic` | Sarcastic responses |
| `Carinha_fds...` | `carinha` | Soft reactions |
| `b8cfc91a...` | `melancholy` | Hunt fails, sad events |
| `5a1d22b1...` | `sleepy` | Cooldowns |
| `64e168a8...` | `excited` | Epic hunts, donate start |
| `OuO_💖...` | `love` | Legendary hunts, donate confirm |
| `59164958...` | `rare` | Rare hunts |

---

## Database Tables

All data stored in `db/noxie.db` (SQLite):

- `economy` — user balances, hunt counts, streaks
- `inventory` — caught creatures per user/guild
- `badges` — awarded badges per user
- `donations` — logged donation transactions
- `guild_prefixes` — custom prefixes per guild

---

## License

MIT — do whatever you want with it.
