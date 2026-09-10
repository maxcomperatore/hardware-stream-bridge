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
        
        conversion_rate = (premium_users / total_users * 100) if total_users > 0 else 0.0
        print(f"--- Platform Stats Report ---")
        print(f"Total Users: {total_users}")
        print(f"Premium Users: {premium_users} ({conversion_rate:.1f}%)")
        print(f"Total Soundbanks: {total_banks}")
        print(f"Subscribers: {total_subscribers}")
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    send_stats_report()
