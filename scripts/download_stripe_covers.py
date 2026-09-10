"""Download DiceBear Stripes SVGs into static/covers/stripes/ (build-time fetch only)."""
from __future__ import annotations

import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "covers" / "stripes"
UA = "knob.monster-asset-mirror/1.0"
API = "https://api.dicebear.com/10.x/stripes/svg"

# Stable seeds → varied stripe angles and palette pairs.
STRIPE_SEEDS = (
    "juno-106",
    "dx7-cartridge",
    "moog-ladder",
    "prophet-five",
    "oberheim-obx",
    "waldorf-microwave",
    "emu-proteus",
    "korg-m1-piano",
    "roland-d50",
    "yamaha-fs1r",
    "casio-cz101",
    "alesis-d4",
    "ensoniq-asr10",
    "sequential-six",
    "arp-2600",
    "buchla-200",
    "synthi-aks",
    "linn-lm1",
    "oberheim-dmx",
    "crumar-bit",
    "elka-synthex",
    "hartmann-neuron",
    "waldorf-q",
    "elektron-digitakt",
)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, seed in enumerate(STRIPE_SEEDS, start=1):
        url = f"{API}?seed={urllib.parse.quote(seed)}"
        dest = OUT / f"stripe-{i:02d}.svg"
        data = fetch_bytes(url)
        dest.write_bytes(data)
        print(f"wrote {dest.name} ({len(data)} bytes) seed={seed}")
    print(f"done — {len(STRIPE_SEEDS)} stripe covers in {OUT}")


if __name__ == "__main__":
    main()
