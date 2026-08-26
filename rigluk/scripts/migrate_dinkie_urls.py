"""Replace Iconify Dinkie CDN URLs with local /static/icons/dinkie/ paths."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(
    r"https://api\.iconify\.design/dinkie-icons[:/]([a-z0-9-]+)\.svg(?:\?[^\"'\s)>]*)?"
)
PRICING = {
    "usd: 'dinkie-icons:money-bag-usd'": "usd: 'money-bag-usd'",
    "gbp: 'dinkie-icons:money-bag-gbp'": "gbp: 'money-bag-gbp'",
    "eur: 'dinkie-icons:money-bag-eur'": "eur: 'money-bag-eur'",
    "cad: 'dinkie-icons:money-bag-usd'": "cad: 'money-bag-usd'",
    "aud: 'dinkie-icons:money-bag-usd'": "aud: 'money-bag-usd'",
}


def main() -> None:
    for path in (ROOT / "templates").rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        new = PATTERN.sub(r"/static/icons/dinkie/\1.svg", text)
        for old, rep in PRICING.items():
            new = new.replace(old, rep)
        new = new.replace(
            "if (img) img.src = `https://api.iconify.design/${icon}.svg`;",
            "if (img) img.src = `/static/icons/dinkie/${icon}.svg`;",
        )
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"updated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
