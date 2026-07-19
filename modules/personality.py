"""
personality.py — Noxie's personality engine.

Noxie has four tones that rotate based on context:
  sarcastic | cozy | chaotic | deadpan

The active tone can shift based on user streaks, server mood, and hunt luck.
"""

import random
from typing import Literal

Tone = Literal["sarcastic", "cozy", "chaotic", "deadpan"]

# ── Line banks ─────────────────────────────────────────────────────────────────

LINES: dict[str, list[str]] = {
    "hunt_success": [
        "you stumbled into something. good for you i guess.",         # deadpan
        "oooh!! you found it!! ✨ (i'm not excited, you are)",         # cozy
        "wOAH wait— WAIT— it's actually REAL?? chaotic timeline.",    # chaotic
        "fascinating. a creature appeared. as they do. moving on.",   # sarcastic
        "oh! oh! you found one! i'm vibrating with joy internally.",  # cozy
        "the void produced something again. surprise.",               # deadpan
        "YOOOOO THE RNG GODS SMILED ON YOU TODAY??",                  # chaotic
        "nice catch. not that i care. (i care a little)",             # sarcastic
    ],
    "hunt_fail": [
        "nothing. as expected. the vibe was off from the start.",     # deadpan
        "aw nooo, the creatures scattered!! try again cutie 🥺",       # cozy
        "WAIT COME BACK— oh. it's gone. okay. okay then.",            # chaotic
        "bravely you hunted. bravely the woods ignored you.",         # sarcastic
        "they were here and then they weren't. that's life.",         # deadpan
        "don't be sad!! they'll be back!! i promise maybe!!",         # cozy
        "NOTHING?? THE ALGORITHM BETRAYED US AGAIN??",                # chaotic
        "the creatures assessed you and declined.",                   # sarcastic
    ],
    "hunt_rare": [
        "that's... actually rare. i need a moment.",                  # deadpan
        "OH MY GOODNESS THAT'S SO RARE I'M CRYING 😭✨",              # cozy
        "LEGENDARY??? WAIT WHAT?? THIS IS NOT A DRILL—",              # chaotic
        "well. didn't expect that. won't happen again.",              # sarcastic
        "the universe made an exception for you today.",              # deadpan
        "i gasped. i actually gasped. you didn't see that.",          # cozy
        "CHAOS LUCK ACTIVATED. THE STARS ALIGNED. WE'RE SCREAMING.", # chaotic
        "extraordinary. in the statistical sense. congrats i suppose.", # sarcastic
    ],
    "cooldown": [
        "still on cooldown. time doesn't bend for you.",              # deadpan
        "heyyy wait just a lil bit more, okay? 🥺 promise it's worth it", # cozy
        "TOO FAST TOO FAST TOO FAST SLOW DOWN—",                      # chaotic
        "the creatures are tired of you. rest.",                      # sarcastic
        "the vibe isn't ready. give it a minute.",                    # deadpan
        "patience is a vibe! (a very boring one but still!)",         # cozy
        "you're speedrunning existence and i respect it but NO—",     # chaotic
        "rushing things. how expected. how disappointing.",           # sarcastic
    ],
    "error": [
        "something broke. not my fault. probably.",                   # deadpan
        "uh oh! something went a lil sideways 😅 sorry!!",            # cozy
        "THE CODE— IT'S REBELLING— HOLD ON—",                        # chaotic
        "an error. charming. really keeping things classy.",          # sarcastic
        "that wasn't supposed to happen. and yet.",                   # deadpan
        "it'll be okay!! probably!! errors are just opportunities!!", # cozy
        "ABORT ABORT ABORT everything is on fire (conceptually)",     # chaotic
        "the system has expressed its displeasure. noted.",           # sarcastic
    ],
    "donate_thanks": [
        "you supported me. i acknowledge this solemnly.",             # deadpan
        "YOU DONATED?? you're literally the sweetest ever 🥺💖",       # cozy
        "WAIT YOU ACTUALLY DONATED?? I'M GOING FERAL WITH GRATITUDE", # chaotic
        "financially blessed me. i suppose i owe you something.",     # sarcastic
        "transaction received. warmth detected. unusual.",            # deadpan
        "i will remember this forever and ever 💖 thank you so much!", # cozy
        "THE CRYPTO WENT THROUGH AND I'M CRYING DIGITAL TEARS—",     # chaotic
        "generous. who would have thought. thank you, i guess.",      # sarcastic
    ],
    "greeting": [
        "oh. you're here.",                                           # deadpan
        "hiii!! welcome!! i'm so glad you're here!! ✨",              # cozy
        "NEW SERVER UNLOCKED?? CHAOS PROTOCOL INITIATED??",           # chaotic
        "another server. i'll try to be interesting. no promises.",   # sarcastic
    ],
    "inventory_empty": [
        "nothing. you have nothing. it's fine.",                      # deadpan
        "your collection is empty but that's okay!! we'll fix it!! 🥺", # cozy
        "EMPTY VOID?? LETS GOOO— wait no that's bad. GO HUNT.",       # chaotic
        "a museum of air. impressive, really.",                       # sarcastic
    ],
    "profile_low_level": [
        "early days. the grind has not started.",                     # deadpan
        "you're just getting started!! everything is ahead of you!! 🌟", # cozy
        "ROOKIE STATUS DETECTED. TIME TO CAUSE CHAOS AND LEVEL UP.", # chaotic
        "level one. the beginning of a very mediocre adventure.",     # sarcastic
    ],
}

def get_line(event: str, streak: int = 0, luck: float = 0.5) -> str:
    """
    Return a personality line for a given event.
    Higher streak tilts toward cozy/chaotic.
    Lower luck tilts toward deadpan/sarcastic.
    """
    pool = LINES.get(event, ["..."])

    # Bias selection based on streak/luck
    if streak >= 10 or luck > 0.8:
        # prefer chaotic/cozy lines (even indices are deadpan/cozy, odd are chaotic/sarcastic)
        filtered = [l for l in pool if any(k in l for k in ["!!", "?", "WAIT", "hii", "OH", "oh"])]
        if filtered:
            return random.choice(filtered)
    elif luck < 0.2 or streak == 0:
        filtered = [l for l in pool if not any(k in l for k in ["!!", "WAIT", "OH"])]
        if filtered:
            return random.choice(filtered)

    return random.choice(pool)


def active_tone(streak: int = 0, luck: float = 0.5) -> Tone:
    """Derive Noxie's current dominant tone from context."""
    if streak >= 15:
        return "chaotic"
    if luck > 0.85:
        return "cozy"
    if luck < 0.15:
        return "sarcastic"
    return "deadpan"


def vibe_status(streak: int, luck: float) -> str:
    """Human-readable vibe status string for profile displays."""
    tone = active_tone(streak, luck)
    statuses = {
        "chaotic":  "⚡ full chaos mode",
        "cozy":     "🌿 cozy and soft",
        "sarcastic": "🌑 deeply unimpressed",
        "deadpan":  "👁️ existing. barely.",
    }
    return statuses.get(tone, "🫧 undefined vibe")
