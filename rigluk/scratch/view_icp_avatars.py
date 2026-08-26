"""ICP Avatar & Profile Viewer Script for rigluk / bipluk.

Fetches all registered users from the PostgreSQL database, retrieves their
Google OAuth profile pictures, Gravatar profile pictures, and avatar badges,
and generates a sleek, dark-mode HTML gallery (scratch/icp_gallery.html).
"""

import os
import sys
import hashlib
import urllib.parse
from datetime import datetime

# Add current directory to path for database and settings imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import database


def calculate_avatar_idx(email: str) -> int:
    """Calculate 32-bit signed hash matching frontend JS avatar indexing."""
    email_clean = email.lower().strip()
    h = 0
    for char in email_clean:
        h = ((h << 5) - h) + ord(char)
        h = h & 0xFFFFFFFF
        if h & 0x80000000:
            h = -((~h + 1) & 0xFFFFFFFF)
    return (abs(h) % 6) + 1


def get_gravatar_url(email: str) -> str:
    """Generate Gravatar URL with fallback to 404."""
    email_clean = email.lower().strip()
    hash_str = hashlib.md5(email_clean.encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_str}?s=250&d=mp"


def fetch_all_users():
    """Fetch all users from PostgreSQL database."""
    conn = database.get_db_connection()
    if not conn:
        print("❌ Could not connect to PostgreSQL database.")
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY created_at DESC;")
            rows = cur.fetchall()
            conn.commit()
            return rows
    except Exception as e:
        print(f"⚠️ Query failed: {e}")
        if conn:
            conn.rollback()
        return []
    finally:
        if conn:
            conn.close()


def generate_icp_gallery(users):
    """Generate dark-mode HTML gallery of all ICP faces and profile pictures."""
    gallery_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icp_gallery.html")

    html_cards = []
    for u in users:
        if isinstance(u, dict):
            email = u.get("email", "unknown")
            created_at = u.get("created_at", "")
            plan = u.get("plan", "free")
            picture = u.get("picture") or u.get("avatar_url") or u.get("google_picture") or ""
        else:
            email = u[0]
            created_at = u[1] if len(u) > 1 else ""
            plan = u[2] if len(u) > 2 else "free"
            picture = u[3] if len(u) > 3 else ""

        # Formatting
        date_str = created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else str(created_at or "N/A")
        gravatar = get_gravatar_url(email)
        avatar_idx = calculate_avatar_idx(email)
        fallback_avatar = f"/static/avatars/Simple%20colors/Icon{avatar_idx}.png"

        # Display image priority: Google Picture -> Gravatar -> Pixel Avatar
        img_src = picture if picture else gravatar

        card_html = f"""
        <div class="user-card">
            <div class="avatar-wrap">
                <img src="{img_src}" alt="{email}" class="avatar-img" onerror="this.onerror=null; this.src='{fallback_avatar}';" />
                <span class="plan-badge {plan}">{plan.upper()}</span>
            </div>
            <div class="user-info">
                <div class="user-email">{email}</div>
                <div class="user-date">Joined: {date_str}</div>
            </div>
        </div>
        """
        html_cards.append(card_html)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>rigluk - ICP User Profile Gallery</title>
    <style>
        body {{
            background-color: #09090b;
            color: #f4f4f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            padding: 40px 20px;
            margin: 0;
        }}
        .header {{
            text-align: center;
            max-width: 800px;
            margin: 0 auto 40px;
        }}
        h1 {{
            font-size: 24px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #60a5fa;
            margin-bottom: 8px;
        }}
        p {{
            color: #71717a;
            font-size: 13px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
            gap: 20px;
            max-w: 1200px;
            margin: 0 auto;
        }}
        .user-card {{
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: transform 0.2s, border-color 0.2s;
        }}
        .user-card:hover {{
            transform: translateY(-4px);
            border-color: #3b82f6;
        }}
        .avatar-wrap {{
            position: relative;
            width: 96px;
            height: 96px;
            margin: 0 auto 16px;
        }}
        .avatar-img {{
            width: 96px;
            height: 96px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #3f3f46;
            background-color: #09090b;
        }}
        .plan-badge {{
            position: absolute;
            bottom: -4px;
            right: -4px;
            font-size: 9px;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .plan-badge.personal, .plan-badge.studio {{
            background: #2563eb;
            color: #ffffff;
            border: 1px solid #60a5fa;
        }}
        .plan-badge.free {{
            background: #27272a;
            color: #a1a1aa;
            border: 1px solid #3f3f46;
        }}
        .user-email {{
            font-size: 12px;
            font-weight: 600;
            color: #e4e4e7;
            word-break: break-all;
        }}
        .user-date {{
            font-size: 10px;
            color: #71717a;
            margin-top: 6px;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>👤 ICP Faces & User Profile Vault</h1>
        <p>Total Registered Users: <strong>{len(users)}</strong> · Google OAuth Pictures + Gravatar Auto-Resolution</p>
    </div>
    <div class="grid">
        {"".join(html_cards)}
    </div>
</body>
</html>
"""

    with open(gallery_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"✅ ICP Profile Gallery generated at: {gallery_path}")
    return gallery_path


if __name__ == "__main__":
    print("🔍 Fetching user profile pictures from PostgreSQL database...")
    users = fetch_all_users()
    print(f"📊 Found {len(users)} registered users in database.")
    
    for idx, u in enumerate(users, start=1):
        email = u.get("email") if isinstance(u, dict) else u[0]
        plan = u.get("plan") if isinstance(u, dict) else u[2]
        picture = (u.get("picture") if isinstance(u, dict) else (u[3] if len(u) > 3 else "")) or get_gravatar_url(email)
        print(f"  [{idx}] {email} ({plan}) -> {picture}")

    gallery_file = generate_icp_gallery(users)
    print("\n🚀 Done! You can view all ICP faces by opening scratch/icp_gallery.html!")
