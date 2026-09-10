#!/usr/bin/env python3
"""Bake shop pack .syx files into private/packs/. Run after changing patch names or generator."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pack_generator
import shop_packs

PACK_SEEDS = {
    "m1_matrix": 41,
    "dx7_retro": 7,
    "juno_nostalgia": 106,
}


def main() -> None:
    meta_path = pack_generator.PACKS_DIR / "manifest.json"
    manifest: dict[str, dict] = {}

    for pack_id, pack in shop_packs.SHOP_PACKS.items():
        seed = PACK_SEEDS.get(pack_id, 0)
        path = pack_generator.write_pack_file(pack_id, pack["patches"], seed)
        data = path.read_bytes()
        names = pack_generator.curated_patch_names(pack_id)
        if not names:
            names = pack_generator.patch_names_from_sysex(pack_id, data)

        manifest[pack_id] = {
            "file": path.name,
            "byte_size": len(data),
            "patch_count": len(names),
            "patches": names,
            "seed": seed,
        }
        print(f"{pack_id}: {len(data)} bytes, {len(names)} patches -> {path}")

    meta_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")


if __name__ == "__main__":
    main()
