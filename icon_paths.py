"""Local static icon path helpers (no CDN)."""

from __future__ import annotations

from pathlib import Path

_DINKIE_DIR = Path(__file__).resolve().parent / "static" / "icons" / "dinkie"
DINKIE_COVER_ICONS: tuple[str, ...] = tuple(
    sorted(p.stem for p in _DINKIE_DIR.glob("*.svg"))
)


def dinkie_icon(name: str) -> str:
    return f"/static/icons/dinkie/{name}.svg"


def dinkie_cover_icon(key: str | int) -> str:
    """Pick a stable random Dinkie icon for vault covers from *key*."""
    if not DINKIE_COVER_ICONS:
        return dinkie_icon("multiple-musical-notes")
    h = 5381
    for ch in str(key):
        h = ((h << 5) + h) + ord(ch)
    return dinkie_icon(DINKIE_COVER_ICONS[abs(h) % len(DINKIE_COVER_ICONS)])


def dinkie_cover_icon_names() -> list[str]:
    return list(DINKIE_COVER_ICONS)


def flag_icon(code: str) -> str:
    return f"/static/icons/flags/{code.strip().lower()}.svg"


def brand_icon(name: str) -> str:
    return f"/static/icons/brands/{name}.svg"
