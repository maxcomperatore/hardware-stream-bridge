"""Download flags + brand icons into static/icons/ (build-time; no runtime CDN)."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAGS_OUT = ROOT / "static" / "icons" / "flags"
BRANDS_OUT = ROOT / "static" / "icons" / "brands"
UA = "knob.monster-asset-mirror/1.0"

# ISO 3166-1 alpha-2 and regional codes in @iconify-json/flagpack (256 icons).
BRAND_ICONS: list[tuple[str, str, str, str | None]] = [
    ("visa.svg", "logos", "visa", None),
    ("mastercard.svg", "logos", "mastercard", None),
    ("amex.svg", "logos", "amex", None),
    ("google-pay.svg", "logos", "google-pay", None),
    ("usdc.svg", "cryptocurrency-color", "usdc", None),
    ("applepay.svg", "simple-icons", "applepay", "#ffffff"),
    ("cashapp.svg", "simple-icons", "cashapp", "#00D632"),
    ("pix.svg", "simple-icons", "pix", "#32B3A6"),
    ("naver.svg", "simple-icons", "naver", "#03C75A"),
    ("openai.svg", "simple-icons", "openai", "#ffffff"),
    ("anthropic.svg", "simple-icons", "anthropic", "#ffffff"),
    ("perplexity.svg", "simple-icons", "perplexity", "#ffffff"),
    ("googlegemini.svg", "simple-icons", "googlegemini", "#ffffff"),
]


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def icon_to_svg(icon_data: dict, defaults: dict, fill: str | None = None) -> str:
    width = icon_data.get("width", defaults.get("width", 24))
    height = icon_data.get("height", defaults.get("height", 24))
    body = icon_data["body"]
    if fill:
        body = re.sub(r'fill="[^"]*"', f'fill="{fill}"', body)
        if 'fill="' not in body:
            body = body.replace("<path ", f'<path fill="{fill}" ', 1)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{body}</svg>'
    )


def load_icon_set(package: str) -> dict:
    url = f"https://cdn.jsdelivr.net/npm/@iconify-json/{package}@1/icons.json"
    return fetch_json(url)


def export_brands() -> None:
    BRANDS_OUT.mkdir(parents=True, exist_ok=True)
    cache: dict[str, dict] = {}
    for filename, package, name, fill in BRAND_ICONS:
        if package not in cache:
            cache[package] = load_icon_set(package)
        data = cache[package]
        icon = data["icons"][name]
        defaults = {"width": data.get("width", 24), "height": data.get("height", 24)}
        (BRANDS_OUT / filename).write_text(icon_to_svg(icon, defaults, fill), encoding="utf-8")
        print(f"brand  {filename}")


def export_flags() -> None:
    FLAGS_OUT.mkdir(parents=True, exist_ok=True)
    data = load_icon_set("flagpack")
    icons = data["icons"]
    defaults = {"width": data.get("width", 24), "height": data.get("height", 24)}
    for code in sorted(icons):
        (FLAGS_OUT / f"{code}.svg").write_text(
            icon_to_svg(icons[code], defaults), encoding="utf-8"
        )
    print(f"flags  {len(icons)} written")


def main() -> None:
    export_flags()
    export_brands()
    flag_count = len(list(FLAGS_OUT.glob("*.svg")))
    brand_count = len(list(BRANDS_OUT.glob("*.svg")))
    print(f"\nDone: {flag_count} flags, {brand_count} brands")


if __name__ == "__main__":
    main()
