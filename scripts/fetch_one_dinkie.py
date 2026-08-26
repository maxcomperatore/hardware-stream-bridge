"""Fetch a single Dinkie icon by glyph name into static/icons/dinkie/."""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "icons" / "dinkie"
URL = "https://cdn.jsdelivr.net/npm/@iconify-json/dinkie-icons@1.2.0/icons.json"


def main(name: str) -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "knob.monster"})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    icon = data["icons"][name]
    w = icon.get("width", data.get("width", 24))
    h = icon.get("height", data.get("height", 24))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">{icon["body"]}</svg>'
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(f"wrote {name}.svg")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "money-bag-frf")
