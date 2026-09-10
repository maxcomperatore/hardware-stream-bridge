"""Generate structurally valid, musically curated SysEx banks for shop packs."""

from __future__ import annotations

import re
from pathlib import Path

import pack_recipes

PACKS_DIR = Path(__file__).resolve().parent / "private" / "packs"


def _dx7_checksum(data: bytearray, start: int, end: int) -> int:
    total = sum(data[start:end]) & 0x7F
    return (-total) & 0x7F


def _korg_checksum(data: bytearray, start: int, end: int) -> int:
    total = sum(data[i] & 0x7F for i in range(start, end)) & 0x7F
    return (-total) & 0x7F


def _fit_name(name: str, width: int) -> str:
    clean = re.sub(r"[^A-Za-z0-9 \-]", "", name.upper()).strip()
    return clean[:width].ljust(width)


def generate_dx7_bulk(patch_names: list[str] | None = None, seed: int = 0) -> bytes:
    del patch_names, seed
    data = bytearray(4104)
    data[0:6] = bytes([0xF0, 0x43, 0x00, 0x09, 0x20, 0x00])
    for i in range(32):
        voice = pack_recipes.dx7_voice_for_slot(i)
        data[6 + i * 128 : 6 + (i + 1) * 128] = voice
    data[4102] = _dx7_checksum(data, 6, 4102)
    data[4103] = 0xF7
    return bytes(data)


def generate_juno106_bulk(patch_names: list[str] | None = None, seed: int = 0, count: int = 128) -> bytes:
    del patch_names, seed
    out = bytearray()
    for patch_num in range(count):
        sliders, sw1, sw2 = pack_recipes.juno_recipe_for_slot(patch_num)
        msg = bytearray([0xF0, 0x41, 0x36, 0x00, 0x35, patch_num & 0x7F])
        msg.extend(sliders)
        msg.extend([sw1 & 0x7F, sw2 & 0x7F, 0xF7])
        out.extend(msg)
    return bytes(out)


def generate_m1_bulk(patch_names: list[str] | None = None, seed: int = 0, count: int = 32) -> bytes:
    del patch_names, seed
    prog_size = 164
    body_len = count * prog_size
    data = bytearray(6 + body_len + 2)
    data[0:4] = bytes([0xF0, 0x42, 0x30, 0x19])
    data[4] = (body_len >> 7) & 0x7F
    data[5] = body_len & 0x7F
    for i in range(count):
        offset = 6 + (i * prog_size)
        data[offset : offset + prog_size] = pack_recipes.m1_program_for_slot(i)
    checksum_index = 6 + body_len
    data[checksum_index] = _korg_checksum(data, 6, checksum_index)
    data[checksum_index + 1] = 0xF7
    return bytes(data)


def patch_names_from_sysex(pack_id: str, data: bytes) -> list[str]:
    import parser

    if pack_id == "dx7_retro":
        return parser.parse_dx7_sysex(data) or []
    if pack_id == "juno_nostalgia":
        return pack_recipes.juno_patch_names()
    if pack_id == "m1_matrix":
        return parser.parse_korg_m1_sysex(data) or []
    return []


def curated_patch_names(pack_id: str) -> list[str]:
    if pack_id == "dx7_retro":
        return [name for name, _ in pack_recipes.DX7_PACK_LAYOUT]
    if pack_id == "m1_matrix":
        return [name for name, _ in pack_recipes.M1_PACK_LAYOUT]
    if pack_id == "juno_nostalgia":
        return pack_recipes.juno_patch_names()
    return []


def generate_pack_bytes(pack_id: str, patch_names: list[str] | None = None, seed: int = 0) -> bytes:
    if pack_id == "dx7_retro":
        return generate_dx7_bulk(patch_names, seed)
    if pack_id == "juno_nostalgia":
        return generate_juno106_bulk(patch_names, seed, count=128)
    if pack_id == "m1_matrix":
        return generate_m1_bulk(patch_names, seed, count=32)
    raise ValueError(f"Unknown pack: {pack_id}")


def write_pack_file(pack_id: str, patch_names: list[str] | None = None, seed: int = 0) -> Path:
    PACKS_DIR.mkdir(parents=True, exist_ok=True)
    data = generate_pack_bytes(pack_id, patch_names, seed)
    path = PACKS_DIR / f"{pack_id}.syx"
    path.write_bytes(data)
    return path


def load_pack_hex(pack_id: str) -> str | None:
    path = PACKS_DIR / f"{pack_id}.syx"
    if path.is_file():
        return path.read_bytes().hex()
    return None
