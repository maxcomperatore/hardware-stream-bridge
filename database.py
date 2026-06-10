import sqlite3
import os
from datetime import datetime

# Hardcoded Production Neon PostgreSQL Configuration
DATABASE_URL = "postgresql://neondb_owner:npg_pS5QZYe0Nwyr@ep-empty-night-ajgmosjt-pooler.c-3.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
IS_POSTGRES = True

def get_db_connection():
    if IS_POSTGRES:
        import psycopg2
        # psycopg2 automatically parses query params like sslmode from the connection string URL
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        DB_PATH = "d:/crew/experiment/sysex_vault.db"
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        return conn

def get_db_cursor(conn):
    if IS_POSTGRES:
        import psycopg2.extras
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn.row_factory = sqlite3.Row
        return conn.cursor()

def insert_and_get_id(conn, query, params):
    cursor = conn.cursor()
    if IS_POSTGRES:
        query = query.replace("?", "%s")
        query += " RETURNING id"
        cursor.execute(query, params)
        last_id = cursor.fetchone()[0]
    else:
        cursor.execute(query, params)
        last_id = cursor.lastrowid
    return last_id

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
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
            user_id INTEGER,
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
            bank_id INTEGER NOT NULL,
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
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            tier TEXT NOT NULL DEFAULT 'free',
            stripe_customer_id TEXT,
            created_at TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            synth_model TEXT NOT NULL,
            sysex_hex TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_id INTEGER NOT NULL,
            patch_index INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (bank_id) REFERENCES banks (id) ON DELETE CASCADE
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        
        # SQLite migration to add user_id column to existing installations
        try:
            cursor.execute("ALTER TABLE banks ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
            conn.commit()
        except sqlite3.OperationalError:
            pass # Already exists
            
    conn.commit()
    conn.close()

# --- User Table operations ---
def create_user(email: str, hashed_password: str) -> int:
    conn = get_db_connection()
    created_at = datetime.now().isoformat()
    try:
        user_id = insert_and_get_id(
            conn,
            "INSERT INTO users (email, hashed_password, tier, created_at) VALUES (?, ?, 'free', ?)",
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
    query = "SELECT * FROM users WHERE email = ?"
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor.execute(query, (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> dict:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    query = "SELECT * FROM users WHERE id = ?"
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor.execute(query, (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_tier(email: str, tier: str, stripe_customer_id: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if stripe_customer_id:
        query = "UPDATE users SET tier = ?, stripe_customer_id = ? WHERE email = ?"
        params = (tier, stripe_customer_id, email.lower().strip())
    else:
        query = "UPDATE users SET tier = ? WHERE email = ?"
        params = (tier, email.lower().strip())
        
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def update_user_tier_by_customer_id(stripe_customer_id: str, tier: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE users SET tier = ? WHERE stripe_customer_id = ?"
    params = (tier, stripe_customer_id)
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# --- Bank & Patch scoped operations ---
def save_bank(name: str, synth_model: str, sysex_hex: str, patch_names: list[str], user_id: int) -> int:
    conn = get_db_connection()
    created_at = datetime.now().isoformat()
    
    bank_id = insert_and_get_id(
        conn,
        "INSERT INTO banks (name, synth_model, sysex_hex, created_at, user_id) VALUES (?, ?, ?, ?, ?)",
        (name, synth_model, sysex_hex, created_at, user_id)
    )
    
    cursor = conn.cursor()
    for idx, patch_name in enumerate(patch_names):
        query = "INSERT INTO patches (bank_id, patch_index, name) VALUES (?, ?, ?)"
        if IS_POSTGRES:
            query = query.replace("?", "%s")
        cursor.execute(query, (bank_id, idx, patch_name))
        
    conn.commit()
    conn.close()
    return bank_id

def get_all_banks(user_id: int) -> list[dict]:
    conn = get_db_connection()
    cursor = get_db_cursor(conn)
    query = "SELECT * FROM banks WHERE user_id = ? ORDER BY id DESC"
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    
    banks = []
    for row in rows:
        p_query = "SELECT COUNT(*) as count FROM patches WHERE bank_id = ?"
        if IS_POSTGRES:
            p_query = p_query.replace("?", "%s")
        
        cursor.execute(p_query, (row['id'],))
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
    query = "SELECT * FROM banks WHERE id = ? AND user_id = ?"
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor.execute(query, (bank_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    p_query = "SELECT * FROM patches WHERE bank_id = ? ORDER BY patch_index ASC"
    if IS_POSTGRES:
        p_query = p_query.replace("?", "%s")
    cursor.execute(p_query, (bank_id,))
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
    
    v_query = "SELECT id FROM banks WHERE id = ? AND user_id = ?"
    if IS_POSTGRES:
        v_query = v_query.replace("?", "%s")
    cursor.execute(v_query, (bank_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return
        
    q1 = "DELETE FROM banks WHERE id = ?"
    q2 = "DELETE FROM patches WHERE bank_id = ?"
    if IS_POSTGRES:
        q1 = q1.replace("?", "%s")
        q2 = q2.replace("?", "%s")
    cursor.execute(q1, (bank_id,))
    cursor.execute(q2, (bank_id,))
    conn.commit()
    conn.close()

def create_subscriber(email: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    try:
        query = "INSERT INTO subscribers (email, created_at) VALUES (?, ?)"
        if IS_POSTGRES:
            query = query.replace("?", "%s")
        cursor.execute(query, (email.lower().strip(), created_at))
        conn.commit()
        return True
    except Exception as e:
        # Ignore unique constraint violations (already subscribed)
        return True
    finally:
        conn.close()
