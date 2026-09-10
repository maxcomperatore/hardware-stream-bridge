#!/usr/bin/env python3
"""Reset a user's password (bcrypt). Run from repo root with DATABASE_URL set."""

import argparse
import secrets
import string
import sys
from pathlib import Path

import bcrypt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import database


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a knob.monster user password.")
    parser.add_argument("email", help="Account email address")
    parser.add_argument(
        "--password",
        help="New password (min 8 chars). If omitted, a random one is generated.",
    )
    args = parser.parse_args()

    email = args.email.lower().strip()
    user = database.get_user_by_email(email)
    if not user:
        print(f"No user found for {email}", file=sys.stderr)
        sys.exit(1)

    password = args.password or generate_password()
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    hashed = hash_password(password)

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET hashed_password = %s WHERE email = %s",
            (hashed, email),
        )
        conn.commit()
        if cursor.rowcount != 1:
            print("Update failed — no row changed.", file=sys.stderr)
            sys.exit(1)
    finally:
        conn.close()

    print(f"Password reset for {email}")
    if args.password:
        print("Used the password you passed on the command line.")
    else:
        print(f"Temporary password: {password}")
        print("Send this to the user once, then ask them to change it after login if you add that later.")


if __name__ == "__main__":
    main()
