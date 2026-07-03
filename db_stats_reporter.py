import settings
import urllib.request
import json
from datetime import datetime

# Import database module from current directory
import database

def send_stats_report():
    try:
        conn = database.get_db_connection()
        cursor = database.get_db_cursor(conn)
        
        # 1. Total users
        cursor.execute("SELECT COUNT(*) as cnt FROM users;")
        total_users = cursor.fetchone()["cnt"]
        
        # 2. Premium users
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE tier = 'premium';")
        premium_users = cursor.fetchone()["cnt"]
        
        # 3. Total banks
        cursor.execute("SELECT COUNT(*) as cnt FROM banks;")
        total_banks = cursor.fetchone()["cnt"]
        
        # 4. Total subscribers
        cursor.execute("SELECT COUNT(*) as cnt FROM subscribers;")
        total_subscribers = cursor.fetchone()["cnt"]
        
        conn.close()
    except Exception as e:
        print(f"Error querying database: {e}")
        return

    webhook_url = settings.DISCORD_WEBHOOK_URL
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL not set; skipping Discord report.")
        return
    
    # Construct Embed payload
    conversion_rate = (premium_users / total_users * 100) if total_users > 0 else 0.0
    embed = {
        "title": "📊 Weekly knob.monster Platform Report",
        "description": "Here is the summary of database metrics and growth for this week.",
        "color": 0x3498db,
        "fields": [
            {"name": "Total Registered Users", "value": str(total_users), "inline": True},
            {"name": "Premium Tier Subscribers", "value": str(premium_users), "inline": True},
            {"name": "Conversion Rate", "value": f"{conversion_rate:.1f}%", "inline": True},
            {"name": "SysEx Soundbanks Saved", "value": str(total_banks), "inline": True},
            {"name": "Newsletter Subscribers", "value": str(total_subscribers), "inline": True}
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "footer": {
            "text": "knob.monster cron jobs",
            "icon_url": "https://knob.monster/static/logo.png"
        }
    }
    
    payload = {
        "username": "Knob Monster Bot",
        "avatar_url": "https://knob.monster/static/logo.png",
        "embeds": [embed]
    }
    
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
        print("Weekly report successfully sent to Discord.")
    except Exception as e:
        print(f"Failed to send weekly report to Discord: {e}")

if __name__ == "__main__":
    send_stats_report()
