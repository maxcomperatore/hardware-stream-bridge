#!/usr/bin/env python3
import os
import re

RIGLUK_DIR = r"d:\crew\experiment\rigluk"

REPLACEMENTS = [
    ("bipluk gang", "rigluk gang"),
    ("support@bipluk.com", "support@rigluk.com"),
    ("bipluk.com", "rigluk.com"),
    ("bipluk+", "rigluk+"),
    ("bipluk", "rigluk"),
    ("Bipluk", "Rigluk"),
    ("BIPLUK", "RIGLUK"),
]

EXCLUDE_DIRS = {".git", "venv", "__pycache__", "scratch"}
EXCLUDE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".avif", ".pyc"}

def rebrand():
    changed_count = 0
    for root, dirs, files in os.walk(RIGLUK_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXCLUDE_EXTS:
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                
                new_content = content
                for old_str, new_str in REPLACEMENTS:
                    new_content = new_content.replace(old_str, new_str)
                
                if new_content != content:
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(new_content)
                    changed_count += 1
                    print(f"Rebranded: {path}")
            except Exception as e:
                print(f"Error processing {path}: {e}")
    print(f"Total files rebranded: {changed_count}")

if __name__ == "__main__":
    rebrand()
