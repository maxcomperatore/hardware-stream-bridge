"""One-off: fetch Dinkie icons used in templates into static/icons/dinkie/."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "icons" / "dinkie"
ICONIFY_JSON = (
    "https://cdn.jsdelivr.net/npm/@iconify-json/dinkie-icons@1.2.0/icons.json"
)
USER_AGENT = "knob.monster-icon-mirror/1.0 (+https://knob.monster)"

# Template names that differ from the Iconify JSON glyph names.
ALIASES = {
    "backhand-index-pointing-down": "white-down-backhand-index",
    "backhand-index-pointing-right": "white-right-backhand-index",
}


def discover_from_templates() -> set[str]:
    found: set[str] = set()
    pattern = re.compile(r"dinkie-icons[:/]([a-z0-9-]+)")
    for path in (ROOT / "templates").rglob("*.html"):
        found.update(pattern.findall(path.read_text(encoding="utf-8")))
    return found


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def icon_to_svg(icon_data: dict, defaults: dict) -> str:
    width = icon_data.get("width", defaults.get("width", 24))
    height = icon_data.get("height", defaults.get("height", 24))
    body = icon_data["body"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{body}</svg>'
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    names = sorted(discover_from_templates())
    print(f"Fetching icon set ({len(names)} icons needed)...")
    data = fetch_json(ICONIFY_JSON)
    icons = data.get("icons", {})
    defaults = {
        "width": data.get("width", 24),
        "height": data.get("height", 24),
    }
    ok, failed = 0, []
    for name in names:
        dest = OUT / f"{name}.svg"
        glyph = ALIASES.get(name, name)
        icon_data = icons.get(glyph)
        if not icon_data:
            failed.append((name, f"missing ({glyph})"))
            print(f"FAIL {name}: not in icons.json ({glyph})")
            continue
        dest.write_text(icon_to_svg(icon_data, defaults), encoding="utf-8")
        ok += 1
        print(f"OK  {name}")
    print(f"\nWrote {ok}/{len(names)} icons to {OUT}")
    if failed:
        raise SystemExit(f"Failed: {failed}")


if __name__ == "__main__":
    main()
