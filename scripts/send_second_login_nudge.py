#!/usr/bin/env python3
"""
Activated User Trigger: Second Login Personal Founder Email for bipluk
Dispatches a high-converting, 1-on-1 personal check-in from Max to free users who have logged in >= 2 times.
"""

import os
import sys
import json
import re
import urllib.error
import urllib.request
from jinja2 import Template

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import settings
import database

RESEND_API_KEY = settings.RESEND_API_KEY
SMTP_FROM = settings.SMTP_FROM or "Max from bipluk <support@bipluk.com>"

def extract_first_name(email_str: str) -> str:
    if not email_str:
        return "Synth Enthusiast"
    local = email_str.split("@")[0]
    parts = re.split(r"[\._\-\+0-9]+", local)
    cleaned = [p.capitalize() for p in parts if p and len(p) > 1]
    return cleaned[0] if cleaned else "Synth Enthusiast"

def mask_email(email_str: str) -> str:
    if not email_str or "@" not in email_str:
        return "***"
    user, domain = email_str.split("@", 1)
    masked_user = (user[0] + "***" + user[-1]) if len(user) > 2 else "***"
    return f"{masked_user}@{domain}"

def generate_plain_text(first_name: str, email: str) -> str:
    return (
        f"Hey {first_name},\n\n"
        f"Saw you hopped back into Bipluk today.\n\n"
        f"Quick question: what hardware synths are you currently running in your studio?\n\n"
        f"If you ever run into any weird SysEx handshake timeouts, buffer issues, or need help with custom patch dumps for your specific machine, just hit reply to this email. It goes straight to my personal inbox and I'm always happy to troubleshoot gear with you directly.\n\n"
        f"If you're ready to unlock unlimited private cloud vaults, one-click patch auditions, and permanent soundbank backup for your entire hardware collection:\n"
        f"Claim Lifetime Studio Access: https://bipluk.com/#pricing?utm_source=email&utm_medium=trigger&utm_campaign=second_login\n\n"
        f"Keep the analog fires burning,\n"
        f"Max from bipluk\n"
        f"bipluk.com\n\n"
        f"To unsubscribe: https://bipluk.com/unsubscribe?email={email}\n"
    )

def send_resend(to: str, subject: str, body: str, html: str, from_addr: str, reply_to: str) -> tuple[bool, str | None]:
    if not RESEND_API_KEY:
        return False, "RESEND_API_KEY not configured in environment"
    payload = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "text": body,
        "html": html,
        "reply_to": [reply_to],
        "headers": {
            "List-Unsubscribe": f"<https://bipluk.com/unsubscribe?email={to}>"
        }
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "bipluk-trigger/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True, None
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        return False, f"HTTP {err.code}: {detail}"
    except Exception as err:
        return False, str(err)

def render_second_login_template(user: dict) -> str:
    template_path = os.path.join(PROJECT_ROOT, "templates", "email_second_login.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    email_str = user.get("email", "")
    first_name = extract_first_name(email_str)

    template = Template(html_content)
    return template.render(
        first_name=first_name,
        email=email_str
    )

def run_second_login_dispatch(force_email: str = None):
    print("--- Starting Second-Login Activated User Trigger Dispatch ---")

    if force_email:
        target_users = [{"id": 0, "email": force_email}]
    else:
        target_users = database.get_pending_second_login_users()

    if not target_users:
        print("No eligible free users pending second-login email dispatch at this time.")
        return

    print(f"Found {len(target_users)} high-intent returning users eligible for personal founder check-in.")

    subject = "quick question about your synth setup (from Max)"

    for user in target_users:
        email = user.get("email")
        user_id = user.get("id")
        masked = mask_email(email)

        if not email or database.is_unsubscribed(email):
            print(f"Skipping unsubscribed or invalid email: {masked}")
            continue

        first_name = extract_first_name(email)
        html_body = render_second_login_template(user)
        text_body = generate_plain_text(first_name, email)

        ok, err = send_resend(
            to=email,
            subject=subject,
            body=text_body,
            html=html_body,
            from_addr=SMTP_FROM,
            reply_to="halfradiationllc@gmail.com"
        )

        if ok:
            print(f"Successfully sent second-login founder check-in to {masked}")
            if user_id and user_id > 0:
                database.mark_second_login_sent(user_id)
        else:
            print(f"Failed to send email to {masked}: {err}")

    print("--- Second-Login Dispatch Finished ---")

if __name__ == "__main__":
    force = sys.argv[1] if len(sys.argv) > 1 else None
    run_second_login_dispatch(force_email=force)
