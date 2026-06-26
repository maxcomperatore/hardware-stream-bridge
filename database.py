import os
from datetime import datetime
import psycopg2
import psycopg2.extras

# Load database connection string from environment variables in production
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_pS5QZYe0Nwyr@ep-empty-night-ajgmosjt-pooler.c-3.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

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
            
    # Cleanup unused, leftover templates/changelog.html (route is a redirect to /about)
    changelog_file = "d:/crew/experiment/templates/changelog.html"
    if os.path.exists(changelog_file):
        try:
            os.remove(changelog_file)
        except Exception as e:
            print(f"Failed to delete leftover changelog template: {e}")

    conn = get_db_connection()
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
        created_at VARCHAR(100) NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

# --- User Table operations ---
def create_user(email: str, hashed_password: str) -> int:
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
    except Exception as e:
        conn.close()
        raise e
    finally:
        conn.close()

def get_user_by_email(email: str) -> dict:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> dict:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_tier(email: str, tier: str, stripe_customer_id: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if stripe_customer_id:
        query = "UPDATE users SET tier = %s, stripe_customer_id = %s WHERE email = %s"
        params = (tier, stripe_customer_id, email.lower().strip())
    else:
        query = "UPDATE users SET tier = %s WHERE email = %s"
        params = (tier, email.lower().strip())
        
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def update_user_tier_by_customer_id(stripe_customer_id: str, tier: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET tier = %s WHERE stripe_customer_id = %s", (tier, stripe_customer_id))
    conn.commit()
    conn.close()

def upsert_pending_premium(email: str, stripe_customer_id: str = None):
    """Park a premium grant for an email that hasn't registered yet."""
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO pending_premiums (email, stripe_customer_id, created_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET stripe_customer_id = EXCLUDED.stripe_customer_id
        """,
        (email.lower().strip(), stripe_customer_id, created_at)
    )
    conn.commit()
    conn.close()

def consume_pending_premium(email: str) -> dict:
    """Check if there's a pending premium for this email. Returns the record and deletes it."""
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM pending_premiums WHERE email = %s", (email.lower().strip(),))
    row = cursor.fetchone()
    if row:
        dc = conn.cursor()
        dc.execute("DELETE FROM pending_premiums WHERE email = %s", (email.lower().strip(),))
        conn.commit()
    conn.close()
    return dict(row) if row else None

# --- Bank & Patch scoped operations ---
def save_bank(name: str, synth_model: str, sysex_hex: str, patch_names: list[str], user_id: int) -> int:
    conn = get_db_connection()
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
    conn.close()
    return bank_id

def get_all_banks(user_id: int) -> list[dict]:
    conn = get_db_connection()
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
        
    conn.close()
    return banks

def get_bank(bank_id: int, user_id: int) -> dict:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    cursor.execute("SELECT * FROM banks WHERE id = %s AND user_id = %s", (bank_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    cursor.execute("SELECT * FROM patches WHERE bank_id = %s ORDER BY patch_index ASC", (bank_id,))
    patch_rows = cursor.fetchall()
    
    dt = datetime.fromisoformat(row['created_at'])
    formatted_date = dt.strftime("%b %d, %Y %I:%M %p")
    
    bank = {
        "id": row['id'],
        "name": row['name'],
        "synth_model": row['synth_model'],
        "sysex_hex": row['sysex_hex'],
        "created_at": formatted_date,
        "patches": [{"index": p['patch_index'], "name": p['name']} for p in patch_rows]
    }
    
    conn.close()
    return bank

def delete_bank(bank_id: int, user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM banks WHERE id = %s AND user_id = %s", (bank_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return
        
    cursor.execute("DELETE FROM banks WHERE id = %s", (bank_id,))
    cursor.execute("DELETE FROM patches WHERE bank_id = %s", (bank_id,))
    conn.commit()
    conn.close()

def create_subscriber(email: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    try:
        cursor.execute(
            "INSERT INTO subscribers (email, created_at) VALUES (%s, %s)",
            (email.lower().strip(), created_at)
        )
        conn.commit()
        return True
    except Exception:
        # Ignore unique constraint violations (already subscribed)
        return True
    finally:
        conn.close()
