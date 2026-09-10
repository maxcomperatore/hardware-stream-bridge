#!/usr/bin/env python3
"""
Marketing Campaign Automation Runner for bipluk
Dispatches high-converting, 3-part infotainment gear stories (60% Tech Story, 20% Hard Reality, 20% Call to Action)
to eligible free users on a 2 to 3 times per week schedule via Resend API.
"""

import os
import sys
from jinja2 import Template

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import json
import re
import urllib.error
import urllib.request

import settings
import database
try:
    from marketing_campaigns_catalog import CAMPAIGNS
except ImportError:
    CAMPAIGNS = []

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

def generate_plain_text(campaign: dict, first_name: str, email: str) -> str:
    ps_line = f"\n\nP.S. {campaign['ps_text'].strip()}\n" if campaign.get("ps_text") else "\n"
    return (
        f"{campaign.get('headline', '')}\n\n"
        f"Hey {first_name},\n\n"
        f"{campaign.get('story_body', '').strip()}\n\n"
        f"THE HARD REALITY:\n{campaign.get('hard_reality', '').strip()}\n\n"
        f"{campaign.get('call_to_action_text', '').strip()}\n\n"
        f"{campaign.get('cta_button', 'Learn More')}: {campaign.get('cta_url', 'https://bipluk.com')}\n\n"
        f"Keep the analog fires burning,\n"
        f"Max from bipluk\n"
        f"bipluk.com{ps_line}\n"
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
            "User-Agent": "bipluk-marketing/1.0",
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

def render_story_template(campaign: dict, user: dict) -> str:
    template_path = os.path.join(PROJECT_ROOT, "templates", "email_marketing_story.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    email_str = user.get("email", "")
    first_name = extract_first_name(email_str)

    template = Template(html_content)
    return template.render(
        campaign=campaign,
        first_name=first_name,
        email=email_str
    )

MAX_MARKETING_LOOPS = 1
MAX_MARKETING_EMAILS = (len(CAMPAIGNS) * MAX_MARKETING_LOOPS) if CAMPAIGNS else 20

def run_marketing_dispatch(days_interval: int = 2, force_email: str = None, max_emails: int = MAX_MARKETING_EMAILS):
    print(f"--- Starting Marketing Campaign Dispatch (Interval: {days_interval} days, Max Cap: {max_emails} emails / {MAX_MARKETING_LOOPS} loop) ---")

    if force_email:
        target_users = [{"id": 0, "email": force_email, "marketing_email_count": 0}]
    else:
        target_users = database.get_pending_marketing_users(days_interval=days_interval, max_emails=max_emails)

    if not target_users:
        print("No free users pending marketing email dispatch at this time.")
        return

    print(f"Found {len(target_users)} users eligible for marketing email dispatch.")

    for user in target_users:
        email = user.get("email")
        user_id = user.get("id")

        masked = mask_email(email)
        if not email or database.is_unsubscribed(email):
            print(f"Skipping unsubscribed or invalid email: {masked}")
            continue

        count = user.get("marketing_email_count") or 0
        if count >= max_emails:
            print(f"User {masked} has reached the maximum of {max_emails} emails (1 full cycle). Sunsetting from drip.")
            continue

        # Sequential rotation: pick next campaign based on user's send count
        if CAMPAIGNS:
            campaign = CAMPAIGNS[count % len(CAMPAIGNS)]
        else:
            print("Warning: CAMPAIGNS catalog empty, aborting.")
            return

        is_sunset_email = (count + 1) >= max_emails
        campaign_index = count % len(CAMPAIGNS)
        print(f"Selected Campaign #{campaign_index} ('{campaign['id']}') for {masked} (Send {count + 1}/{max_emails})")

        first_name = extract_first_name(email)
        html_body = render_story_template(campaign, user)
        text_body = generate_plain_text(campaign, first_name, email)

        if is_sunset_email:
            print(f"Appending graceful sunset breakup notice to final email for {masked}")
            text_body += (
                f"\n\nP.P.S. This is our {max_emails}th and final scheduled gear story. We are pausing frequent updates so we don't crowd your inbox. "
                "Your free vault and soundbanks will always remain active at bipluk.com whenever you need a quick backup. Keep the analog fires burning!\n"
            )
            sunset_notice_html = f"""
            <div style="margin-top: 24px; padding: 14px 18px; background-color: #18181b; border: 1px solid #27272a; border-radius: 8px; font-size: 11px; color: #a1a1aa; line-height: 1.5;">
                <strong style="color: #ffffff;">Final Scheduled Update ({max_emails} of {max_emails}):</strong> We are taking you off our frequent gear stories so your inbox stays clean. Your free synthesizer patch vault and Web MIDI tools will remain active whenever you need them.
            </div>
            """
            if "</body>" in html_body:
                html_body = html_body.replace("</body>", f"{sunset_notice_html}</body>")
            else:
                html_body += sunset_notice_html

        ok, err = send_resend(
            to=email,
            subject=campaign["subject"],
            body=text_body,
            html=html_body,
            from_addr=SMTP_FROM,
            reply_to="halfradiationllc@gmail.com"
        )

        if ok:
            print(f"Successfully sent campaign '{campaign['id']}' to {masked} (Send {count + 1}/{max_emails})")
            if user_id and user_id > 0:
                database.mark_marketing_sent(user_id)
            if is_sunset_email:
                print(f"--> User {masked} has completed 2 full loops ({max_emails} emails) and is now sunsetted from active drip.")
        else:
            print(f"Failed to send email to {masked}: {err}")

    print("--- Marketing Campaign Dispatch Finished ---")

if __name__ == "__main__":
    # Default interval: 2 days (enables 3x per week schedule: Tue, Thu, Sun)
    interval = 2
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        interval = int(sys.argv[1])
    
    force = None
    if len(sys.argv) > 2:
        force = sys.argv[2]

    run_marketing_dispatch(days_interval=interval, force_email=force)
