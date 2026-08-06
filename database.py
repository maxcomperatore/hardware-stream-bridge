import os
import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import settings
import psycopg2
import psycopg2.extras

RAW_DATABASE_URL = settings.DATABASE_URL
_DB_OFFLINE_CACHE = False
_DB_LAST_CHECK = 0.0

def optimize_neon_url(url: str | None) -> str | None:
    """Return clean database URL without host string corruption."""
    return url

DATABASE_URL = optimize_neon_url(RAW_DATABASE_URL)

def mark_db_offline():
    global _DB_OFFLINE_CACHE, _DB_LAST_CHECK
    _DB_OFFLINE_CACHE = True
    _DB_LAST_CHECK = time.time()

def is_db_offline() -> bool:
    global _DB_OFFLINE_CACHE, _DB_LAST_CHECK
    now = time.time()
    # Cache result for 30s to avoid repeated timeouts
    if _DB_OFFLINE_CACHE and (now - _DB_LAST_CHECK < 30):
        return True
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
        conn.close()
        _DB_OFFLINE_CACHE = False
        return False
    except Exception as e:
        mark_db_offline()
        return True

def get_db_connection(max_retries=1, retry_delay=0.5):
    """
    Connect to PostgreSQL with quick retry for Neon cold starts.
    Includes connect_timeout=5 to prevent hanging connections.
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set.")

    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
            _DB_OFFLINE_CACHE = False
            return conn
        except Exception as e:
            mark_db_offline()
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise e

def get_db_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def insert_and_get_id(conn, query, params):
    cursor = conn.cursor()
    if "RETURNING id" not in query.upper():
        query += " RETURNING id"
    cursor.execute(query, params)
    last_id = cursor.fetchone()[0]
    return last_id

def init_db():
    # Cleanup local SQLite leftover database file if present
    sqlite_file = "d:/crew/experiment/sysex_vault.db"
    if os.path.exists(sqlite_file):
        try:
            os.remove(sqlite_file)
        except Exception as e:
            print(f"Failed to delete SQLite leftovers: {e}")
            
    # Cleanup unused, leftover templates
    deprecated_templates = [
        "d:/crew/experiment/templates/changelog.html",
        "d:/crew/experiment/templates/about.html",
        "d:/crew/experiment/templates/library.html",
        "d:/crew/experiment/templates/roadmap.html"
    ]
    for temp_path in deprecated_templates:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Failed to delete leftover template {temp_path}: {e}")

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"Warning: Skipping init_db because database is offline/suspended: {e}")
        return

    try:
        cursor = conn.cursor()
        
        # Create users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            tier VARCHAR(50) NOT NULL DEFAULT 'free',
            stripe_customer_id VARCHAR(255),
            created_at VARCHAR(100) NOT NULL
        )
        """)
        # Create banks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            synth_model VARCHAR(255) NOT NULL,
            sysex_hex TEXT NOT NULL,
            created_at VARCHAR(100) NOT NULL
        )
        """)
        # Create patches
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patches (
            id SERIAL PRIMARY KEY,
            bank_id INTEGER REFERENCES banks(id) ON DELETE CASCADE,
            patch_index INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL
        )
        """)
        # Create subscribers
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            created_at VARCHAR(100) NOT NULL
        )
        """)
        # Pending premiums: holds paid-but-not-yet-registered users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_premiums (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            stripe_customer_id VARCHAR(255),
            created_at VARCHAR(100) NOT NULL,
            plan VARCHAR(50) DEFAULT 'personal'
        )
        """)
        
        # Create unsubscribed_emails table for tracking opt-outs
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS unsubscribed_emails (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            unsubscribed_at VARCHAR(100) NOT NULL
        )
        """)
        
        # Add drip_email_sent tracking to users table
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS drip_email_sent BOOLEAN DEFAULT FALSE;")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(50);")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS picture_url TEXT;")
        cursor.execute("ALTER TABLE pending_premiums ADD COLUMN IF NOT EXISTS plan VARCHAR(50) DEFAULT 'personal';")
        
        conn.commit()
    except Exception as e:
        print(f"Warning: Database error during table migrations: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

# --- User Table operations ---
def create_user(email: str, hashed_password: str) -> int:
    try:
        conn = get_db_connection()
        created_at = datetime.now().isoformat()
        try:
            user_id = insert_and_get_id(
                conn,
                "INSERT INTO users (email, hashed_password, tier, created_at) VALUES (%s, %s, 'free', %s)",
                (email.lower().strip(), hashed_password, created_at)
            )
            conn.commit()
            return user_id
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in create_user: {e}")
        raise RuntimeError("Database is undergoing monthly quota reset. Registration will resume tomorrow!")

def get_user_by_email(email: str) -> dict | None:
    try:
        conn = get_db_connection()
        try:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in get_user_by_email: {e}")
        return None

def get_user_by_id(user_id: int) -> dict | None:
    try:
        conn = get_db_connection()
        try:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in get_user_by_id: {e}")
        return None

def get_user_by_customer_id(stripe_customer_id: str) -> dict | None:
    try:
        conn = get_db_connection()
        try:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT * FROM users WHERE stripe_customer_id = %s", (stripe_customer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in get_user_by_customer_id: {e}")
        return None

def update_user_tier(email: str, tier: str, stripe_customer_id: str = None, plan: str = None):
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            email = email.lower().strip()
            if stripe_customer_id and plan:
                query = "UPDATE users SET tier = %s, stripe_customer_id = %s, plan = %s WHERE email = %s"
                params = (tier, stripe_customer_id, plan, email)
            elif stripe_customer_id:
                query = "UPDATE users SET tier = %s, stripe_customer_id = %s WHERE email = %s"
                params = (tier, stripe_customer_id, email)
            elif plan:
                query = "UPDATE users SET tier = %s, plan = %s WHERE email = %s"
                params = (tier, plan, email)
            else:
                query = "UPDATE users SET tier = %s WHERE email = %s"
                params = (tier, email)
                
            cursor.execute(query, params)
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in update_user_tier: {e}")

def update_user_picture(email: str, picture_url: str):
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET picture_url = %s WHERE email = %s", (picture_url, email.lower().strip()))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in update_user_picture: {e}")
        return None

def update_user_password(email: str, hashed_password: str):
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET hashed_password = %s WHERE email = %s", (hashed_password, email.lower().strip()))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in update_user_password: {e}")
        return None

def delete_user(user_id: int) -> bool:
    """Permanently delete user and all associated soundbank vaults."""
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM banks WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in delete_user: {e}")
        return False

def update_user_tier_by_customer_id(stripe_customer_id: str, tier: str):
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET tier = %s WHERE stripe_customer_id = %s", (tier, stripe_customer_id))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in update_user_tier_by_customer_id: {e}")
        return None

def upsert_pending_premium(email: str, stripe_customer_id: str = None, plan: str = "personal"):
    """Park a premium grant for an email that hasn't registered yet."""
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            created_at = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO pending_premiums (email, stripe_customer_id, created_at, plan)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    stripe_customer_id = EXCLUDED.stripe_customer_id,
                    plan = EXCLUDED.plan
                """,
                (email.lower().strip(), stripe_customer_id, created_at, plan)
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in upsert_pending_premium: {e}")
        return None

def consume_pending_premium(email: str) -> dict | None:
    """Check if there's a pending premium for this email. Returns the record and deletes it."""
    try:
        conn = get_db_connection()
        try:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT * FROM pending_premiums WHERE email = %s", (email.lower().strip(),))
            row = cursor.fetchone()
            if row:
                dc = conn.cursor()
                dc.execute("DELETE FROM pending_premiums WHERE email = %s", (email.lower().strip(),))
                conn.commit()
            return dict(row) if row else None
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in consume_pending_premium: {e}")
        return None

# --- Bank & Patch scoped operations ---
def save_bank(name: str, synth_model: str, sysex_hex: str, patch_names: list[str], user_id: int) -> int | None:
    try:
        conn = get_db_connection()
        try:
            created_at = datetime.now().isoformat()
            
            bank_id = insert_and_get_id(
                conn,
                "INSERT INTO banks (name, synth_model, sysex_hex, created_at, user_id) VALUES (%s, %s, %s, %s, %s)",
                (name, synth_model, sysex_hex, created_at, user_id)
            )
            
            cursor = conn.cursor()
            for idx, patch_name in enumerate(patch_names):
                cursor.execute(
                    "INSERT INTO patches (bank_id, patch_index, name) VALUES (%s, %s, %s)",
                    (bank_id, idx, patch_name)
                )
                
            conn.commit()
            return bank_id
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in save_bank: {e}")
        return None

def get_all_banks(user_id: int) -> list[dict]:
    try:
        conn = get_db_connection()
        try:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT * FROM banks WHERE user_id = %s ORDER BY id DESC", (user_id,))
            rows = cursor.fetchall()
            
            banks = []
            for row in rows:
                cursor.execute("SELECT COUNT(*) as count FROM patches WHERE bank_id = %s", (row['id'],))
                count = cursor.fetchone()['count']
                
                dt = datetime.fromisoformat(row['created_at'])
                formatted_date = dt.strftime("%b %d, %Y %I:%M %p")
                
                banks.append({
                    "id": row['id'],
                    "name": row['name'],
                    "synth_model": row['synth_model'],
                    "sysex_hex": row['sysex_hex'],
                    "created_at": formatted_date,
                    "patch_count": count
                })
                
            return banks
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in get_all_banks: {e}")
        return []

def get_bank(bank_id: int, user_id: int) -> dict | None:
    try:
        conn = get_db_connection()
        try:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT * FROM banks WHERE id = %s AND user_id = %s", (bank_id, user_id))
            row = cursor.fetchone()
            if not row:
                return None
                
            cursor.execute("SELECT * FROM patches WHERE bank_id = %s ORDER BY patch_index ASC", (bank_id,))
            patch_rows = cursor.fetchall()
            
            dt = datetime.fromisoformat(row['created_at'])
            formatted_date = dt.strftime("%b %d, %Y %I:%M %p")
            
            return {
                "id": row['id'],
                "name": row['name'],
                "synth_model": row['synth_model'],
                "sysex_hex": row['sysex_hex'],
                "created_at": formatted_date,
                "patches": [{"index": p['patch_index'], "name": p['name']} for p in patch_rows]
            }
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in get_bank: {e}")
        return None

def delete_bank(bank_id: int, user_id: int):
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM banks WHERE id = %s AND user_id = %s", (bank_id, user_id))
            if not cursor.fetchone():
                return
                
            cursor.execute("DELETE FROM banks WHERE id = %s", (bank_id,))
            cursor.execute("DELETE FROM patches WHERE bank_id = %s", (bank_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in delete_bank: {e}")
        return

def create_subscriber(email: str) -> bool:
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            created_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO subscribers (email, created_at) VALUES (%s, %s)",
                (email.lower().strip(), created_at)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in create_subscriber: {e}")
        return True

def get_pending_drip_users() -> list[dict]:
    try:
        conn = get_db_connection()
        try:
            cursor = get_db_cursor(conn)
            cursor.execute("SELECT id, email, created_at FROM users WHERE tier = 'free' AND drip_email_sent = FALSE")
            rows = cursor.fetchall()
            return rows
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in get_pending_drip_users: {e}")
        return []

def mark_drip_sent(user_id: int):
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET drip_email_sent = TRUE WHERE id = %s", (user_id,))
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in mark_drip_sent: {e}")
        return

def add_to_unsubscribed(email: str):
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            unsubscribed_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO unsubscribed_emails (email, unsubscribed_at) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING",
                (email.lower().strip(), unsubscribed_at)
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in add_to_unsubscribed: {e}")
        return

def get_all_newsletter_recipients() -> list[str]:
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Fetch all user emails
            cursor.execute("SELECT email FROM users")
            user_emails = [row[0].lower().strip() for row in cursor.fetchall()]
            
            # Fetch all newsletter subscribers
            cursor.execute("SELECT email FROM subscribers")
            sub_emails = [row[0].lower().strip() for row in cursor.fetchall()]
            
            # Fetch all unsubscribed emails
            cursor.execute("SELECT email FROM unsubscribed_emails")
            unsub_emails = set(row[0].lower().strip() for row in cursor.fetchall())
            
            # Combine, de-duplicate and filter
            all_emails = set(user_emails + sub_emails)
            valid_recipients = [email for email in all_emails if email and email not in unsub_emails]
            return valid_recipients
        finally:
            conn.close()
    except Exception as e:
        print(f"Database error in get_all_newsletter_recipients: {e}")
        return []
