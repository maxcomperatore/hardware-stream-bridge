"""Download pixel-art avatars from Dicebear once into static/avatars/ (build-time only)."""
from __future__ import annotations

import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "avatars"
UA = "knob.monster-asset-mirror/1.0"
API = "https://api.dicebear.com/10.x/pixel-art/svg"

# Distinct seeds → numbered files for self-hosted random pool.
AVATAR_SEEDS = (
    "patchouli-pete",
    "juno-widow-86",
    "midi-goblin-x",
    "dx7-dust-bunny",
    "moog-moth",
)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, seed in enumerate(AVATAR_SEEDS, start=1):
        url = f"{API}?seed={urllib.parse.quote(seed)}"
        dest = OUT / f"avatar-{i:02d}.svg"
        data = fetch_bytes(url)
        dest.write_bytes(data)
        print(f"wrote {dest.name} ({len(data)} bytes) seed={seed}")
    print(f"done — {len(AVATAR_SEEDS)} avatars in {OUT}")


if __name__ == "__main__":
    main()
