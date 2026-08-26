"""Inactivity Warning & Soft-Archival Worker Engine for bipluk & rigluk.

Executes two-stage dormant retention workflow:
1. STAGE 1 (Day 330 of zero logins):
   Finds free users inactive for 330+ days who haven't received a warning.
   Renders email_inactivity_warning.html & dispatches warning email via Resend.
   Sets inactivity_warning_sent = TRUE.

2. STAGE 2 (Day 360 of zero logins):
   Finds free users with inactivity_warning_sent = TRUE who still haven't logged in after 30 days.
   Flags is_archived = TRUE and records archived_at timestamp.

3. RE-ACTIVATION (Automated):
   When a user logs in (database.record_user_login), is_archived and inactivity_warning_sent automatically reset to FALSE.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import database
import main

def process_inactivity_lifecycle(dry_run: bool = True):
    database.init_db()
    print("=" * 70)
    print("⏰ INACTIVITY & VAULT ARCHIVAL WORKER ENGINE")
    print("=" * 70)
    print(f"Mode: {'🧪 DRY RUN' if dry_run else '🚀 EXECUTING LIVE'}\n")

    conn = database.get_db_connection()
    if not conn:
        print("❌ Could not connect to database.")
        return

    now = datetime.now()
    cutoff_warning = now - timedelta(days=330)
    cutoff_archive = now - timedelta(days=360)

    try:
        cursor = conn.cursor(cursor_factory=database.psycopg2.extras.RealDictCursor)

        # STAGE 1: Find users needing inactivity warning (Day 330)
        cursor.execute("""
            SELECT id, email, created_at, last_login_at, tier, plan
            FROM users
            WHERE (tier IS NULL OR LOWER(tier) = 'free')
              AND (plan IS NULL OR LOWER(plan) NOT IN ('personal', 'studio', 'vip', 'pro'))
              AND (inactivity_warning_sent IS FALSE OR inactivity_warning_sent IS NULL)
              AND (is_archived IS FALSE OR is_archived IS NULL)
        """)
        candidates = cursor.fetchall()
        
        warning_targets = []
        for u in candidates:
            last_activity_str = u.get("last_login_at") or u.get("created_at")
            if not last_activity_str:
                continue
            try:
                dt = datetime.fromisoformat(str(last_activity_str))
                if dt <= cutoff_warning:
                    warning_targets.append(u)
            except Exception:
                pass

        print(f"📧 Stage 1 - Warning Targets (Day 330 Inactive): {len(warning_targets)}")
        for u in warning_targets:
            print(f"   • Sending 30-day archival alert to: {u['email']}")
            if not dry_run:
                main.send_inactivity_warning_email_task(u['email'])
                up_cursor = conn.cursor()
                up_cursor.execute("UPDATE users SET inactivity_warning_sent = TRUE WHERE id = %s", (u['id'],))
                conn.commit()

        # STAGE 2: Soft-Archive Users (Day 360)
        cursor.execute("""
            SELECT id, email, created_at, last_login_at
            FROM users
            WHERE (tier IS NULL OR LOWER(tier) = 'free')
              AND inactivity_warning_sent IS TRUE
              AND (is_archived IS FALSE OR is_archived IS NULL)
        """)
        archive_candidates = cursor.fetchall()
        archive_targets = []
        for u in archive_candidates:
            last_activity_str = u.get("last_login_at") or u.get("created_at")
            if not last_activity_str:
                continue
            try:
                dt = datetime.fromisoformat(str(last_activity_str))
                if dt <= cutoff_archive:
                    archive_targets.append(u)
            except Exception:
                pass

        print(f"\n📦 Stage 2 - Soft-Archive Targets (Day 360 Inactive): {len(archive_targets)}")
        for u in archive_targets:
            print(f"   • Soft-archiving dormant vault for: {u['email']}")
            if not dry_run:
                up_cursor = conn.cursor()
                up_cursor.execute(
                    "UPDATE users SET is_archived = TRUE, archived_at = %s WHERE id = %s",
                    (now.isoformat(), u['id'])
                )
                conn.commit()

    finally:
        conn.close()

    print("\n" + "=" * 70)
    print("✅ Inactivity Worker Process Complete!")
    print("=" * 70)

if __name__ == "__main__":
    live = "--live" in sys.argv
    process_inactivity_lifecycle(dry_run=not live)
