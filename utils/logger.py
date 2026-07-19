"""
utils/logger.py — ANSI-colored console logger for Noxie.

Color palette matches Noxie's aesthetic:
  DEBUG   → cyan       (🔵)
  INFO    → purple     (🟣)
  SUCCESS → magenta    (💜)
  WARNING → yellow     (🟡)
  ERROR   → red        (🔴)

Usage:
    from utils.logger import log
    log.info("bot is online")
    log.success("cog loaded")
    log.warning("cooldown hit")
    log.error("something broke", exc=e)
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime


# ── ANSI codes ────────────────────────────────────────────────────────────────

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Noxie palette
CYAN    = "\033[36m"
PURPLE  = "\033[35m"      # magenta-ish — used for INFO
MAGENTA = "\033[95m"      # bright magenta — used for SUCCESS
YELLOW  = "\033[33m"
RED     = "\033[31m"
BRIGHT_RED = "\033[91m"
WHITE   = "\033[97m"
GREY    = "\033[90m"


# ── Level config ──────────────────────────────────────────────────────────────

_LEVELS = {
    "DEBUG":   (CYAN,       "DBG"),
    "INFO":    (PURPLE,     "INF"),
    "SUCCESS": (MAGENTA,    "OK "),
    "WARNING": (YELLOW,     "WRN"),
    "ERROR":   (BRIGHT_RED, "ERR"),
}


# ── Logger ────────────────────────────────────────────────────────────────────

class NoxieLogger:
    """
    Minimal structured logger with ANSI color output.
    All output goes to stderr so it doesn't interfere with piped stdout.
    """

    def _write(self, level: str, message: str, exc: BaseException | None = None) -> None:
        color, tag = _LEVELS.get(level, (WHITE, level[:3].upper()))
        now = datetime.now().strftime("%H:%M:%S")

        timestamp = f"{GREY}{now}{RESET}"
        bracket   = f"{color}{BOLD}[{tag}]{RESET}"
        text      = f"{WHITE}{message}{RESET}"

        print(f"{timestamp} {bracket} {text}", file=sys.stderr)

        if exc is not None:
            tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
            for line in "".join(tb).rstrip().splitlines():
                print(f"         {RED}{line}{RESET}", file=sys.stderr)

    def debug(self, message: str, exc: BaseException | None = None) -> None:
        self._write("DEBUG", message, exc)

    def info(self, message: str, exc: BaseException | None = None) -> None:
        self._write("INFO", message, exc)

    def success(self, message: str, exc: BaseException | None = None) -> None:
        self._write("SUCCESS", message, exc)

    def warning(self, message: str, exc: BaseException | None = None) -> None:
        self._write("WARNING", message, exc)

    def error(self, message: str, exc: BaseException | None = None) -> None:
        self._write("ERROR", message, exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

log = NoxieLogger()
