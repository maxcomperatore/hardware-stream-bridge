#!/usr/bin/env python3
"""
Marketing Campaign Automation Runner for bipluk
Sends randomized / scheduled marketing emails (Did You Know?, Features, Remember to Back Up)
to eligible users every X days via Resend API.
"""

import os
import sys
import random
import requests
from jinja2 import Template

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import main
import database

TEMPLATES = [
    {
        "name": "did_you_know",
        "file": "email_marketing_did_you_know.html",
        "subject": "Did you know? The 1983 SysEx mystery behind vintage synths 🎹"
    },
    {
        "name": "features",
        "file": "email_marketing_features.html",
        "subject": "✨ 4 superpowers inside your bipluk synth vault"
    },
    {
        "name": "remember",
        "file": "email_marketing_remember.html",
        "subject": "Remember that custom patch you spent hours tweaking? ⚡"
    }
]

def render_marketing_template(template_file: str, user: dict) -> str:
    file_path = os.path.join(PROJECT_ROOT, "templates", template_file)
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    email_str = user.get("email", "")
    first_name = email_str.split("@")[0].capitalize() if email_str else "Synth Enthusiast"

    template = Template(html_content)
    return template.render(
        first_name=first_name,
        email=email_str
    )

def run_marketing_dispatch(days_interval: int = 3, force_email: str = None):
    print(f"--- Starting Marketing Campaign Dispatch (Interval: {days_interval} days) ---")

    if force_email:
        target_users = [{"id": 0, "email": force_email}]
    else:
        target_users = database.get_pending_marketing_users(days_interval=days_interval)

    if not target_users:
        print("No users pending marketing email dispatch.")
        return

    print(f"Found {len(target_users)} users eligible for marketing email.")

    for user in target_users:
        email = user.get("email")
        user_id = user.get("id")

        if not email or database.is_unsubscribed(email):
            print(f"Skipping unsubscribed or invalid email: {email}")
            continue

        # Pick a random template campaign for variety
        campaign = random.choice(TEMPLATES)
        print(f"Selected campaign '{campaign['name']}' for {email}")

        html_body = render_marketing_template(campaign["file"], user)
        ok, err = main.send_email_via_resend(
            to=email,
            subject=campaign["subject"],
            body="",
            html=html_body,
            reply_to="halfradiationllc@gmail.com"
        )

        if ok:
            print(f"Successfully sent '{campaign['name']}' email to {email}")
            if user_id and user_id > 0:
                database.mark_marketing_sent(user_id)
        else:
            print(f"Failed to send email to {email}: {err}")

    print("--- Marketing Campaign Dispatch Finished ---")

if __name__ == "__main__":
    interval = 14  # Default 14 days (bi-weekly)
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        interval = int(sys.argv[1])
    
    force = None
    if len(sys.argv) > 2:
        force = sys.argv[2]

    run_marketing_dispatch(days_interval=interval, force_email=force)
