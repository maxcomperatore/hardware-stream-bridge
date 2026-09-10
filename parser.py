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
    
    # Standard format: starts with F0 43, length is ~4104, Format ID is 09
    if len(data) >= 4104 and data[0] == 0xF0 and data[1] == 0x43 and data[3] == 0x09:
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
    Parses Roland Juno-106 SysEx patch parameters.
    APR format: F0 41 30 0n pp [16 sliders] [sw1] [sw2] F7 (24 bytes total).
    Since Juno-106 patches have no digital name tags, we analyze VCF, DCO, VCA,
    and envelope parameters to dynamically generate descriptive name tags (e.g., 'A11 ACID BASS').
    """
    patches_by_number: dict[int, str] = {}

    idx = 0
    while idx < len(data):
        start = data.find(b'\xF0\x41', idx)
        if start == -1:
            break
        end = data.find(b'\xF7', start)
        if end == -1:
            break

        msg = data[start:end + 1]
        if len(msg) >= 24 and msg[1] == 0x41:
            patch_num = None
            params = None
            # Legacy / captured dumps
            if msg[2] == 0x30:
                patch_num = msg[4]
                params = msg[5:23]
            # Roland Juno-106 APR (device 0x36, command 0x35)
            elif msg[2] == 0x36 and len(msg) >= 25 and msg[4] == 0x35:
                patch_num = msg[5]
                params = msg[6:24]
            if patch_num is not None and params is not None and len(params) == 18:
                if patch_num < 128:
                    patches_by_number[patch_num] = analyze_juno106_patch(params, patch_num)
        idx = end + 1

    if patches_by_number:
        return [patches_by_number[i] for i in sorted(patches_by_number.keys())]

    return []

def analyze_juno106_patch(p: bytes, index: int) -> str:
    group = "A" if index < 64 else "B"
    local_idx = index % 64
    bank = (local_idx // 8) + 1
    patch = (local_idx % 8) + 1
    prefix = f"{group}{bank}{patch}"

    if len(p) < 18:
        return f"{prefix} JUNO PATCH"

    # 16 slider bytes: LFO rate, LFO delay, DCO LFO, DCO PWM, Noise, VCF Freq,
    # VCF Res, VCF Env, VCF LFO, VCF KYBD, VCA Level, A, D, S, R, Sub Osc
    noise_level = p[4]
    cutoff = p[5]
    resonance = p[6]
    attack = p[11]
    sustain = p[13]
    release = p[14]
    sub_level = p[15]
    
    # Switch status:SW1 at index 16, SW2 at index 17
    sw2 = p[17]
    chorus_on = (sw2 & 0x03) > 0  # Chorus bit mask (00 = off, 01 = chorus I, 10 = chorus II)
    
    # Sound naming logic
    if cutoff < 40 and resonance > 60:
        if attack < 20:
            name = "ACID BASS" if not chorus_on else "CHORUS BASS"
        else:
            name = "REZ SWEEP"
    elif cutoff < 50 and sub_level > 60:
        name = "SUB BASS"
    elif attack > 50 and release > 50:
        if noise_level > 40:
            name = "WIND PAD"
        else:
            name = "WARM PAD" if chorus_on else "ANALOG SHIMMER"
    elif attack < 15 and release > 60 and sustain < 30:
        name = "PLUCK SYNTH"
    elif cutoff > 80 and resonance > 50:
        name = "RESO LEAD"
    elif cutoff > 70 and attack < 15:
        name = "JUNO BRASS"
    else:
        name = "POLY SYNTH"

    return f"{prefix} {name}"

def parse_korg_m1_sysex(data: bytes) -> list[str]:
    """
    Parses a Korg M1 100-program bulk dump.
    Standard dump size is ~16422 bytes. Each program contains 164 bytes of parameters,
    with the program name stored at parameters 133-142 (packed in 7-to-8 bit format).
    """
    voices = []
    
    # M1 format header starts with F0 42 [channel] 19 ...
    if len(data) >= 16000 and data[0] == 0xF0 and data[1] == 0x42 and data[3] == 0x19:
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
        if prog_offset + 164 <= len(data):
            # M1 program name occupies parameters 133-142 (10 chars).
            # When packed 7-to-8:
            # - First 133 bytes pack to 152 bytes in stream (19 chunks of 7 bytes).
            # - Byte 152 is collection byte for chunk 20. Chars 0-6 are at 153 to 159.
            # - Byte 160 is collection byte for chunk 21. Chars 7-9 are at 161 to 163.
            name_bytes = data[prog_offset + 153 : prog_offset + 160] + data[prog_offset + 161 : prog_offset + 164]
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
    # Fallback to DX7/M1/Juno/Jupiter/CZ/Prophet parser if it looks like one of them
    dx7_patches = parse_dx7_sysex(data)
    if dx7_patches:
        return dx7_patches
        
    m1_patches = parse_korg_m1_sysex(data)
    if m1_patches:
        return m1_patches

    juno_patches = parse_juno106_sysex(data)
    if juno_patches:
        return juno_patches

    jupiter_patches = parse_jupiter6_sysex(data)
    if jupiter_patches:
        return jupiter_patches

    cz_patches = parse_cz101_sysex(data)
    if cz_patches:
        return cz_patches

    prophet_patches = parse_prophet_sysex(data)
    # Check if we got any real Prophet names out of it, or if it has a high-quality Prophet-like layout
    if len(prophet_patches) >= 8 and any(not p.startswith("Prophet Patch") for p in prophet_patches):
        return prophet_patches

    # Count individual SysEx messages in the data
    messages_count = 0
    idx = 0
    while True:
        start = data.find(b'\xF0', idx)
        if start == -1:
            break
        end = data.find(b'\xF7', start)
        if end == -1:
            break
        messages_count += 1
        idx = end + 1

    # Find printable ASCII segments of length 6 to 16
    patches = []
    temp_name = []
    
    for b in data:
        if 32 <= b <= 126:
            temp_name.append(chr(b))
        else:
            if len(temp_name) >= 6 and len(temp_name) <= 16:
                name = "".join(temp_name).strip()
                if re.match(r'^[A-Za-z0-9\s\-\.\_\+\*\/\[\]\!\#]{4,}$', name):
                    patches.append(name)
            temp_name = []
            
    if 8 <= len(patches) <= 128:
        return patches
        
    # Default fallback to 128 if messages count matches common formats, otherwise fallback to 32 or message count
    fallback_count = messages_count if messages_count >= 8 else 32
    return [f"Patch {i+1:02d}" for i in range(fallback_count)]


def parse_jupiter6_sysex(data: bytes) -> list[str]:
    """
    Parses Roland Jupiter-6 SysEx dumps (Europa/Tauntek).
    Since JP-6 patches have no digital names, we analyze DCO, VCF, and envelope settings
    to dynamically name the patches.
    """
    patches = []
    
    # Roland SysEx starts with F0 41. Manufacturer ID 41.
    idx = 0
    while True:
        start = data.find(b'\xF0\x41', idx)
        if start == -1:
            break
        end = data.find(b'\xF7', start)
        if end == -1:
            break
        
        msg = data[start:end+1]
        # Jupiter-6 program dump is typically around 32-128 bytes
        if 32 <= len(msg) <= 128:
            params = msg[8:-2] if len(msg) > 10 else msg
            patches.append(analyze_jupiter6_patch(params, len(patches)))
        idx = end + 1
        
    if patches:
        return patches
        
    if b'\xF0\x41' in data:
        return [f"P{((i%48)//8)+1}{((i%48)%8)+1} JP-6 Patch" for i in range(48)]
        
    return []

def analyze_jupiter6_patch(p: bytes, index: int) -> str:
    if len(p) < 20:
        bank_num = (index // 8) + 1
        patch_num = (index % 8) + 1
        return f"P{bank_num}{patch_num} JP-6 Patch"
        
    cutoff = p[10] if len(p) > 10 else 64
    resonance = p[11] if len(p) > 11 else 0
    env_attack = p[18] if len(p) > 18 else 0
    env_release = p[20] if len(p) > 20 else 20
    
    if cutoff < 45 and resonance > 55:
        if env_attack < 20:
            name = "EUROPA BASS"
        else:
            name = "ACID SWEEP"
    elif env_attack > 60 and env_release > 60:
        name = "SPACE PAD"
    elif env_attack < 10 and env_release > 50:
        name = "SH-PLUCK"
    elif cutoff > 75 and resonance > 45:
        name = "RESO LEAD"
    elif cutoff > 60 and env_attack < 15:
        name = "JP BRASS"
    else:
        name = "ANALOG POLY"
        
    bank_num = (index // 8) + 1
    patch_num = (index % 8) + 1
    return f"P{bank_num}{patch_num} {name}"

def parse_cz101_sysex(data: bytes) -> list[str]:
    """
    Parses Casio CZ-101 tone dumps (typically starts with F0 44 ... F7).
    CZ tones do not have ASCII names, so we analyze DCO/DCW/DCA and envelopes.
    """
    patches = []
    
    # Casio manufacturer ID is 0x44
    idx = 0
    while True:
        start = data.find(b'\xF0\x44', idx)
        if start == -1:
            break
        end = data.find(b'\xF7', start)
        if end == -1:
            break
        
        msg = data[start:end+1]
        # CZ tone SysEx blocks can vary.
        if 80 <= len(msg) <= 300:
            params = msg[6:-1]
            patches.append(analyze_cz101_patch(params, len(patches)))
        idx = end + 1
        
    if patches:
        return patches
        
    if b'\xF0\x44' in data:
        return [f"INT-{i+1:02d} CZ Tone" for i in range(16)]
        
    return []

def analyze_cz101_patch(p: bytes, index: int) -> str:
    if len(p) < 30:
        bank = "INT" if index < 16 else "CRT"
        num = (index % 16) + 1
        return f"{bank}-{num:02d} CZ Tone"
        
    # CZ series tone parameters are nibblized (4 bits per byte, LSN first, then MSN)
    # Parameter 5 (index 10 & 11 in p)
    wave = (p[10] & 0x0F) | ((p[11] & 0x0F) << 4) if len(p) > 11 else 0
    # Parameter 9 (index 18 & 19 in p)
    dcw_level = (p[18] & 0x0F) | ((p[19] & 0x0F) << 4) if len(p) > 19 else 50
    # Parameter 13 (index 26 & 27 in p)
    dca_release = (p[26] & 0x0F) | ((p[27] & 0x0F) << 4) if len(p) > 27 else 30
    
    if dcw_level < 30:
        name = "PD SOFT BASS"
    elif dcw_level > 70 and wave > 2:
        name = "SYN LEAD"
    elif dca_release > 70:
        name = "COSMIC PAD"
    elif wave == 1 and dcw_level > 50:
        name = "CZ BRASS"
    else:
        name = "PD SYNTH"
        
    bank = "INT" if index < 16 else "CRT"
    num = (index % 16) + 1
    return f"{bank}-{num:02d} {name}"

def parse_prophet_sysex(data: bytes) -> list[str]:
    """
    Parses Sequential Prophet SysEx data (Prophet-5, Prophet-6, Prophet-8/12, OB-6, etc.).
    Supports multi-message dumps and single bulk dumps.
    Handles non-standard quotes (e.g. ’ / '), spaces, and prevents +1 index offset caused by identity headers.
    """
    def unescape_sequential(sysex):
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

    def extract_dsi_name(unescaped):
        strings = []
        current = []
        for b in unescaped:
            if 32 <= b <= 126:
                current.append(chr(b))
            else:
                if len(current) >= 4:
                    strings.append("".join(current))
                current = []
        if len(current) >= 4:
            strings.append("".join(current))

        candidates = []
        for s in strings:
            if len(s) in [16, 20]:
                if re.match(r'^[xXdX]+$', s): continue
                if re.match(r'^[<]+$', s): continue
                if re.match(r'^[0-9A-Fa-f]+$', s): continue
                if sum(1 for c in s if c.isalpha()) >= 3:
                    candidates.append(s)

        if candidates:
            return candidates[0]

        if len(unescaped) >= 85:
            p5_name = unescaped[65:85]
            if all(32 <= b <= 126 for b in p5_name):
                s = p5_name.decode('ascii')
                if sum(1 for c in s if c.isalpha()) >= 3:
                    return s

        filtered = []
        for s in strings:
            if re.match(r'^[<xXdX]+$', s): continue
            if re.match(r'^[0-9A-Fa-f]+$', s): continue
            if sum(1 for c in s if c.isalpha()) >= 3:
                filtered.append(s[:20])

        if filtered:
            return max(filtered, key=len)

        return None

    messages = []
    idx = 0
    while True:
        start = data.find(b'\xF0', idx)
        if start == -1:
            break
        end = data.find(b'\xF7', start)
        if end == -1:
            break
        msg = data[start:end+1]
        # Filter out identity responses (F0 7E ... F7) or short non-program messages (< 10 bytes)
        if len(msg) >= 10 and not msg.startswith(b'\xF0\x7E'):
            messages.append(msg)
        idx = end + 1

    patches = []

    def clean_name(raw_bytes: bytes) -> str:
        try:
            text = raw_bytes.decode('utf-8', errors='replace')
        except Exception:
            text = raw_bytes.decode('latin-1', errors='replace')
        cleaned = []
        for ch in text:
            if ch in "’'\"" or (ord(ch) >= 32 and ord(ch) != 127):
                cleaned.append(ch)
            else:
                cleaned.append(' ')
        return " ".join("".join(cleaned).split()).strip()

    if len(messages) > 0:
        for i, msg in enumerate(messages):
            patch_name = None
            if len(msg) > 7 and msg[0] == 0xF0 and msg[1] == 0x01:
                unescaped = unescape_sequential(msg[6:-1])
                extracted = extract_dsi_name(unescaped)
                if extracted:
                    patch_name = extracted.strip()

            if not patch_name:
                text = clean_name(msg)
                matches = re.findall(r'[A-Za-z0-9][A-Za-z0-9\s\-\.\_\+\*\/\[\]\!\#\’\']{2,15}', text)
                filtered = []
                for m in matches:
                    name = m.strip()
                    if len(name) >= 3 and not any(kw in name.lower() for kw in ["dsi", "sequential", "sysex", "system"]):
                        filtered.append(name)
                patch_name = max(filtered, key=len) if filtered else f"Patch {i+1:02d}"

            # Format with Prophet-5 hardware base-8 bank/slot display (11..18, 21..28, up to 58)
            group = (i // 8) + 1
            slot = (i % 8) + 1
            slot_label = f"{group}{slot}"
            # Prepend if not already prefixed with hardware numbers
            if not re.match(r'^\d{2}\s', patch_name):
                patch_name = f"{slot_label} {patch_name}"

            patches.append(patch_name)
    else:
        text = clean_name(data)
        matches = re.findall(r'[A-Za-z0-9][A-Za-z0-9\s\-\.\_\+\*\/\[\]\!\#\’\']{3,15}', text)
        for i, m in enumerate(matches):
            name = m.strip()
            if len(name) >= 4 and not any(kw in name.lower() for kw in ["dsi", "sequential", "sysex", "system"]):
                group = (i // 8) + 1
                slot = (i % 8) + 1
                slot_label = f"{group}{slot}"
                if not re.match(r'^\d{2}\s', name):
                    name = f"{slot_label} {name}"
                patches.append(name)

    expected_count = len(messages) if len(messages) >= 1 else (len(patches) if len(patches) > 0 else 40)
    if len(patches) < expected_count:
        while len(patches) < expected_count:
            idx = len(patches)
            group = (idx // 8) + 1
            slot = (idx % 8) + 1
            patches.append(f"{group}{slot} Prophet Patch {idx+1:02d}")

    return patches[:expected_count] if expected_count > 0 else patches


def escape_sequential(unescaped: bytes) -> bytes:
    result = bytearray()
    idx = 0
    while idx < len(unescaped):
        chunk = unescaped[idx:idx+7]
        idx += 7
        msbits = 0
        for i, b in enumerate(chunk):
            if b & 0x80:
                msbits |= (1 << i)
        result.append(msbits)
        for b in chunk:
            result.append(b & 0x7F)
    return bytes(result)

def inject_hardware_base8_names_prophet(data: bytes, patch_names: list[str]) -> bytes:
    """Modifies the Prophet SysEx to inject the hardware numbers back into the SysEx payload."""
    if not data or not patch_names:
        return data

    def unescape_sequential(sysex):
        result = bytearray()
        dataIndex = 0
        while dataIndex < len(sysex):
            msbits = sysex[dataIndex]
            dataIndex += 1
            for i in range(7):
                if dataIndex < len(sysex):
                    result.append(sysex[dataIndex] | ((msbits & (1 << i)) << (7 - i)))
                dataIndex += 1
        return bytearray(result)

    messages = []
    idx = 0
    while True:
        start = data.find(b'\xF0', idx)
        if start == -1:
            break
        end = data.find(b'\xF7', start)
        if end == -1:
            break
        msg = data[start:end+1]
        messages.append((start, end+1, msg))
        idx = end + 1

    patch_messages = []
    for start, end, msg in messages:
        if len(msg) >= 10 and not msg.startswith(b'\xF0\x7E'):
            patch_messages.append((start, end, msg))

    # Case A: Multi-message dump (each patch is an individual SysEx message)
    if len(patch_messages) > 1:
        modified_data = bytearray(data)
        offset_diff = 0
        limit = min(len(patch_messages), len(patch_names))
        for i in range(limit):
            start, end, msg = patch_messages[i]
            new_name = patch_names[i]

            new_name_bytes = new_name.encode('ascii', errors='ignore')
            new_name_bytes = new_name_bytes[:20].ljust(20, b' ')

            header_len = 6
            if len(msg) > 8 and msg[0] == 0xF0:
                if msg[1] == 0x00 and msg[2] == 0x01:
                    header_len = 7
                elif msg[1] == 0x01:
                    header_len = 6
                else:
                    header_len = 5

            if len(msg) > header_len + 1:
                unescaped = unescape_sequential(msg[header_len:-1])

                strings = []
                current = []
                start_idx = -1
                for j, b in enumerate(unescaped):
                    if 32 <= b <= 126:
                        if not current: start_idx = j
                        current.append(chr(b))
                    else:
                        if len(current) >= 3:
                            strings.append(("".join(current), start_idx))
                        current = []
                        start_idx = -1
                if len(current) >= 3:
                    strings.append(("".join(current), start_idx))

                name_offset = -1
                import re
                candidates = []
                for s, s_idx in strings:
                    if len(s) in [16, 20]:
                        if re.match(r'^[xXdX]+$', s): continue
                        if re.match(r'^[<]+$', s): continue
                        if re.match(r'^[0-9A-Fa-f]+$', s): continue
                        if sum(1 for c in s if c.isalpha()) >= 2:
                            candidates.append((s, s_idx))

                if candidates:
                    name_offset = candidates[0][1]
                elif len(unescaped) >= 85 and all(32 <= b <= 126 for b in unescaped[65:85]):
                    name_offset = 65
                elif strings:
                    best = max(strings, key=lambda item: len(item[0]))
                    name_offset = best[1]

                if name_offset != -1:
                    target_len = min(20, len(unescaped) - name_offset)
                    unescaped[name_offset:name_offset+target_len] = new_name_bytes[:target_len]

                    new_payload = escape_sequential(bytes(unescaped))
                    new_msg = msg[:header_len] + new_payload + msg[-1:]

                    modified_data[start+offset_diff : end+offset_diff] = new_msg
                    offset_diff += len(new_msg) - len(msg)

        return bytes(modified_data)

    # Case B: Single bulk SysEx message containing multiple patches unescaped
    elif len(patch_messages) == 1:
        start, end, msg = patch_messages[0]
        header_len = 6
        if len(msg) > 8 and msg[1] == 0x00 and msg[2] == 0x01:
            header_len = 7
        payload = msg[header_len:-1]
        unescaped = bytearray(unescape_sequential(payload))

        strings = []
        current = []
        start_idx = -1
        for j, b in enumerate(unescaped):
            if 32 <= b <= 126:
                if not current: start_idx = j
                current.append(chr(b))
            else:
                if len(current) >= 4:
                    strings.append(("".join(current), start_idx, len(current)))
                current = []
                start_idx = -1
        if len(current) >= 4:
            strings.append(("".join(current), start_idx, len(current)))

        valid_names = [item for item in strings if sum(1 for c in item[0] if c.isalpha()) >= 2 and not any(kw in item[0].lower() for kw in ["sequential", "sysex", "system"])]
        
        limit = min(len(valid_names), len(patch_names))
        for i in range(limit):
            s, s_idx, s_len = valid_names[i]
            new_name = patch_names[i]
            new_name_bytes = new_name.encode('ascii', errors='ignore')[:s_len].ljust(s_len, b' ')
            unescaped[s_idx:s_idx+s_len] = new_name_bytes

        new_payload = escape_sequential(bytes(unescaped))
        new_msg = msg[:header_len] + new_payload + msg[-1:]
        modified_data = bytearray(data)
        modified_data[start:end] = new_msg
        return bytes(modified_data)

    return data
