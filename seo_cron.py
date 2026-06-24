#!/usr/bin/env python3
"""
SEO cron for knob.monster

What it does:
- Fetches key pages
- Checks title, description, canonical, robots meta
- Validates sitemap.xml and robots.txt
- Finds broken internal links
- Optionally runs Lighthouse if installed

Usage:
  python seo_cron.py https://knob.monster

Exit codes:
  0 = all good or only non-blocking warnings
  1 = one or more failures
"""

from __future__ import annotations

import re
import sys
import json
import shutil
import subprocess
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


TIMEOUT = 15
USER_AGENT = "knob-monster-seo-cron/1.0"


IMPORTANT_PATHS = [
    "/",
    "/roadmap",
    "/about",
    "/payment-methods",
    "/terms",
    "/privacy",
    "/sysex-librarian-alternatives",
    "/knob-monster-vs-snoize-sysex-librarian",
    "/knob-monster-vs-midi-ox",
    "/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str = ""


def fetch(url: str) -> requests.Response:
    return requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        allow_redirects=True,
    )


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def check_page(base_url: str, path: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    url = urljoin(base_url, path)

    try:
        resp = fetch(url)
    except Exception as e:
        return [CheckResult(f"{path} fetch", False, f"request failed: {e}")]

    if resp.status_code >= 400:
        return [CheckResult(f"{path} fetch", False, f"HTTP {resp.status_code}")]

    soup = BeautifulSoup(resp.text, "html.parser")

    title = clean_text(soup.title.string if soup.title else None)
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = clean_text(desc_tag.get("content") if desc_tag else None)
    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical = clean_text(canonical_tag.get("href") if canonical_tag else None)
    robots_tag = soup.find("meta", attrs={"name": "robots"})
    robots = clean_text(robots_tag.get("content") if robots_tag else "")

    results.append(
        CheckResult(
            f"{path} title",
            bool(title),
            title or "missing title",
        )
    )
    results.append(
        CheckResult(
            f"{path} description",
            bool(desc),
            desc or "missing meta description",
        )
    )
    results.append(
        CheckResult(
            f"{path} canonical",
            bool(canonical),
            canonical or "missing canonical",
        )
    )

    if robots:
        bad = any(x in robots.lower() for x in ["noindex", "none"])
        results.append(
            CheckResult(
                f"{path} indexability",
                not bad,
                f"robots meta = {robots}",
            )
        )
    else:
        results.append(
            CheckResult(f"{path} indexability", True, "no robots meta found")
        )

    # internal links on this page
    page_url = resp.url
    page_base = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        abs_url = urljoin(page_base, href)
        if urlparse(abs_url).netloc == urlparse(page_base).netloc:
            links.add(abs_url)

    broken = []
    for link in sorted(links):
        try:
            r = fetch(link)
            if r.status_code >= 400:
                broken.append(f"{link} -> HTTP {r.status_code}")
        except Exception as e:
            broken.append(f"{link} -> request failed: {e}")

    if broken:
        results.append(
            CheckResult(
                f"{path} broken links",
                False,
                "\n".join(broken[:20]) + ("" if len(broken) <= 20 else "\n...more"),
            )
        )
    else:
        results.append(CheckResult(f"{path} broken links", True, "none found"))

    return results


def check_sitemap(base_url: str) -> CheckResult:
    try:
        resp = fetch(urljoin(base_url, "/sitemap.xml"))
    except Exception as e:
        return CheckResult("sitemap", False, f"request failed: {e}")

    if resp.status_code >= 400:
        return CheckResult("sitemap", False, f"HTTP {resp.status_code}")

    ok = "<urlset" in resp.text and "<loc>" in resp.text
    return CheckResult("sitemap", ok, "valid xml" if ok else "invalid sitemap format")


def check_robots(base_url: str) -> CheckResult:
    try:
        resp = fetch(urljoin(base_url, "/robots.txt"))
    except Exception as e:
        return CheckResult("robots.txt", False, f"request failed: {e}")

    if resp.status_code >= 400:
        return CheckResult("robots.txt", False, f"HTTP {resp.status_code}")

    text = resp.text.lower()
    ok = "user-agent" in text and ("allow" in text or "disallow" in text)
    return CheckResult("robots.txt", ok, "present" if ok else "missing expected directives")


def run_lighthouse(base_url: str) -> CheckResult:
    if not shutil.which("lighthouse"):
        return CheckResult("lighthouse", True, "skipped (lighthouse not installed)")

    cmd = [
        "lighthouse",
        base_url,
        "--quiet",
        "--only-categories=seo",
        "--output=json",
        "--output-path=./lighthouse-seo.json",
        "--chrome-flags=--headless --no-sandbox",
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            return CheckResult("lighthouse", False, proc.stderr.strip() or proc.stdout.strip())

        with open("./lighthouse-seo.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        seo_score = data["categories"]["seo"]["score"] * 100
        return CheckResult("lighthouse", seo_score >= 90, f"seo score={seo_score:.0f}")
    except Exception as e:
        return CheckResult("lighthouse", False, f"failed: {e}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python seo_cron.py https://knob.monster")
        return 1

    base_url = sys.argv[1].rstrip("/")
    failures = 0
    warnings = []

    checks: list[CheckResult] = []
    checks.append(check_sitemap(base_url))
    checks.append(check_robots(base_url))
    checks.append(run_lighthouse(base_url))

    for path in IMPORTANT_PATHS:
        checks.extend(check_page(base_url, path))

    print("\nSEO CRON REPORT")
    print("=" * 60)

    for c in checks:
        status = "OK" if c.ok else "FAIL"
        print(f"[{status}] {c.name}: {c.details}")
        if not c.ok:
            failures += 1

    print("=" * 60)
    print(f"Failures: {failures}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())