"""Digital sound expansion packs for the Monster Shop."""

import json
from pathlib import Path

import pack_generator

PACKS_DIR = pack_generator.PACKS_DIR
MANIFEST_PATH = PACKS_DIR / "manifest.json"

SHOP_PACKS: dict[str, dict] = {
    "m1_matrix": {
        "id": "m1_matrix",
        "name": "Korg M1: Off the Matrix",
        "synth": "Korg M1",
        "price_cents": 900,
        "price_display": "$9.00",
        "description": "Sample-keymap style programs with house pianos, pads, and basses. 32 curated programs.",
        "patches_count": 32,
        "demo_patches": ["Cyber Gate", "HousePiano", "Ethereal", "TridentStr", "Glassy Pad", "Obese Poly"],
        "patches": [
            "Cyber Gate", "HousePiano", "Ethereal", "TridentStr", "Glassy Pad", "Obese Poly",
            "Karimba!", "Narnia", "Matrix Pad", "Analog Str", "Deep House", "Crystal",
            "Warm Brass", "Soft Choir", "Power Bass", "Night Drive", "Glass Keys", "Echo Bell",
            "Soft Wind", "Metal Hit", "Slow Wave", "Bright EP", "Dark Pad", "Pulse Bass",
            "Soft Flute", "Hard Stab", "Wide Pad", "Low Drone", "Spark Lead", "Soft Organ",
            "Chorus EP", "Final Hit",
        ],
        "spec_label": "M1 // KORG MATRIX",
        "seed": 41,
    },
    "dx7_retro": {
        "id": "dx7_retro",
        "name": "Yamaha DX7: Classic FM Leads & Basses",
        "synth": "Yamaha DX7",
        "price_cents": 900,
        "price_display": "$9.00",
        "description": "Punchy FM basses, bell leads, and electric pianos. 32 curated DX7 voices.",
        "patches_count": 32,
        "demo_patches": ["Super Bass", "Chime Bell", "FM Rhodes", "Synth Brass", "Sitar Glide", "Atmosphere"],
        "patches": [
            "Super Bass", "Chime Bell", "FM Rhodes", "Synth Brass", "Sitar Glide", "Atmosphere",
            "Digi Bass", "Church Org", "Glass EP", "Power Lead", "Soft Pad", "Metal Key",
            "Deep FM", "Bright Bell", "Warm Bass", "Space Pad", "Hard Edge", "Soft Flute",
            "Euro Bass", "Crystal", "Dark Wire", "Soft Horn", "Pulse FM", "Low Stack",
            "Glass Hit", "Slow Dusk", "Bright Stab", "Wide FM", "Echo Pad", "Sub Drive",
            "Soft Air", "Final DX",
        ],
        "spec_label": "DX7 // YAMAHA FM",
        "seed": 7,
    },
    "juno_nostalgia": {
        "id": "juno_nostalgia",
        "name": "Roland Juno-106: Nostalgia Plucks & Pads",
        "synth": "Roland Juno-106",
        "price_cents": 900,
        "price_display": "$9.00",
        "description": "Chorus pads, plucks, acid bass, and leads. Full 128-patch Juno bank.",
        "patches_count": 128,
        "demo_patches": ["Nostalgia", "Chorused Pad", "Snap Pluck", "Space Wind", "Analog Sweep", "Sub Bass"],
        "patches": [
            "Nostalgia", "Chorused Pad", "Snap Pluck", "Space Wind", "Analog Sweep", "Sub Bass",
            "Euro Bass", "PPG Wave", "Soft Glow", "Bright Juno", "Deep Pad", "Glass Pluck",
            "Warm Bass", "Slow Drift", "Hard Stab", "Soft Air", "Chorus Str", "Low Pulse",
            "Bright Lead", "Dark Pad", "Soft Keys", "Wide Juno", "Echo Pad", "Sub Drive",
            "Soft Hit", "Slow Wave", "Power Pad", "Night Bass", "Glass Sweep", "Soft Choir",
            "Final Juno", "Last Pad",
        ],
        "spec_label": "JUNO // ROLAND CHORUS",
        "seed": 106,
    },
}


def _load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_pack_sysex_hex(pack_id: str) -> str:
    cached = pack_generator.load_pack_hex(pack_id)
    if cached:
        return cached
    pack = get_shop_pack(pack_id)
    if not pack:
        raise ValueError(f"Unknown pack: {pack_id}")
    data = pack_generator.generate_pack_bytes(pack_id, pack["patches"], pack.get("seed", 0))
    return data.hex()


def get_pack_patch_names(pack_id: str) -> list[str]:
    manifest = _load_manifest()
    if pack_id in manifest and manifest[pack_id].get("patches"):
        return manifest[pack_id]["patches"]
    curated = pack_generator.curated_patch_names(pack_id)
    if curated:
        return curated
    pack = get_shop_pack(pack_id)
    if not pack:
        return []
    try:
        data = bytes.fromhex(get_pack_sysex_hex(pack_id))
        names = pack_generator.patch_names_from_sysex(pack_id, data)
        if names:
            return names
    except (ValueError, TypeError):
        pass
    return pack["patches"]


def list_shop_packs() -> list[dict]:
    return list(SHOP_PACKS.values())


def packs_for_template() -> list[dict]:
    packs = []
    for pack in list_shop_packs():
        patch_names = get_pack_patch_names(pack["id"])
        packs.append({
            "id": pack["id"],
            "name": pack["name"],
            "synth": pack["synth"],
            "price": pack["price_display"],
            "price_cents": pack["price_cents"],
            "description": pack["description"],
            "patches_count": len(patch_names) or pack["patches_count"],
            "demo_patches": pack["demo_patches"],
            "spec_label": pack["spec_label"],
            "slug": f"{pack['id']}.bank",
            "is_new": pack["id"] == "m1_matrix",
            "footnote": "Delivers to your vault instantly after checkout. Transmit to your synth via Web MIDI. No DAW required.",
            "available": "Instant",
        })
    return packs


def get_shop_pack(pack_id: str) -> dict | None:
    return SHOP_PACKS.get(pack_id)


def pack_bank_name(pack: dict) -> str:
    return f"{pack['name']} (Shop)"


def user_owns_pack(user_id: int, pack_id: str) -> bool:
    import database

    pack = get_shop_pack(pack_id)
    if not pack:
        return False
    target = pack_bank_name(pack)
    for bank in database.get_all_banks(user_id):
        if bank.get("name") == target:
            return True
    return False


def fulfill_sound_pack(email: str, pack_id: str) -> int | None:
    import database

    pack = get_shop_pack(pack_id)
    if not pack:
        return None
    user = database.get_user_by_email(email)
    if not user:
        return None
    if user_owns_pack(user["id"], pack_id):
        return None
    return database.save_bank(
        pack_bank_name(pack),
        pack["synth"],
        get_pack_sysex_hex(pack_id),
        get_pack_patch_names(pack_id),
        user["id"],
    )
