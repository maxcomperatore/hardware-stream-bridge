"""Curated patch recipes for shop SysEx packs."""

from __future__ import annotations

from dx7_pack import build_dx7_voice

# Juno-106 APR sliders (16) + sw1 + sw2
# Order: LFO rate, LFO delay, DCO LFO, DCO PWM, PWM rate/noise, VCF cutoff,
#        VCF res, VCF env, VCF LFO, VCF key, VCA, A, D, S, R, sub level

JUNO_SW1_OFF = 0x00
JUNO_SW1_SAW = 0x20
JUNO_SW1_PULSE = 0x40
JUNO_SW2_OFF = 0x00
JUNO_SW2_CHORUS_I = 0x01
JUNO_SW2_CHORUS_II = 0x02


def _juno(sliders: tuple[int, ...], sw1: int = JUNO_SW1_SAW, sw2: int = JUNO_SW2_CHORUS_I) -> tuple[tuple[int, ...], int, int]:
    return sliders, sw1, sw2


JUNO_ARCHETYPES: dict[str, tuple[tuple[int, ...], int, int]] = {
    "acid_bass": _juno((0, 0, 0, 0, 0, 28, 118, 72, 0, 40, 100, 0, 18, 100, 12, 0), JUNO_SW1_SAW, JUNO_SW2_OFF),
    "sub_bass": _juno((0, 0, 0, 0, 0, 22, 40, 55, 0, 30, 100, 0, 20, 100, 8, 110), JUNO_SW1_SAW, JUNO_SW2_OFF),
    "warm_pad": _juno((18, 20, 12, 0, 0, 62, 18, 48, 8, 55, 95, 55, 40, 88, 72, 0), JUNO_SW1_SAW, JUNO_SW2_CHORUS_II),
    "chorus_pad": _juno((22, 25, 15, 0, 0, 58, 22, 52, 10, 50, 92, 60, 45, 85, 78, 0), JUNO_SW1_SAW, JUNO_SW2_CHORUS_II),
    "pluck": _juno((0, 0, 0, 0, 0, 88, 12, 65, 0, 60, 100, 0, 28, 0, 55, 0), JUNO_SW1_PULSE, JUNO_SW2_OFF),
    "brass": _juno((0, 0, 0, 0, 0, 78, 35, 70, 0, 45, 100, 5, 22, 90, 35, 0), JUNO_SW1_SAW, JUNO_SW2_CHORUS_I),
    "reso_lead": _juno((8, 0, 8, 0, 0, 95, 95, 80, 12, 70, 100, 0, 16, 75, 40, 0), JUNO_SW1_SAW, JUNO_SW2_OFF),
    "poly": _juno((10, 0, 6, 0, 0, 70, 28, 45, 6, 50, 95, 8, 30, 80, 45, 20), JUNO_SW1_SAW, JUNO_SW2_CHORUS_I),
    "organ": _juno((0, 0, 0, 0, 0, 55, 10, 20, 0, 35, 100, 0, 10, 100, 20, 0), JUNO_SW1_PULSE, JUNO_SW2_CHORUS_I),
    "strings": _juno((14, 18, 10, 0, 0, 52, 15, 55, 12, 48, 90, 48, 38, 92, 80, 0), JUNO_SW1_SAW, JUNO_SW2_CHORUS_II),
    "wind": _juno((20, 30, 18, 0, 55, 48, 8, 40, 20, 40, 85, 70, 50, 75, 90, 0), JUNO_SW1_SAW, JUNO_SW2_CHORUS_I),
    "bell": _juno((0, 0, 0, 0, 0, 92, 5, 75, 0, 65, 100, 0, 8, 0, 70, 0), JUNO_SW1_PULSE, JUNO_SW2_OFF),
}

# 128 slots: archetype key per patch (A11..B88)
JUNO_BANK_LAYOUT: list[str] = (
    ["warm_pad", "chorus_pad", "pluck", "strings", "poly", "acid_bass", "sub_bass", "wind"] * 8
    + ["reso_lead", "poly", "warm_pad", "pluck", "acid_bass", "chorus_pad", "sub_bass", "wind"] * 8
)

DX7_PACK_LAYOUT: list[tuple[str, str]] = [
    ("Super Bass", "bass"),
    ("Chime Bell", "bell"),
    ("FM Rhodes", "epiano"),
    ("Synth Brass", "brass"),
    ("Sitar Glide", "lead"),
    ("Atmosphere", "pad"),
    ("Digi Bass", "bass"),
    ("Church Org", "organ"),
    ("Glass EP", "epiano"),
    ("Power Lead", "lead"),
    ("Soft Pad", "pad"),
    ("Metal Key", "bell"),
    ("Deep FM", "bass"),
    ("Bright Bell", "bell"),
    ("Warm Bass", "bass"),
    ("Space Pad", "pad"),
    ("Hard Edge", "lead"),
    ("Soft Flute", "pad"),
    ("Euro Bass", "bass"),
    ("Crystal", "bell"),
    ("Dark Wire", "lead"),
    ("Soft Horn", "brass"),
    ("Pulse FM", "keys"),
    ("Low Stack", "bass"),
    ("Glass Hit", "bell"),
    ("Slow Dusk", "pad"),
    ("Bright Stab", "brass"),
    ("Wide FM", "keys"),
    ("Echo Pad", "pad"),
    ("Sub Drive", "bass"),
    ("Soft Air", "pad"),
    ("Final DX", "keys"),
]

M1_PACK_LAYOUT: list[tuple[str, str]] = [
    ("Cyber Gate", "house"),
    ("HousePiano", "piano"),
    ("Ethereal", "pad"),
    ("TridentStr", "strings"),
    ("Glassy Pad", "pad"),
    ("Obese Poly", "poly"),
    ("Karimba!", "bell"),
    ("Narnia", "fantasy"),
    ("Matrix Pad", "pad"),
    ("Analog Str", "strings"),
    ("Deep House", "house"),
    ("Crystal", "bell"),
    ("Warm Brass", "brass"),
    ("Soft Choir", "choir"),
    ("Power Bass", "bass"),
    ("Night Drive", "bass"),
    ("Glass Keys", "keys"),
    ("Echo Bell", "bell"),
    ("Soft Wind", "pad"),
    ("Metal Hit", "fx"),
    ("Slow Wave", "pad"),
    ("Bright EP", "piano"),
    ("Dark Pad", "pad"),
    ("Pulse Bass", "bass"),
    ("Soft Flute", "wind"),
    ("Hard Stab", "brass"),
    ("Wide Pad", "pad"),
    ("Low Drone", "bass"),
    ("Spark Lead", "lead"),
    ("Soft Organ", "organ"),
    ("Chorus EP", "piano"),
    ("Final Hit", "fx"),
]


def _m1_base_program() -> bytearray:
    """Factory-style M1 program skeleton referencing ROM multisamples."""
    block = bytearray(164)
    # Bend / modulation defaults
    block[0] = 2
    block[1] = 12
    block[2] = 0
    block[3] = 0
    # Oscillator A on, level high
    block[8] = 99
    block[9] = 0
    block[10] = 0
    block[11] = 0
    # TVF / TVA neutral musical defaults
    block[24] = 80
    block[25] = 20
    block[26] = 60
    block[27] = 40
    block[28] = 70
    block[29] = 90
    block[30] = 50
    block[31] = 30
    block[32] = 80
    block[33] = 60
    return block


def _apply_m1_archetype(block: bytearray, archetype: str, variation: int) -> None:
    v = variation % 4
    # ROM wave indices (approximate factory multisample slots)
    waves = {
        "piano": (0, 1),
        "house": (1, 12),
        "pad": (18, 19),
        "strings": (14, 15),
        "bell": (22, 23),
        "brass": (16, 17),
        "bass": (8, 9),
        "organ": (4, 5),
        "choir": (20, 21),
        "wind": (24, 25),
        "poly": (6, 7),
        "lead": (10, 11),
        "fantasy": (26, 27),
        "keys": (2, 3),
        "fx": (28, 29),
    }
    w1, w2 = waves.get(archetype, (0, 1))
    block[9] = (w1 + v) & 0x7F
    block[10] = w2 & 0x7F
    block[11] = 40 + v * 8

    if archetype in ("bass", "house"):
        block[24] = 35 + v * 4
        block[25] = 55
        block[28] = 20
        block[29] = 95
        block[32] = 30
        block[33] = 20
    elif archetype in ("pad", "choir", "wind", "fantasy"):
        block[24] = 70 + v * 3
        block[25] = 10
        block[28] = 55
        block[29] = 85
        block[32] = 75
        block[33] = 65
    elif archetype in ("piano", "keys", "house"):
        block[24] = 85
        block[25] = 8
        block[28] = 5
        block[29] = 90
        block[32] = 40
        block[33] = 35
    elif archetype in ("bell", "fx"):
        block[24] = 92
        block[25] = 5
        block[28] = 0
        block[29] = 70
        block[32] = 15
        block[33] = 10
    elif archetype == "brass":
        block[24] = 78
        block[25] = 25
        block[28] = 8
        block[29] = 92
        block[32] = 45
        block[33] = 30
    elif archetype == "strings":
        block[24] = 68
        block[25] = 12
        block[28] = 40
        block[29] = 88
        block[32] = 70
        block[33] = 60
    elif archetype == "organ":
        block[24] = 60
        block[25] = 0
        block[28] = 0
        block[29] = 100
        block[32] = 50
        block[33] = 45
    elif archetype == "lead":
        block[24] = 88
        block[25] = 30
        block[28] = 2
        block[29] = 88
        block[32] = 25
        block[33] = 15


def build_m1_program(name: str, archetype: str, variation: int = 0) -> bytes:
    block = _m1_base_program()
    _apply_m1_archetype(block, archetype, variation)
    clean = name.upper()[:10]
    chars = clean.encode("ascii", errors="ignore")[:10].ljust(10, b" ")
    block[153:160] = chars[0:7]
    block[161:164] = chars[7:10]
    return bytes(block)


def juno_recipe_for_slot(slot: int) -> tuple[tuple[int, ...], int, int]:
    archetype = JUNO_BANK_LAYOUT[slot % len(JUNO_BANK_LAYOUT)]
    sliders, sw1, sw2 = JUNO_ARCHETYPES[archetype]
    s = list(sliders)
    s[5] = max(0, min(127, s[5] + (slot % 5) - 2))
    s[11] = max(0, min(127, s[11] + (slot % 3)))
    s[13] = max(0, min(127, s[13] + (slot % 4) - 1))
    return tuple(s), sw1, sw2


def dx7_voice_for_slot(slot: int) -> bytes:
    name, archetype = DX7_PACK_LAYOUT[slot]
    return build_dx7_voice(name, archetype, variation=slot)


def m1_program_for_slot(slot: int) -> bytes:
    name, archetype = M1_PACK_LAYOUT[slot]
    return build_m1_program(name, archetype, variation=slot)


def juno_patch_names() -> list[str]:
    names = []
    for i in range(128):
        group = "A" if i < 64 else "B"
        local = i % 64
        bank = (local // 8) + 1
        patch = (local % 8) + 1
        archetype = JUNO_BANK_LAYOUT[i % len(JUNO_BANK_LAYOUT)]
        label = archetype.replace("_", " ").title()
        names.append(f"{group}{bank}{patch} {label}")
    return names
