"""ICP Intelligence & User Segmentation Analyzer for bipluk & rigluk.

Segments all database users into actionable cohort buckets:
1. LURKER_ZERO_USAGE: Registered, 0 banks created (Needs 1-click demo bank push)
2. ENGAGED_FREE_USER: 1 bank full, >= 2 logins (Prime $49 Lifetime upgrade target!)
3. BOUNCED_ONETIMER: 1 login, 0 banks, > 48h old (Needs re-engagement drip)
4. HAPPY_CUSTOMERS: Paid members ($49 Lifetime)
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import database

def run_icp_intelligence():
    database.init_db()
    print("=" * 70)
    print("🧠 BIPLUK / RIGLUK - ICP USER INTELLIGENCE & SEGMENTATION ENGINE")
    print("=" * 70)

    segments = database.get_icp_user_segmentation()

    total_users = sum(len(users) for users in segments.values())
    print(f"\n📊 TOTAL REGISTERED USERS IN DATABASE: {total_users}\n")

    # 1. Lurkers
    lurkers = segments.get("LURKER_ZERO_USAGE", [])
    print(f"🥷 1. LURKERS (Registered, 0 banks, 0 usage) -> {len(lurkers)} users ({round(len(lurkers)/max(1, total_users)*100, 1)}%)")
    for u in lurkers[:5]:
        print(f"   • {u['email']} | Logins: {u.get('login_count', 1)} | Joined: {u.get('created_at', 'N/A')}")
    if len(lurkers) > 5:
        print(f"   ... and {len(lurkers) - 5} more lurkers")

    # 2. Engaged Free Users
    engaged = segments.get("ENGAGED_FREE_USER", [])
    print(f"\n⚡ 2. ENGAGED FREE USERS (Vault Full - 1 Bank, >= 2 Logins) -> {len(engaged)} users ({round(len(engaged)/max(1, total_users)*100, 1)}%)")
    print("   👉 ACTION: Prime target for $49 Lifetime upgrade email!")
    for u in engaged[:5]:
        print(f"   • {u['email']} | Banks: {u['bank_count']} | Logins: {u.get('login_count', 1)}")

    # 3. Bounced One-Timers
    bounced = segments.get("BOUNCED_ONETIMER", [])
    print(f"\n👻 3. BOUNCED ONE-TIMERS (1 Login, 0 Banks, >48h old) -> {len(bounced)} users ({round(len(bounced)/max(1, total_users)*100, 1)}%)")
    for u in bounced[:5]:
        print(f"   • {u['email']} | Joined: {u.get('created_at', 'N/A')}")

    # 4. Happy Customers
    paid = segments.get("HAPPY_CUSTOMERS", [])
    print(f"\n🏆 4. HAPPY CUSTOMERS (Paid $49 Lifetime Members) -> {len(paid)} users ({round(len(paid)/max(1, total_users)*100, 1)}%)")
    for u in paid[:5]:
        print(f"   • {u['email']} | Plan: {(u.get('plan') or u.get('tier') or 'PAID').upper()} | Banks: {u['bank_count']}")

    print("\n" + "=" * 70)
    print("✅ ICP Intelligence Segmentation Complete!")
    print("=" * 70)

if __name__ == "__main__":
    run_icp_intelligence()
