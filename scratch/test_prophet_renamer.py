import re

def unescape_sequential(sysex: bytes) -> bytes:
    result = bytearray()
    dataIndex = 0
    while dataIndex < len(sysex):
        msbits = sysex[dataIndex]
        dataIndex += 1
        for i in range(7):
            if dataIndex < len(sysex):
                result.append(sysex[dataIndex] | ((msbits & (1 << i)) << (7 - i)))
            dataIndex += 1
    return bytes(result)

def escape_sequential(data: bytes) -> bytes:
    result = bytearray()
    idx = 0
    while idx < len(data):
        chunk = data[idx:idx+7]
        idx += 7
        msbits = 0
        body = bytearray()
        for i, b in enumerate(chunk):
            if b & 0x80:
                msbits |= (1 << i)
            body.append(b & 0x7F)
        result.append(msbits)
        result.extend(body)
    return bytes(result)

# Test roundtrip
test_data = b"Hello World! This is a test string for Prophet-5 8-to-7 packing."
escaped = escape_sequential(test_data)
unescaped = unescape_sequential(escaped)
assert test_data == unescaped, f"Mismatch: {test_data} != {unescaped}"
print("Roundtrip 8-to-7 packing test PASSED!")

def prophet_slot_label(index: int) -> str:
    """Returns 11..18, 21..28, up to 58 (5 banks of 8 programs)."""
    group = (index // 8) + 1
    slot = (index % 8) + 1
    return f"{group}{slot}"

print("Slot labels test:")
print([prophet_slot_label(i) for i in range(40)])
