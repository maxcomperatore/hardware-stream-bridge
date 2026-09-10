"""Test 1-Click Demo Pack Insertion into PostgreSQL Database."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import shop_packs
import pack_generator

def test_demo_load():
    user = database.get_user_by_email("halfradiationllc@gmail.com")
    if not user:
        print("Creating mock user for testing...")
        database.create_user("halfradiationllc@gmail.com", "testpass123")
        user = database.get_user_by_email("halfradiationllc@gmail.com")

    uid = user["id"]
    print(f"User ID: {uid} ({user['email']})")

    pack = shop_packs.SHOP_PACKS["dx7_retro"]
    data = pack_generator.generate_pack_bytes(pack["id"], patch_names=pack["patches"], seed=pack.get("seed", 0))
    bank_name = f"{pack['name']} (Factory Demo)"

    bank_id = database.save_bank(
        name=bank_name,
        synth_model=pack["synth"],
        sysex_hex=data.hex(),
        patch_names=pack["patches"],
        user_id=uid
    )
    print(f"✅ Demo Bank Loaded into DB! Bank ID: {bank_id}")

    banks = database.get_all_banks(uid)
    print(f"📊 User Vault now contains {len(banks)} banks.")
    for b in banks:
        print(f"   - [{b['id']}] {b['name']} ({b['synth_model']}) -> {b.get('patch_count', 0)} patches")

if __name__ == "__main__":
    test_demo_load()
