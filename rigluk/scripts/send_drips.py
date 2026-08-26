#!/usr/bin/env python3
"""Send paywall drip emails via Resend from GitHub Actions (not Vercel — CF 1010)."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import settings

SITE = settings.SITE_BASE
CRON_SECRET = settings.CRON_SECRET
RESEND_API_KEY = settings.RESEND_API_KEY


def http_json(method: str, url: str, body: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {CRON_SECRET}", "User-Agent": "rigluk-drip/1.0"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_resend(to: str, subject: str, body: str, from_addr: str, reply_to: str) -> tuple[bool, str | None]:
    payload = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "text": body,
        "reply_to": [reply_to],
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "rigluk-drip/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True, None
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        return False, f"HTTP {err.code}: {detail}"
    except Exception as err:
        return False, str(err)


def main() -> int:
    queue = http_json("GET", f"{SITE}/api/cron/drip-pending")
    subject = queue["subject"]
    body = queue["body"]
    from_addr = queue["from"]
    reply_to = queue["reply_to"]
    users = queue.get("users") or []

    sent: list[dict] = []
    failed: list[dict] = []

    for user in users:
        ok, err = send_resend(user["email"], subject, body, from_addr, reply_to)
        if ok:
            sent.append(
                {
                    "id": user["id"],
                    "email": user["email"],
                    "elapsed_seconds": user.get("elapsed_seconds"),
                }
            )
            print(f"sent: {user['email']}")
        else:
            failed.append({"id": user["id"], "email": user["email"], "error": err})
            print(f"failed: {user['email']} — {err}", file=sys.stderr)
        time.sleep(0.6)

    result = http_json(
        "POST",
        f"{SITE}/api/cron/drip-ack",
        {
            "sent": sent,
            "failed": failed,
            "skipped_young": queue.get("skipped_young", 0),
            "pending_total": queue.get("pending_total", 0),
        },
    )
    print(json.dumps(result, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
