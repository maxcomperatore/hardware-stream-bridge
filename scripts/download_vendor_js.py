"""Vendor htmx + rough-notation into static/js/ (build-time CDN fetch only)."""
from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS_OUT = ROOT / "static" / "js"
UA = "knob.monster-asset-mirror/1.0"

VENDOR_FILES = (
    ("https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js", "htmx.min.js"),
    ("https://cdn.jsdelivr.net/npm/rough-notation@0.5.1/+esm", "rough-notation.js"),
)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def main() -> None:
    JS_OUT.mkdir(parents=True, exist_ok=True)
    for url, name in VENDOR_FILES:
        dest = JS_OUT / name
        data = fetch_bytes(url)
        dest.write_bytes(data)
        print(f"wrote {dest} ({len(data)} bytes)")
    print("done")


if __name__ == "__main__":
    main()
