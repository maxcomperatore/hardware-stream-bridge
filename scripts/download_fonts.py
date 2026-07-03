"""Download knob.monster web fonts into static/fonts/ and emit knob-monster.css."""
from __future__ import annotations

import hashlib
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "fonts"
CSS_OUT = OUT / "knob-monster.css"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

GEIST_BASE = "https://cdn.jsdelivr.net/npm/geist@1.4.2/dist/fonts"
GEIST_SANS = [
    ("Geist", 400, "normal", f"{GEIST_BASE}/geist-sans/Geist-Regular.woff2"),
    ("Geist", 500, "normal", f"{GEIST_BASE}/geist-sans/Geist-Medium.woff2"),
    ("Geist", 600, "normal", f"{GEIST_BASE}/geist-sans/Geist-SemiBold.woff2"),
    ("Geist", 700, "normal", f"{GEIST_BASE}/geist-sans/Geist-Bold.woff2"),
]
GEIST_MONO = [
    ("Geist Mono", 400, "normal", f"{GEIST_BASE}/geist-mono/GeistMono-Regular.woff2"),
    ("Geist Mono", 500, "normal", f"{GEIST_BASE}/geist-mono/GeistMono-Medium.woff2"),
    ("Geist Mono", 600, "normal", f"{GEIST_BASE}/geist-mono/GeistMono-SemiBold.woff2"),
    ("Geist Mono", 700, "normal", f"{GEIST_BASE}/geist-mono/GeistMono-Bold.woff2"),
]
GOOGLE_CSS = (
    "https://fonts.googleapis.com/css2?"
    "family=Silkscreen:wght@400;700&family=VT323&family=Nabla&family=Kablammo&display=swap"
)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8")


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def file_name_for_url(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    ext = ".woff2" if ".woff2" in url else ".woff"
    return f"{digest}{ext}"


def face_block(family: str, weight: int, style: str, src_path: str) -> str:
    return (
        "@font-face {\n"
        f"  font-family: '{family}';\n"
        f"  font-style: {style};\n"
        f"  font-weight: {weight};\n"
        f"  font-display: swap;\n"
        f"  src: url('{src_path}') format('woff2');\n"
        "}"
    )


def download_geist(entries: list[tuple[str, int, str, str]], folder: str) -> list[str]:
    blocks: list[str] = []
    for family, weight, style, url in entries:
        filename = url.rsplit("/", 1)[-1]
        dest = OUT / folder / filename
        download_file(url, dest)
        blocks.append(face_block(family, weight, style, f"/static/fonts/{folder}/{filename}"))
    return blocks


def download_google_faces() -> list[str]:
    css = fetch_text(GOOGLE_CSS)
    url_map: dict[str, str] = {}
    blocks: list[str] = []
    for block in re.split(r"(?=@font-face)", css):
        if "@font-face" not in block:
            continue
        family_match = re.search(r"font-family:\s*['\"]([^'\"]+)['\"]", block)
        weight_match = re.search(r"font-weight:\s*(\d+)", block)
        style_match = re.search(r"font-style:\s*(\w+)", block)
        url_match = re.search(r"url\((https?://[^)]+)\)", block)
        if not (family_match and weight_match and url_match):
            continue
        remote_url = url_match.group(1)
        if remote_url not in url_map:
            filename = file_name_for_url(remote_url)
            dest = OUT / "google" / filename
            download_file(remote_url, dest)
            url_map[remote_url] = f"/static/fonts/google/{filename}"
        blocks.append(
            face_block(
                family_match.group(1),
                int(weight_match.group(1)),
                style_match.group(1) if style_match else "normal",
                url_map[remote_url],
            )
        )
    return blocks


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sections = [
        "/* Self-hosted fonts — scripts/download_fonts.py */",
        *download_geist(GEIST_SANS, "geist"),
        *download_geist(GEIST_MONO, "geist-mono"),
        *download_google_faces(),
        "body { --google-font-color-nabla: colrv1; }",
    ]
    CSS_OUT.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    count = sum(1 for _ in OUT.rglob("*") if _.is_file())
    print(f"Wrote {CSS_OUT.relative_to(ROOT)} ({count} files)")


if __name__ == "__main__":
    main()
