#!/usr/bin/env python3
"""Send biweekly newsletter via Resend from GitHub Actions (not Vercel — CF 1010)."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

SITE = "https://knob.monster"
CRON_SECRET = "knob_drip_cron_secret_7788"
RESEND_API_KEY = "re_ADkvw7wX_M7HjJRUUVphAuWg6rf8aNpQa"


def http_json(method: str, url: str, body: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {CRON_SECRET}", "User-Agent": "knob.monster-newsletter/1.0"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_resend(
    to: str,
    subject: str,
    body: str,
    from_addr: str,
    reply_to: str,
    list_unsubscribe: str,
) -> tuple[bool, str | None]:
    payload = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "text": body,
        "reply_to": [reply_to],
        "headers": {
            "List-Unsubscribe": f"<{list_unsubscribe}>",
            "Precedence": "bulk",
        },
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "knob.monster-newsletter/1.0",
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
    queue = http_json("GET", f"{SITE}/api/cron/newsletter-pending")
    status = queue.get("status")
    if status == "skipped":
        print(json.dumps(queue, indent=2))
        return 0
    if status == "empty":
        print("no newsletter recipients")
        return 0
    if status != "ready":
        print(f"unexpected status: {status}", file=sys.stderr)
        return 1

    subject = queue["subject"]
    from_addr = queue["from"]
    reply_to = queue["reply_to"]
    recipients = queue.get("recipients") or []

    sent_count = 0
    failed: list[dict] = []

    for item in recipients:
        ok, err = send_resend(
            item["email"],
            subject,
            item["body"],
            from_addr,
            reply_to,
            item["list_unsubscribe"],
        )
        if ok:
            sent_count += 1
            print(f"sent: {item['email']}")
        else:
            failed.append({"email": item["email"], "error": err})
            print(f"failed: {item['email']} — {err}", file=sys.stderr)
        time.sleep(0.6)

    result = http_json(
        "POST",
        f"{SITE}/api/cron/newsletter-ack",
        {
            "sent_count": sent_count,
            "failed_count": len(failed),
            "subject": subject,
            "failed": failed,
        },
    )
    print(json.dumps(result, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
