"""Local static icon path helpers (no CDN)."""

from __future__ import annotations

from pathlib import Path

_DINKIE_DIR = Path(__file__).resolve().parent / "static" / "icons" / "dinkie"
_STRIPE_DIR = Path(__file__).resolve().parent / "static" / "covers" / "stripes"

DINKIE_COVER_ICONS: tuple[str, ...] = tuple(
    sorted(p.stem for p in _DINKIE_DIR.glob("*.svg"))
)
STRIPE_COVER_ICONS: tuple[str, ...] = tuple(
    sorted(p.name for p in _STRIPE_DIR.glob("stripe-*.svg"))
)


def _stable_hash(key: str | int) -> int:
    h = 5381
    for ch in str(key):
        h = ((h << 5) + h) + ord(ch)
    return abs(h)


def dinkie_icon(name: str) -> str:
    return f"/static/icons/dinkie/{name}.svg"


def dinkie_cover_icon(key: str | int) -> str:
    """Pick a stable random Dinkie icon for vault covers from *key*."""
    if not DINKIE_COVER_ICONS:
        return dinkie_icon("multiple-musical-notes")
    return dinkie_icon(DINKIE_COVER_ICONS[_stable_hash(key) % len(DINKIE_COVER_ICONS)])


def stripe_cover_icon(key: str | int) -> str:
    """Pick a stable random self-hosted Stripes cover from *key*."""
    if not STRIPE_COVER_ICONS:
        return "/static/covers/stripes/stripe-01.svg"
    return f"/static/covers/stripes/{STRIPE_COVER_ICONS[_stable_hash(key) % len(STRIPE_COVER_ICONS)]}"


def dinkie_cover_icon_names() -> list[str]:
    return list(DINKIE_COVER_ICONS)


def stripe_cover_icon_names() -> list[str]:
    return list(STRIPE_COVER_ICONS)


def flag_icon(code: str) -> str:
    return f"/static/icons/flags/{code.strip().lower()}.svg"


def brand_icon(name: str) -> str:
    return f"/static/icons/brands/{name}.svg"
