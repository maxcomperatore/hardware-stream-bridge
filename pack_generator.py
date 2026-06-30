"""Generate structurally valid SysEx banks for shop packs (no hardware required)."""

from __future__ import annotations

import random
import re
from pathlib import Path

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


def _dx7_voice_params(category: str, rng: random.Random) -> list[int]:
    params = [rng.randint(0, 127) for _ in range(118)]

    if category == "bass":
        for i in range(0, 40, 4):
            params[i] = rng.randint(0, 35)
        params[16] = rng.randint(90, 127)
        params[17] = rng.randint(0, 20)
    elif category == "pad":
        for i in range(60, 90):
            params[i] = rng.randint(70, 127)
        params[17] = rng.randint(80, 127)
        params[18] = rng.randint(70, 120)
    elif category == "bell":
        for i in range(20, 60, 3):
            params[i] = rng.randint(80, 127)
        params[11] = rng.randint(90, 127)
    elif category == "brass":
        params[5] = rng.randint(70, 110)
        params[6] = rng.randint(40, 80)
        params[16] = rng.randint(85, 127)
    elif category == "keys":
        params[0] = rng.randint(50, 90)
        params[1] = rng.randint(40, 80)
        params[17] = rng.randint(30, 70)
    else:
        for i in range(0, 118, 7):
            params[i] = rng.randint(20, 100)

    return params


def _guess_dx7_category(name: str) -> str:
    upper = name.upper()
    if any(k in upper for k in ("BASS", "SUB", "DIGI")):
        return "bass"
    if any(k in upper for k in ("PAD", "ATMOS", "WIND", "CHOIR", "SPACE", "NIGHT")):
        return "pad"
    if any(k in upper for k in ("BELL", "CHIME", "CRYSTAL", "GLASS")):
        return "bell"
    if any(k in upper for k in ("BRASS", "HORN", "STAB")):
        return "brass"
    if any(k in upper for k in ("PIANO", "RHODES", "EP", "KEY", "ORG", "CLAV")):
        return "keys"
    return "lead"


def generate_dx7_bulk(patch_names: list[str], seed: int = 0) -> bytes:
    rng = random.Random(seed)
    data = bytearray(4104)
    data[0:6] = bytes([0xF0, 0x43, 0x00, 0x09, 0x20, 0x00])

    for i, raw_name in enumerate(patch_names[:32]):
        voice_offset = 6 + (i * 128)
        category = _guess_dx7_category(raw_name)
        params = _dx7_voice_params(category, rng)
        data[voice_offset : voice_offset + 118] = bytes(params)
        name = _fit_name(raw_name, 10).encode("ascii", errors="ignore")
        data[voice_offset + 118 : voice_offset + 128] = name[:10].ljust(10, b" ")

    data[4102] = _dx7_checksum(data, 6, 4102)
    data[4103] = 0xF7
    return bytes(data)


def _juno_params(category: str, rng: random.Random) -> tuple[list[int], int, int]:
    """16 slider bytes + sw1 + sw2."""
    sliders = [rng.randint(0, 127) for _ in range(16)]
    sw1 = 0
    sw2 = 0

    if category == "bass":
        sliders[5] = rng.randint(10, 45)
        sliders[6] = rng.randint(70, 127)
        sliders[11] = rng.randint(0, 20)
        sliders[14] = rng.randint(20, 60)
        sliders[15] = rng.randint(60, 127)
    elif category == "pad":
        sliders[5] = rng.randint(55, 95)
        sliders[11] = rng.randint(70, 127)
        sliders[13] = rng.randint(80, 127)
        sliders[14] = rng.randint(70, 127)
        sliders[4] = rng.randint(0, 50)
        sw2 = 0x01
    elif category == "pluck":
        sliders[5] = rng.randint(50, 100)
        sliders[11] = rng.randint(0, 15)
        sliders[13] = rng.randint(0, 25)
        sliders[14] = rng.randint(70, 127)
    elif category == "brass":
        sliders[5] = rng.randint(75, 127)
        sliders[6] = rng.randint(45, 90)
        sliders[11] = rng.randint(0, 25)
    elif category == "lead":
        sliders[5] = rng.randint(80, 127)
        sliders[6] = rng.randint(55, 110)
        sliders[11] = rng.randint(0, 30)
    else:
        sliders[5] = rng.randint(40, 100)
        sliders[6] = rng.randint(20, 90)

    return sliders, sw1, sw2


def _guess_juno_category(name: str) -> str:
    upper = name.upper()
    if "BASS" in upper or "SUB" in upper:
        return "bass"
    if "PAD" in upper or "NOSTALG" in upper or "WIND" in upper or "DRIFT" in upper:
        return "pad"
    if "PLUCK" in upper:
        return "pluck"
    if "BRASS" in upper or "CHORUS" in upper:
        return "brass"
    if "LEAD" in upper:
        return "lead"
    return "poly"


def generate_juno106_bulk(patch_names: list[str], seed: int = 0, count: int = 128) -> bytes:
    """128 individual APR messages (Roland Juno-106 patch dump stream)."""
    rng = random.Random(seed)
    out = bytearray()

    for patch_num in range(count):
        name = patch_names[patch_num] if patch_num < len(patch_names) else f"Patch {patch_num + 1}"
        category = _guess_juno_category(name)
        sliders, sw1, sw2 = _juno_params(category, rng)
        channel = 0x00
        msg = bytearray([0xF0, 0x41, 0x36, channel, 0x35, patch_num & 0x7F])
        msg.extend(sliders)
        msg.extend([sw1 & 0x7F, sw2 & 0x7F, 0xF7])
        out.extend(msg)

    return bytes(out)


def _m1_embed_name(block: bytearray, name: str) -> None:
    clean = _fit_name(name, 10)
    chars = clean.encode("ascii", errors="ignore")[:10]
    padded = chars.ljust(10, b" ")
    block[153:160] = padded[0:7]
    block[161:164] = padded[7:10]


def generate_m1_bulk(patch_names: list[str], seed: int = 0, count: int = 32) -> bytes:
    """32-program Korg M1 bulk dump (short bank for shop packs)."""
    rng = random.Random(seed)
    prog_size = 164
    body_len = count * prog_size
    data = bytearray(6 + body_len + 2)
    data[0:4] = bytes([0xF0, 0x42, 0x30, 0x19])
    data[4] = (body_len >> 7) & 0x7F
    data[5] = body_len & 0x7F

    for i in range(count):
        offset = 6 + (i * prog_size)
        block = bytearray(prog_size)
        category = _guess_dx7_category(patch_names[i] if i < len(patch_names) else "M1 PROG")
        for j in range(133):
            if category == "bass":
                block[j] = rng.randint(0, 50) if j % 5 == 0 else rng.randint(0, 127)
            elif category == "pad":
                block[j] = rng.randint(60, 127) if j % 4 == 0 else rng.randint(0, 127)
            else:
                block[j] = rng.randint(0, 127)
        name = patch_names[i] if i < len(patch_names) else f"M1 Voice {i + 1:02d}"
        _m1_embed_name(block, name)
        data[offset : offset + prog_size] = block

    checksum_index = 6 + body_len
    data[checksum_index] = _korg_checksum(data, 6, checksum_index)
    data[checksum_index + 1] = 0xF7
    return bytes(data)


def patch_names_from_sysex(pack_id: str, data: bytes) -> list[str]:
    import parser

    if pack_id == "dx7_retro":
        return parser.parse_dx7_sysex(data) or []
    if pack_id == "juno_nostalgia":
        return parser.parse_juno106_sysex(data) or []
    if pack_id == "m1_matrix":
        return parser.parse_korg_m1_sysex(data) or []
    return []


def generate_pack_bytes(pack_id: str, patch_names: list[str], seed: int) -> bytes:
    if pack_id == "dx7_retro":
        return generate_dx7_bulk(patch_names, seed)
    if pack_id == "juno_nostalgia":
        names = patch_names[:128]
        while len(names) < 128:
            names.append(f"Juno Voice {len(names) + 1:03d}")
        return generate_juno106_bulk(names, seed, count=128)
    if pack_id == "m1_matrix":
        return generate_m1_bulk(patch_names, seed, count=32)
    raise ValueError(f"Unknown pack: {pack_id}")


def write_pack_file(pack_id: str, patch_names: list[str], seed: int) -> Path:
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
