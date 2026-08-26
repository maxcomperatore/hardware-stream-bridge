"""Replace CDN font/icon URLs with self-hosted /static/ paths."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = '{% include "partials/local_fonts.html" %}'

REPLACEMENTS = [
    (r"https://api\.iconify\.design/flagpack/([a-z]{2})\.svg", r"/static/icons/flags/\1.svg"),
    (r"https://api\.iconify\.design/flagpack/\$\{code\}\.svg", "/static/icons/flags/${code}.svg"),
    (r"https://api\.iconify\.design/logos:([a-z0-9-]+)\.svg(?:\?[^\"'\s)>]*)?", r"/static/icons/brands/\1.svg"),
    (r"https://api\.iconify\.design/cryptocurrency-color:usdc\.svg", "/static/icons/brands/usdc.svg"),
    (r"https://api\.iconify\.design/simple-icons:openai\.svg\?color=white", "/static/icons/brands/openai.svg"),
    (r"https://api\.iconify\.design/simple-icons:anthropic\.svg\?color=white", "/static/icons/brands/anthropic.svg"),
    (r"https://api\.iconify\.design/simple-icons:perplexity\.svg\?color=white", "/static/icons/brands/perplexity.svg"),
    (r"https://api\.iconify\.design/simple-icons:googlegemini\.svg\?color=white", "/static/icons/brands/googlegemini.svg"),
    (r"https://cdn\.simpleicons\.org/applepay/ffffff", "/static/icons/brands/applepay.svg"),
    (r"https://cdn\.simpleicons\.org/cashapp/00D632", "/static/icons/brands/cashapp.svg"),
    (r"https://cdn\.simpleicons\.org/pix/32B3A6", "/static/icons/brands/pix.svg"),
    (r"https://cdn\.simpleicons\.org/naver/03C75A", "/static/icons/brands/naver.svg"),
]


def strip_cdn_font_links(text: str) -> str:
    patterns = [
        r"\s*<link[^>]*preconnect[^>]*(?:fonts\.googleapis\.com|fonts\.gstatic\.com|api\.fontshare\.com|api\.iconify\.design|cdn\.simpleicons\.org)[^>]*>\s*",
        r"\s*<!--[^\n]*(?:Geist|Pixel|Dot-Matrix|Retro|Vercel)[^\n]*-->\s*",
        r"<link[\s\S]*?fontshare\.com[\s\S]*?>\s*",
        r"<noscript>\s*<link[\s\S]*?fontshare\.com[\s\S]*?</noscript>\s*",
        r"<link[\s\S]*?fonts\.googleapis\.com/css2\?[\s\S]*?(?:Silkscreen|VT323|Nabla|Kablammo)[\s\S]*?>\s*",
        r"<noscript>\s*<link[\s\S]*?fonts\.googleapis\.com/css2\?[\s\S]*?(?:Silkscreen|VT323|Nabla)[\s\S]*?</noscript>\s*",
        r'\s*<link href="https://fonts\.googleapis\.com/css2\?family=Kablammo[^"]*" rel="stylesheet">\s*',
    ]
    out = text
    for pattern in patterns:
        out = re.sub(pattern, "", out, flags=re.I)
    return out


def insert_font_include(text: str) -> str:
    if INCLUDE in text or "knob-monster.css" in text:
        return text
    for marker in ('<link rel="shortcut icon"', '<link id="favicon"', "<title>"):
        idx = text.find(marker)
        if idx != -1:
            return text[:idx] + INCLUDE + "\n    " + text[idx:]
    head_end = text.find("</head>")
    if head_end == -1:
        return text
    return text[:head_end] + "    " + INCLUDE + "\n" + text[head_end:]


def apply_icon_replacements(text: str) -> str:
    out = text
    for pattern, repl in REPLACEMENTS:
        out = re.sub(pattern, repl, out, flags=re.I)
    return out


def migrate_file(text: str) -> str:
    needs_fonts = "fontshare.com" in text or re.search(
        r"fonts\.googleapis\.com/css2\?[^\"']*(Silkscreen|VT323|Nabla|Kablammo)", text
    )
    out = apply_icon_replacements(text)
    if needs_fonts:
        out = insert_font_include(strip_cdn_font_links(out))
    else:
        out = strip_cdn_font_links(out) if "preconnect" in out and "iconify" in out else out
    return apply_icon_replacements(out)


def main() -> None:
    targets = list((ROOT / "templates").rglob("*.html"))
    targets.append(ROOT / "pricing_geo_titles.py")
  # main.py earth day inline html
    targets.append(ROOT / "main.py")
    for path in targets:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        new = migrate_file(text)
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"updated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
