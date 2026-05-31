import re

def clean_ascii(name_bytes: bytes) -> str:
    """Convert bytes to a clean ASCII string, replacing non-printable chars."""
    chars = []
    for b in name_bytes:
        # DX7 uses standard ASCII but sometimes has special chars or upper/lower ranges
        if 32 <= b <= 126:
            chars.append(chr(b))
        else:
            chars.append(' ')
    return "".join(chars).strip()

def parse_dx7_sysex(data: bytes) -> list[str]:
    """
    Parses a Yamaha DX7 32-voice bulk dump.
    Standard dump size is 4104 bytes:
      - 0: F0 (SysEx Start)
      - 1: 43 (Yamaha Manufacturer ID)
      - 2: Sub-status/Channel (usually 00-0F, or 09 for classification status)
      - 3: 09 (Format classification: 32 voices)
      - 4-5: Byte count MSB/LSB (usually 0x20, 0x00 = 4096 bytes)
      - 6 to 4101: 32 voices * 128 bytes each = 4096 bytes
      - 4102: Checksum
      - 4103: F7 (SysEx End)
    """
    # Check if this matches a DX7 32-voice bulk dump structure
    # We can be slightly lenient on length because some dumps strip F0/F7 or have extra headers
    voices = []
    
    # Standard format: starts with F0 43, length is ~4104
    if len(data) >= 4100 and data[0] == 0xF0 and data[1] == 0x43:
        # DX7 bulk dump voice data starts at offset 6
        start_offset = 6
    elif len(data) == 4096:
        # Raw voice data dump
        start_offset = 0
    else:
        # Let's search for the DX7 header F0 43 [chan] 09 20 00 inside the data
        header_index = data.find(b'\xF0\x43')
        if header_index != -1 and header_index + 6 < len(data) and data[header_index + 3] == 0x09:
            start_offset = header_index + 6
        else:
            return []

    for i in range(32):
        voice_offset = start_offset + (i * 128)
        if voice_offset + 128 <= len(data):
            # DX7 patch name is stored in the last 10 bytes of the 128-byte voice structure
            name_offset = voice_offset + 118
            name_bytes = data[name_offset:name_offset + 10]
            patch_name = clean_ascii(name_bytes)
            # If name is completely empty or junk, give it a default
            if not patch_name:
                patch_name = f"DX7 Voice {i+1:02d}"
            voices.append(patch_name)
            
    return voices

def parse_generic_sysex(data: bytes) -> list[str]:
    """
    Scans SysEx data for blocks of printable ASCII text.
    Many synths store patch names in ASCII sequences.
    """
    # Fallback to DX7 parser if it looks like one
    dx7_patches = parse_dx7_sysex(data)
    if dx7_patches:
        return dx7_patches

    # Find printable ASCII segments of length 6 to 16
    # Keep it simple: look for continuous blocks of ASCII chars
    patches = []
    temp_name = []
    
    # We scan bytes and accumulate printable characters
    for b in data:
        if 32 <= b <= 126:
            temp_name.append(chr(b))
        else:
            if len(temp_name) >= 6 and len(temp_name) <= 16:
                name = "".join(temp_name).strip()
                # Exclude strings that are just spaces or symbols
                if re.match(r'^[A-Za-z0-9\s\-\.\_\+\*\/]{4,}$', name):
                    patches.append(name)
            temp_name = []
            
    # If we extracted between 8 and 128 reasonable names, return them
    if 8 <= len(patches) <= 128:
        return patches
        
    # Otherwise, return generic names
    return [f"Patch {i+1:02d}" for i in range(32)]
