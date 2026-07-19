"""
logger.py — Colored console logger for Noxie.

Uses ANSI escape codes only (no external dependencies).
Design matches the bot's dark/moody aesthetic: purples, cool whites, dim greys.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime


# ── ANSI palette ──────────────────────────────────────────────────────────────

class _C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Noxie palette
    PURPLE  = "\033[38;5;141m"   # soft lavender — startup / info
    MAGENTA = "\033[38;5;201m"   # vivid pink-purple — success
    CYAN    = "\033[38;5;117m"   # cool blue — debug
    YELLOW  = "\033[38;5;221m"   # warm amber — warning
    RED     = "\033[38;5;204m"   # soft red — error
    WHITE   = "\033[38;5;252m"   # near-white — message body
    GREY    = "\033[38;5;240m"   # dark grey — timestamps / brackets
    DARK    = "\033[38;5;235m"   # very dark — dividers


# ── Internals ─────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _fmt(level_color: str, level_label: str, message: str) -> str:
    ts      = f"{_C.GREY}{_ts()}{_C.RESET}"
    bracket = f"{_C.GREY}[{_C.RESET}"
    level   = f"{level_color}{_C.BOLD}{level_label:<7}{_C.RESET}"
    rb      = f"{_C.GREY}]{_C.RESET}"
    body    = f"{_C.WHITE}{message}{_C.RESET}"
    return f"{ts} {bracket}{level}{rb} {body}"


# ── Public API ────────────────────────────────────────────────────────────────

def info(message: str) -> None:
    """General information — purple."""
    print(_fmt(_C.PURPLE, "INFO", message), flush=True)


def success(message: str) -> None:
    """Positive outcome — magenta/pink."""
    print(_fmt(_C.MAGENTA, "OK", message), flush=True)


def warn(message: str) -> None:
    """Soft warning — amber."""
    print(_fmt(_C.YELLOW, "WARN", message), flush=True)


def error(message: str, exc: BaseException | None = None) -> None:
    """Error — red, with optional traceback."""
    print(_fmt(_C.RED, "ERROR", message), flush=True)
    if exc is not None:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        for line in tb.rstrip().splitlines():
            print(f"  {_C.DIM}{_C.RED}{line}{_C.RESET}", flush=True)


def debug(message: str) -> None:
    """Verbose debug — dim cyan."""
    print(_fmt(_C.CYAN, "DEBUG", message), flush=True)


def divider(label: str = "") -> None:
    """Print a section divider that matches the bot's aesthetic."""
    line = "─" * 48
    if label:
        padded = f" {label} "
        half   = (48 - len(padded)) // 2
        line   = "─" * half + padded + "─" * (48 - half - len(padded))
    print(f"{_C.DARK}{line}{_C.RESET}", flush=True)


def startup_banner() -> None:
    """Print Noxie's startup banner."""
    divider()
    print(f"  {_C.PURPLE}{_C.BOLD}🌑  N O X I E{_C.RESET}  {_C.GREY}vibe engine · discord companion{_C.RESET}")
    divider()
