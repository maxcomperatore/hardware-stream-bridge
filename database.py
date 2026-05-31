import sqlite3
import os
from datetime import datetime

DB_PATH = "d:/crew/experiment/sysex_vault.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create banks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS banks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        synth_model TEXT NOT NULL,
        sysex_hex TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    # Create patches table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_id INTEGER NOT NULL,
        patch_index INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (bank_id) REFERENCES banks (id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

def save_bank(name: str, synth_model: str, sysex_hex: str, patch_names: list[str]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    created_at = datetime.now().isoformat()
    
    # Insert bank
    cursor.execute(
        "INSERT INTO banks (name, synth_model, sysex_hex, created_at) VALUES (?, ?, ?, ?)",
        (name, synth_model, sysex_hex, created_at)
    )
    bank_id = cursor.lastrowid
    
    # Insert patches
    for idx, patch_name in enumerate(patch_names):
        cursor.execute(
            "INSERT INTO patches (bank_id, patch_index, name) VALUES (?, ?, ?)",
            (bank_id, idx, patch_name)
        )
        
    conn.commit()
    conn.close()
    return bank_id

def get_all_banks() -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM banks ORDER BY id DESC")
    rows = cursor.fetchall()
    
    banks = []
    for row in rows:
        # Get count of patches
        cursor.execute("SELECT COUNT(*) as count FROM patches WHERE bank_id = ?", (row['id'],))
        count = cursor.fetchone()['count']
        
        # Format created_at to a human readable format
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

def get_bank(bank_id: int) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM banks WHERE id = ?", (bank_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    # Get patches
    cursor.execute("SELECT * FROM patches WHERE bank_id = ? ORDER BY patch_index ASC", (bank_id,))
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

def delete_bank(bank_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banks WHERE id = ?", (bank_id,))
    cursor.execute("DELETE FROM patches WHERE bank_id = ?", (bank_id,))
    conn.commit()
    conn.close()
