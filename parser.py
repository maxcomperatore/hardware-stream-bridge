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

def parse_juno106_sysex(data: bytes) -> list[str]:
    """
    Parses Roland Juno-106 Sysex patch parameters.
    Since Juno-106 patches have no digital name tags, we analyze VCF, DCO, VCA,
    and envelope parameters to dynamically generate descriptive name tags (e.g., 'A11 ACID BASS').
    """
    patches = []
    
    # Juno-106 patch parameters are typically 34 bytes
    # If the length of the file matches exactly 128 patches * 34 bytes
    if len(data) == 4352:
        for i in range(128):
            offset = i * 34
            if offset + 34 <= len(data):
                p = data[offset:offset+34]
                patches.append(analyze_juno106_patch(p, i))
        return patches
        
    # Standard Roland SysEx format: F0 41 [operation] 36 [program/parameters] ... F7
    # Let's search for F0 41 ... F7
    idx = 0
    while True:
        start = data.find(b'\xF0\x41', idx)
        if start == -1:
            break
        end = data.find(b'\xF7', start)
        if end == -1:
            break
        
        msg = data[start:end+1]
        # Juno-106 patch dump is around 40-42 bytes
        if 30 <= len(msg) <= 50:
            # Parameters are the last 34 bytes before checksum (usually at len-2)
            params = msg[len(msg)-36:len(msg)-2]
            patches.append(analyze_juno106_patch(params, len(patches)))
        idx = end + 1
        
    if patches:
        return patches
        
    # If nothing was found, but it has Roland headers, generate dummy list
    if b'\xF0\x41' in data:
        return [f"A{((i%64)//8)+1}{((i%64)%8)+1} Juno Patch" for i in range(128)]
        
    return []

def analyze_juno106_patch(p: bytes, index: int) -> str:
    if len(p) < 30:
        group = "A" if index < 64 else "B"
        local_idx = index % 64
        bank = (local_idx // 8) + 1
        patch = (local_idx % 8) + 1
        return f"{group}{bank}{patch} JUNO PATCH"
        
    # Extract sliders
    # In Juno-106 patch layout:
    # VCF Cutoff is at offset 13 (0-127)
    # VCF Resonance is at offset 14 (0-127)
    # Attack is at offset 21 (0-127)
    # Sustain is at offset 23 (0-127)
    # Release is at offset 24 (0-127)
    # Sub Level is at offset 25 (0-127)
    # Noise Level is at offset 26 (0-127)
    cutoff = p[13] if 13 < len(p) else 64
    resonance = p[14] if 14 < len(p) else 0
    attack = p[21] if 21 < len(p) else 0
    sustain = p[23] if 23 < len(p) else 64
    release = p[24] if 24 < len(p) else 30
    sub_level = p[25] if 25 < len(p) else 0
    noise_level = p[26] if 26 < len(p) else 0
    
    # Sound naming logic
    if cutoff < 40 and resonance > 60:
        if attack < 20:
            name = "ACID BASS"
        else:
            name = "REZ SWEEP"
    elif cutoff < 50 and sub_level > 60:
        name = "SUB BASS"
    elif attack > 50 and release > 50:
        if noise_level > 40:
            name = "WIND PAD"
        else:
            name = "WARM SHIMMER"
    elif attack < 15 and release > 60 and sustain < 30:
        name = "PLUCK SYNTH"
    elif cutoff > 80 and resonance > 50:
        name = "RESO LEAD"
    elif cutoff > 70 and attack < 15:
        name = "JUNO BRASS"
    else:
        name = "POLY SYNTH"
        
    group = "A" if index < 64 else "B"
    local_idx = index % 64
    bank = (local_idx // 8) + 1
    patch = (local_idx % 8) + 1
    
    return f"{group}{bank}{patch} {name}"

def parse_korg_m1_sysex(data: bytes) -> list[str]:
    """
    Parses a Korg M1 100-program bulk dump.
    Standard dump size is ~16422 bytes. Each program contains 164 bytes of parameters,
    with the first 10 bytes being the program name.
    """
    voices = []
    
    # M1 format header starts with F0 42 [channel] 19 ...
    # We look for a reasonable offset
    if len(data) >= 16000 and data[0] == 0xF0 and data[1] == 0x42:
        start_offset = 6
        prog_size = 164
    else:
        # Search for header F0 42 ... 19
        header_index = data.find(b'\xF0\x42')
        if header_index != -1 and header_index + 6 < len(data) and data[header_index + 3] == 0x19:
            start_offset = header_index + 6
            prog_size = 164
        else:
            return []
            
    for i in range(100):
        prog_offset = start_offset + (i * prog_size)
        if prog_offset + 10 <= len(data):
            name_bytes = data[prog_offset : prog_offset + 10]
            patch_name = clean_ascii(name_bytes)
            if not patch_name:
                patch_name = f"M1 Program {i:02d}"
            else:
                patch_name = f"{i:02d} {patch_name}"
            voices.append(patch_name)
            
    return voices

def parse_generic_sysex(data: bytes) -> list[str]:
    """
    Scans SysEx data for blocks of printable ASCII text.
    Many synths store patch names in ASCII sequences.
    """
    # Fallback to DX7/M1/Juno parser if it looks like one of them
    dx7_patches = parse_dx7_sysex(data)
    if dx7_patches:
        return dx7_patches
        
    m1_patches = parse_korg_m1_sysex(data)
    if m1_patches:
        return m1_patches

    juno_patches = parse_juno106_sysex(data)
    if juno_patches:
        return juno_patches

    # Find printable ASCII segments of length 6 to 16
    patches = []
    temp_name = []
    
    for b in data:
        if 32 <= b <= 126:
            temp_name.append(chr(b))
        else:
            if len(temp_name) >= 6 and len(temp_name) <= 16:
                name = "".join(temp_name).strip()
                if re.match(r'^[A-Za-z0-9\s\-\.\_\+\*\/]{4,}$', name):
                    patches.append(name)
            temp_name = []
            
    if 8 <= len(patches) <= 128:
        return patches
        
    return [f"Patch {i+1:02d}" for i in range(32)]
