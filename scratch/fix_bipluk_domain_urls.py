"""Script to fix all invalid domain URLs missing '.com' in bipluk template & schema files.
Replaces 'https://bipluk/' with 'https://bipluk.com/'.
"""

import os
import glob

BASE_DIR = r"d:\crew\experiment"

files_to_check = []
for root, dirs, files in os.walk(BASE_DIR):
    if ".git" in root or "venv" in root or "__pycache__" in root or "scratch" in root:
        continue
    for file in files:
        if file.endswith(".html") or file.endswith(".py"):
            files_to_check.append(os.path.join(root, file))

modified_count = 0
for filepath in files_to_check:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if "https://bipluk/" in content:
            new_content = content.replace("https://bipluk/", "https://bipluk.com/")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✅ Fixed domain URLs in: {os.path.basename(filepath)}")
            modified_count += 1
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

print(f"\nTotal files updated: {modified_count}")
