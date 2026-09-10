"""Pack / unpack Yamaha DX7 155-parameter voices into 128-byte bulk format."""

from __future__ import annotations


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _write_op(out: bytearray, base: int, op: list[int]) -> None:
    """Write one operator (21 unpacked params) into 17 packed bytes."""
    out[base + 0] = _clamp(op[0], 0, 99)
    out[base + 1] = _clamp(op[1], 0, 99)
    out[base + 2] = _clamp(op[2], 0, 99)
    out[base + 3] = _clamp(op[3], 0, 99)
    out[base + 4] = _clamp(op[4], 0, 99)
    out[base + 5] = _clamp(op[5], 0, 99)
    out[base + 6] = _clamp(op[6], 0, 99)
    out[base + 7] = _clamp(op[7], 0, 99)
    out[base + 8] = _clamp(op[8], 0, 99)
    out[base + 9] = _clamp(op[9], 0, 99)
    out[base + 10] = _clamp(op[10], 0, 99)
    out[base + 11] = ((_clamp(op[12], 0, 3) & 0x7) << 3) | (_clamp(op[11], 0, 3) & 0x7)
    out[base + 12] = ((_clamp(op[20], 0, 14) & 0xF) << 3) | (_clamp(op[13], 0, 7) & 0x7)
    out[base + 13] = ((_clamp(op[15], 0, 7) & 0x7) << 2) | (_clamp(op[14], 0, 3) & 0x3)
    out[base + 14] = _clamp(op[16], 0, 99)
    out[base + 15] = ((_clamp(op[18], 0, 31) & 0x1F) << 1) | (_clamp(op[17], 0, 1) & 0x1)
    out[base + 16] = _clamp(op[19], 0, 99)


def pack_dx7_voice(params: list[int], name: str = "") -> bytes:
    """Pack 155 voice parameters (indices 0-154) into 128 bytes."""
    if len(params) < 145:
        params = list(params) + [0] * (145 - len(params))

    out = bytearray(128)
    for op_index in range(6):
        start = op_index * 21
        op = params[start : start + 21]
        if len(op) < 21:
            op = list(op) + [0] * (21 - len(op))
        _write_op(out, op_index * 17, op)

    out[102] = _clamp(params[126], 0, 99)
    out[103] = _clamp(params[127], 0, 99)
    out[104] = _clamp(params[128], 0, 99)
    out[105] = _clamp(params[129], 0, 99)
    out[106] = _clamp(params[130], 0, 99)
    out[107] = _clamp(params[131], 0, 99)
    out[108] = _clamp(params[132], 0, 99)
    out[109] = _clamp(params[133], 0, 99)
    out[110] = _clamp(params[134], 0, 31)
    out[111] = ((_clamp(params[136], 0, 1) & 0x1) << 3) | (_clamp(params[135], 0, 7) & 0x7)
    out[112] = _clamp(params[137], 0, 99)
    out[113] = _clamp(params[138], 0, 99)
    out[114] = _clamp(params[139], 0, 99)
    out[115] = _clamp(params[140], 0, 99)
    out[116] = (
        ((_clamp(params[143], 0, 7) & 0x7) << 4)
        | ((_clamp(params[142], 0, 5) & 0x7) << 1)
        | (_clamp(params[141], 0, 1) & 0x1)
    )
    out[117] = _clamp(params[144], 0, 48)

    clean_name = (name or "").upper()[:10]
    for i in range(10):
        ch = ord(clean_name[i]) if i < len(clean_name) else 0x20
        if ch < 32 or ch > 126:
            ch = 0x20
        out[118 + i] = ch

    return bytes(out)


def dx7_init_params() -> list[int]:
    """INIT VOICE II style defaults — all operators alive, neutral FM."""
    params = [0] * 155
    for op in range(6):
        base = op * 21
        params[base + 0] = 99
        params[base + 1] = 99
        params[base + 2] = 99
        params[base + 3] = 99
        params[base + 4] = 99
        params[base + 5] = 99
        params[base + 6] = 99
        params[base + 7] = 99
        params[base + 8] = 0
        params[base + 9] = 0
        params[base + 10] = 0
        params[base + 11] = 0
        params[base + 12] = 0
        params[base + 13] = 0
        params[base + 14] = 0
        params[base + 15] = 0
        params[base + 16] = 99
        params[base + 17] = 0
        params[base + 18] = 1
        params[base + 19] = 0
        params[base + 20] = 7
    params[134] = 5
    params[135] = 0
    params[136] = 0
    params[137] = 35
    params[138] = 0
    params[139] = 0
    params[140] = 0
    params[141] = 0
    params[142] = 0
    params[143] = 0
    params[144] = 24
    return params


def _set_op(params: list[int], op_num: int, **kwargs) -> None:
    """op_num 1-6 (DX7 panel numbering)."""
    base = (6 - op_num) * 21
    field_map = {
        "r1": 0, "r2": 1, "r3": 2, "r4": 3,
        "l1": 4, "l2": 5, "l3": 6, "l4": 7,
        "breakpoint": 8, "left_depth": 9, "right_depth": 10,
        "left_curve": 11, "right_curve": 12, "rate_scale": 13,
        "amp_mod": 14, "velocity": 15, "level": 16,
        "mode": 17, "coarse": 18, "fine": 19, "detune": 20,
    }
    for key, value in kwargs.items():
        if key in field_map:
            params[base + field_map[key]] = value


def build_dx7_voice(name: str, archetype: str, variation: int = 0) -> bytes:
    """Build a musical DX7 voice from a curated archetype."""
    params = dx7_init_params()
    v = variation % 4

    if archetype == "bass":
        params[134] = 6
        _set_op(params, 6, level=99, coarse=1 + v, fine=0, r1=31, r2=26, r3=20, l1=99, l2=85, l3=0, l4=0)
        _set_op(params, 5, level=78, coarse=1, fine=12 + v * 2, r1=31, r2=20, l3=0, l4=0)
        _set_op(params, 4, level=0, coarse=1)
        _set_op(params, 3, level=0, coarse=1)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)
    elif archetype == "epiano":
        params[134] = 5
        params[135] = 2
        _set_op(params, 6, level=99, coarse=1, fine=0, r1=31, r2=24, r3=18, l1=99, l2=75, l3=0, l4=0)
        _set_op(params, 5, level=85, coarse=1, fine=4, r1=31, r2=22, l3=0, l4=0)
        _set_op(params, 4, level=70, coarse=2, fine=8, r1=31, r2=20, l3=0, l4=0)
        _set_op(params, 3, level=55, coarse=3, fine=0, r1=31, r2=18, l3=0, l4=0)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)
        params[139] = 10 + v * 2
    elif archetype == "bell":
        params[134] = 1
        _set_op(params, 6, level=99, coarse=14 + v, fine=20, r1=31, r2=28, r3=25, l1=99, l2=70, l3=0, l4=0)
        _set_op(params, 5, level=88, coarse=7, fine=30, r1=31, r2=26, l3=0, l4=0)
        _set_op(params, 4, level=72, coarse=3, fine=10, r1=31, r2=24, l3=0, l4=0)
        _set_op(params, 3, level=0, coarse=1)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)
    elif archetype == "brass":
        params[134] = 11
        _set_op(params, 6, level=99, coarse=1, fine=0, r1=20, r2=18, r3=16, l1=99, l2=90, l3=70, l4=0)
        _set_op(params, 5, level=82, coarse=1, fine=2, r1=22, r2=20, l3=60, l4=0)
        _set_op(params, 4, level=68, coarse=2, fine=0, r1=24, r2=22, l3=50, l4=0)
        _set_op(params, 3, level=0, coarse=1)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)
    elif archetype == "pad":
        params[134] = 8
        params[137] = 28
        params[139] = 18 + v * 3
        _set_op(params, 6, level=92, coarse=1, fine=0, r1=45, r2=38, r3=30, l1=99, l2=85, l3=75, l4=65)
        _set_op(params, 5, level=78, coarse=1, fine=6, r1=48, r2=40, l3=70, l4=60)
        _set_op(params, 4, level=62, coarse=2, fine=4, r1=50, r2=42, l3=65, l4=55)
        _set_op(params, 3, level=0, coarse=1)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)
    elif archetype == "organ":
        params[134] = 16
        _set_op(params, 6, level=99, coarse=1, fine=0, r1=31, r2=31, r3=31, l1=99, l2=99, l3=90, l4=80)
        _set_op(params, 5, level=90, coarse=2, fine=0, r1=31, r2=31, l3=85, l4=75)
        _set_op(params, 4, level=80, coarse=3, fine=0, r1=31, r2=31, l3=80, l4=70)
        _set_op(params, 3, level=0, coarse=1)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)
    elif archetype == "lead":
        params[134] = 14
        _set_op(params, 6, level=99, coarse=1, fine=v, r1=18, r2=16, r3=14, l1=99, l2=88, l3=0, l4=0)
        _set_op(params, 5, level=84, coarse=2, fine=4, r1=20, r2=18, l3=0, l4=0)
        _set_op(params, 4, level=70, coarse=3, fine=8, r1=22, r2=20, l3=0, l4=0)
        _set_op(params, 3, level=0, coarse=1)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)
    else:  # keys / misc
        params[134] = 5
        _set_op(params, 6, level=99, coarse=1, fine=0, r1=28, r2=24, r3=20, l1=99, l2=80, l3=0, l4=0)
        _set_op(params, 5, level=72, coarse=1, fine=8 + v, r1=30, r2=26, l3=0, l4=0)
        _set_op(params, 4, level=0, coarse=1)
        _set_op(params, 3, level=0, coarse=1)
        _set_op(params, 2, level=0, coarse=1)
        _set_op(params, 1, level=0, coarse=1)

    return pack_dx7_voice(params, name)
