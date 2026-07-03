"""Local static icon path helpers (no CDN)."""

from __future__ import annotations


def dinkie_icon(name: str) -> str:
    return f"/static/icons/dinkie/{name}.svg"


def flag_icon(code: str) -> str:
    return f"/static/icons/flags/{code.strip().lower()}.svg"


def brand_icon(name: str) -> str:
    return f"/static/icons/brands/{name}.svg"
