"""
synth_seo_catalog.py - Universal Programmatic SEO & Hardware Synth Catalog
========================================================================
Extracts metadata from all 110+ synthesizer adapters in sysex_adapters/
and generates rich SEO profiles, hardware memory protect instructions,
and schema.org definitions.
"""

import os
import re
import glob
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger("synth_seo_catalog")

BASE_DIR = Path(__file__).resolve().parent
ADAPTERS_DIR = BASE_DIR / "sysex_adapters"
FALLBACK_ADAPTERS_DIR = BASE_DIR / "knobkraft_src" / "adaptations"

# Brand normalization mappings
BRAND_MAP = {
    "yamaha": "Yamaha",
    "roland": "Roland",
    "korg": "Korg",
    "oberheim": "Oberheim",
    "sequential": "Sequential",
    "dsi": "Dave Smith Instruments",
    "dave smith": "Dave Smith Instruments",
    "kawai": "Kawai",
    "casio": "Casio",
    "moog": "Moog",
    "ensoniq": "Ensoniq",
    "novation": "Novation",
    "alesis": "Alesis",
    "behringer": "Behringer",
    "elektron": "Elektron",
    "emu": "E-MU",
    "e-mu": "E-MU",
    "waldorf": "Waldorf",
    "access": "Access",
    "akai": "Akai",
    "pioneer": "Pioneer",
    "groove": "Groove Synthesis",
    "erica": "Erica Synths",
    "line 6": "Line 6",
    "jb": "John Bowen",
    "bc": "Black Corporation",
    "studiologic": "Studiologic",
}

# Known synth specifications database for deeper enrichment
SYNTH_SPEC_DB: Dict[str, Dict[str, Any]] = {
    "prophet-5": {
        "engine": "Analog Polyphonic (Curtis/SSM VCOs, 24dB 4-pole Lowpass Filter)",
        "polyphony": "5 voices",
        "year": "1978 / 2020",
        "famous_tracks": ["Michael Jackson - Thriller", "Phil Collins - In the Air Tonight", "Radiohead - Everything in Its Right Place"],
        "protect_steps": "On Rev 4, press GLOBALS, navigate to MIDI SysEx, and enable SysEx Dump/Load. On Rev 3.3 MIDI, ensure the rear memory protect switch is disabled."
    },
    "prophet-6": {
        "engine": "Discrete VCO Analog Polyphonic with Dual DSP FX",
        "polyphony": "6 voices",
        "year": "2015",
        "famous_tracks": ["Tycho - Epoch", "Bon Iver - 22, A Million", "RÜFÜS DU SOL - Bloom"],
        "protect_steps": "Press GLOBALS, scroll to MIDI SysEx (Page 8), and toggle to 'All' or 'NRPN+SysEx' to allow patch transfers."
    },
    "prophet-08": {
        "engine": "Analog Subtractive with Curtis DCOs and Analog Low-Pass Filter",
        "polyphony": "8 voices",
        "year": "2007",
        "famous_tracks": ["James Blake - Retrograde", "Snarky Puppy - Lingus"],
        "protect_steps": "Press GLOBAL, scroll to 'MIDI SysEx: On', and ensure MIDI Channel is set to Omni or matches your transmitter."
    },
    "prophet-12": {
        "engine": "Hybrid (Digital Oscillators with Character section + Analog Curtis Filters)",
        "polyphony": "12 voices",
        "year": "2013",
        "famous_tracks": ["Nine Inch Nails - Bad Witch", "Chvrches - Every Open Eye"],
        "protect_steps": "Press GLOBAL, scroll to MIDI SysEx settings, and select 'MIDI + USB' for bidirection SysEx dumps."
    },
    "ob-6": {
        "engine": "Discrete VCO Analog Polyphonic with Oberheim SEM State-Variable Filter",
        "polyphony": "6 voices",
        "year": "2016",
        "famous_tracks": ["Deadmau5 - Polar", "Kiasmos - Blurred EP"],
        "protect_steps": "Press GLOBALS, scroll to MIDI SysEx parameter, and enable SysEx Transmission and Reception."
    },
    "matrix-6": {
        "engine": "Analog Subtractive with CEM3396 Curtis synth-on-a-chip",
        "polyphony": "6 voices",
        "year": "1985",
        "famous_tracks": ["Vangelis - Direct", "The Prodigy - Experience"],
        "protect_steps": "Press Master, select MIDI Parameters, and toggle SysEx (System Exclusive) to Enabled. Switch Protect to OFF."
    },
    "matrix-1000": {
        "engine": "Analog Subtractive (6 voices, CEM3396 Waveshaping DCOs + 24dB LPF)",
        "polyphony": "6 voices",
        "year": "1988",
        "famous_tracks": ["Moby - Play", "Aphex Twin - Selected Ambient Works 85-92"],
        "protect_steps": "Press Select until the Bank/Protect LED lights up. Press + / - to toggle to 'U F' (Unprotected) for banks 000-199."
    },
    "ob-8": {
        "engine": "Discrete Polyphonic Analog with Curtis CEM3340 VCOs & CEM3320 Filters",
        "polyphony": "8 voices",
        "year": "1983",
        "famous_tracks": ["Prince - 1999", "Van Halen - Jump (Live / Studio backup)", "Depeche Mode - Some Great Reward"],
        "protect_steps": "If equipped with Encore MIDI retrofit, enter the MIDI setup menu and set SysEx mode to Active. Disable rear write-protect."
    },
    "ob-x8": {
        "engine": "Pure Analog Signal Path (OB-X, OB-Xa, OB-8 discrete circuits)",
        "polyphony": "8 voices",
        "year": "2022",
        "famous_tracks": ["Modern Synthwave & Touring Pop Masters"],
        "protect_steps": "Press GLOBAL, navigate to Page 4 (MIDI Configuration), and set SysEx transfer mode to USB / DIN."
    },
    "deepmind-12": {
        "engine": "Analog Polyphonic (2 DCOs per voice + TC Electronic/Klark Teknik FX)",
        "polyphony": "12 voices",
        "year": "2016",
        "famous_tracks": ["Com Truise - Iteration", "Carpenter Brut - Leather Patrol"],
        "protect_steps": "Press GLOBAL, go to Connectivity -> MIDI Settings, and enable 'SysEx Rx/Tx: On'."
    },
    "kawai-k1": {
        "engine": "8-bit VM (Vector Mixer) PCM + Additive Harmonic Waveforms",
        "polyphony": "16 voices",
        "year": "1988",
        "famous_tracks": ["Enya - Watermark (Choir & Glass elements)", "Early 90s ambient & dungeon synth"],
        "protect_steps": "Press SYSTEM, navigate to PROTECT, toggle 'INTERNAL PROTECT: OFF', and set 'SYS EX: ON'."
    },
    "kawai-k4": {
        "engine": "16-bit DMS (Digital Multi-Spectrum) PCM with Digital Resonant Filters",
        "polyphony": "16 voices",
        "year": "1989",
        "famous_tracks": ["Early Rave, Hardcore Techno, & 90s Game Soundtracks"],
        "protect_steps": "Press SYSTEM, scroll to Page 3 (Protect), change INT PROTECT to OFF, and enable System Exclusive receive."
    },
    "kawai-k5000": {
        "engine": "Advanced Additive Synthesis (128 Harmonics + Formant Filter)",
        "polyphony": "32 voices",
        "year": "1996",
        "famous_tracks": ["Kraftwerk - Tour de France Soundtracks", "Solar Fields - Earthshine"],
        "protect_steps": "Press SYSTEM/MIDI, scroll to MIDI RX FILTER, ensure SysEx is set to ENABLE, and turn Memory Protect to OFF."
    },
    "ensoniq-esq1": {
        "engine": "8-bit Digital Wavetable Oscillators through CEM3379 Analog 4-pole Lowpass Filters",
        "polyphony": "8 voices",
        "year": "1986",
        "famous_tracks": ["Jean-Michel Jarre - Revolutions", "Skinny Puppy - Cleanse Fold and Manipulate"],
        "protect_steps": "Press MIDI, scroll to SYS-EX, change to 'ENABLED=ON'. Memory protection is bypassed during direct SysEx bank dump."
    },
    "ensoniq-vfx": {
        "engine": "21-bit Transwave Wavetable Synthesis with Dynamic Modulation",
        "polyphony": "21 voices",
        "year": "1989",
        "famous_tracks": ["Tony Banks (Genesis) - Bankstatement", "Rick Wakeman"],
        "protect_steps": "Press MASTER, go to MIDI settings, enable SysEx Receive, and turn System Memory Lock OFF."
    },
    "moog-voyager": {
        "engine": "100% Discrete Analog Monophonic with Dual Moog Ladder Filters",
        "polyphony": "1 voice (Monophonic)",
        "year": "2002",
        "famous_tracks": ["Daft Punk - Tron: Legacy", "Herbie Hancock", "Nine Inch Nails"],
        "protect_steps": "Press EDIT, navigate to Master MIDI setup, set 'Send/Receive SysEx: Enabled', and turn Memory Protect OFF."
    },
    "microkorg": {
        "engine": "DSP Analog Modeling (Korg MS2000 engine with 8-band Vocoder)",
        "polyphony": "4 voices",
        "year": "2002",
        "famous_tracks": ["The Killers - Hot Fuss", "LCD Soundsystem - Sound of Silver", "Justice - †"],
        "protect_steps": "Turn Edit Select 2 to MIDI, turn parameter knob 3 (System Exclusive) to ON, and ensure Write Protect is set to OFF."
    },
    "ms2000": {
        "engine": "Analog Modeling DSP with Dual Oscillators, Virtual Patch, and Vocoder",
        "polyphony": "4 voices",
        "year": "2000",
        "famous_tracks": ["Ladytron - 604", "The Prodigy - Always Outnumbered, Never Outgunned"],
        "protect_steps": "Press GLOBAL, turn page to MIDI Filter, set System Exclusive to 'ENABLE', and turn Memory Protect OFF."
    },
    "d-50": {
        "engine": "Linear Arithmetic (LA) Synthesis (PCM Attacks + Sampled Loops)",
        "polyphony": "16 voices",
        "year": "1987",
        "famous_tracks": ["Enya - Orinoco Flow", "Michael Jackson - Bad", "Miles Davis - Amandla"],
        "protect_steps": "Press TUNE/FUNCTION, scroll to 'PROTECT', set 'INT MEMORY PROTECT' to OFF. Press MIDI and enable 'EXCLUSIVE: ON'."
    },
    "alpha-juno": {
        "engine": "Analog Subtractive with Multi-Waveshaping DCOs and IR3109 Filter",
        "polyphony": "6 voices",
        "year": "1985",
        "famous_tracks": ["The Prodigy - Charly (Hoover patch / What the?)", "Joey Beltram - Mentasm"],
        "protect_steps": "Press MIDI, use Alpha Dial to select 'EXCLUSIVE', toggle to 'ON', and set Protect Switch on rear to OFF."
    },
    "jv-1080": {
        "engine": "32-bit Sample Playback & Roland Super JV Architecture",
        "polyphony": "64 voices",
        "year": "1994",
        "famous_tracks": ["Hans Zimmer - The Rock soundtrack", "90s Film & TV Scores worldwide"],
        "protect_steps": "Press SYSTEM, page down to 'MIDI', set 'SysEx Receive' to ON, and toggle 'Memory Protect' to OFF."
    },
    "waldorf-blofeld": {
        "engine": "Virtual Analog & PPG Wavetable Synthesis",
        "polyphony": "Up to 25 voices",
        "year": "2007",
        "famous_tracks": ["Modern Ambient, IDM, and Game Scoring"],
        "protect_steps": "Press GLOBAL, navigate to MIDI menu, set 'SysEx ID' and ensure 'Send/Receive: Enabled'."
    },
    "access-virus": {
        "engine": "Advanced Virtual Analog & Wavetable DSP",
        "polyphony": "16 to 80 voices (depending on model)",
        "year": "1997 - 2009",
        "famous_tracks": ["Sasha - Airdrawndagger", "Noisia", "The Chemical Brothers"],
        "protect_steps": "Press SYSTEM/CONFIG, scroll to MIDI System, set 'Midi Dump Rx: Enable', and set Memory Lock to OFF."
    },
    "akai-ax80": {
        "engine": "Analog Subtractive (2 DCOs per voice with CEM3372 Analog VCF/VCA)",
        "polyphony": "8 voices",
        "year": "1984",
        "famous_tracks": ["80s Italo Disco, Synthwave, and Darkwave"],
        "protect_steps": "Locate the Memory Protect switch on the rear panel and slide to OFF. Set MIDI Channel and enable SysEx communication."
    },
    "alesis-andromeda-a6": {
        "engine": "16-voice True Analog Polyphonic with Dual Discrete Filters (Moog + Oberheim style)",
        "polyphony": "16 voices",
        "year": "2000",
        "famous_tracks": ["BT - Emotional Technology", "Daft Punk - Tron: Legacy"],
        "protect_steps": "Press GLOBAL, select MIDI tab, set 'SysEx Transmit/Receive' to ON, and disable System Write Protect."
    }
}

def clean_slug(name_or_file: str) -> str:
    """Standardizes slug format."""
    clean = Path(name_or_file).stem
    clean = clean.replace("_", " ").replace("-", " ")
    clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean)  # camelCase to words
    clean = re.sub(r'[^a-zA-Z0-9\s]+', '', clean)
    clean = re.sub(r'\s+', '-', clean.strip().lower())
    return clean

def extract_adapter_info(filepath: Path) -> Tuple[str, str, str]:
    """
    Parses adapter python file without full dynamic import to extract display name and brand safely.
    """
    stem = filepath.stem
    content = ""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass

    # Try finding `def name(): return "..."`
    name_match = re.search(r'def\s+name\s*\(\s*\)\s*:\s*(?:return|\n\s+return)\s*["\']([^"\']+)["\']', content)
    if name_match:
        display_name = name_match.group(1).strip()
    else:
        # Format stem nicely (e.g. Oberheim_OB8 -> Oberheim OB-8)
        display_name = stem.replace("_", " ")
        display_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', display_name)

    slug = clean_slug(display_name)

    # Determine brand
    brand = "Vintage"
    lower_name = (display_name + " " + stem).lower()
    for k, v in BRAND_MAP.items():
        if k in lower_name:
            brand = v
            break

    # If brand isn't in display_name, prepend it nicely unless it already starts with it
    if brand != "Vintage" and not display_name.lower().startswith(brand.lower()):
        display_name = f"{brand} {display_name}"

    return brand, display_name, slug

def build_programmatic_records() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Scans adapters and builds SEO_DATA and WIKI_DATA dictionaries for all synths.
    """
    seo_data: Dict[str, Dict[str, Any]] = {}
    wiki_data: Dict[str, Dict[str, Any]] = {}

    target_dir = ADAPTERS_DIR if ADAPTERS_DIR.exists() else FALLBACK_ADAPTERS_DIR
    if not target_dir.exists():
        logger.warning(f"No adapters directory found at {target_dir}")
        return seo_data, wiki_data

    for py_file in sorted(target_dir.glob("*.py")):
        if py_file.stem.startswith("test_") or py_file.name in ("conftest.py", "PythonUtils.py", "__init__.py"):
            continue

        brand, synth_name, slug = extract_adapter_info(py_file)
        if not slug:
            continue

        # Look up pre-defined rich specs if available
        spec = SYNTH_SPEC_DB.get(slug, {})
        if not spec:
            # Try fuzzy matching
            for k, v in SYNTH_SPEC_DB.items():
                if k in slug or slug in k:
                    spec = v
                    break

        engine = spec.get("engine", f"{brand} Hardware Synthesizer & SysEx Engine")
        polyphony = spec.get("polyphony", "Hardware Polyphonic / Monophonic")
        year = spec.get("year", "Vintage Era")
        famous_tracks = spec.get("famous_tracks", [f"Iconic studio productions featuring {synth_name}"])
        protect_steps = spec.get(
            "protect_steps",
            f"Enter Global / Utility MIDI settings on your {synth_name}. Toggle Memory Protect to OFF and set System Exclusive (SysEx) Receive to ON."
        )

        title = f"{synth_name} SysEx Librarian & Web MIDI Cloud Backup | bipluk"
        description = (
            f"Browser-native SysEx librarian and patch manager for the {synth_name}. "
            f"Back up, organize, and restore {synth_name} soundbanks directly via Web MIDI in Chrome. "
            f"Zero driver installation, instant 1-click transfers."
        )
        keywords = (
            f"{synth_name.lower()} sysex librarian, {synth_name.lower()} backup, "
            f"how to save {synth_name.lower()} presets, {brand.lower()} sysex transfer mac, "
            f"cloud backup for synthesizers, web midi {synth_name.lower()}"
        )

        docs_content = f"""<p class="text-zinc-400 mb-4 text-sm md:text-base">To dump or load soundbanks on the {synth_name}, internal memory protection must be disabled and System Exclusive communication enabled.</p>
<ol class="list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium">
    <li>Ensure MIDI IN and MIDI OUT DIN/USB cables are connected properly.</li>
    <li>{protect_steps}</li>
    <li>Click <strong>Start MIDI Engine</strong> below to initiate the Web MIDI SysEx handshake.</li>
</ol>
<p class="text-zinc-400 mt-5 text-sm md:text-base">Your {synth_name} is now ready for 1-click cloud backup and patch recall.</p>"""

        seo_data[slug] = {
            "title": title,
            "description": description,
            "keywords": keywords,
            "synth_name": synth_name,
            "hero_title": f"The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">{synth_name}.</span>",
            "hero_subtitle": (
                f"The easiest way to manage {synth_name} soundbanks and patches directly from your browser. "
                f"Zero setup, zero driver headaches, instant Web MIDI transfers."
            ),
            "docs": {
                "title": f"How to Turn Off Memory Protect & Enable SysEx on {synth_name}",
                "content": docs_content,
            }
        }

        wiki_data[slug] = {
            "brand": brand,
            "name": synth_name,
            "year": year,
            "engine": engine,
            "polyphony": polyphony,
            "dac": "Hardware Circuitry",
            "presets_count": "Full Soundbank Support",
            "rarity": "⭐⭐⭐★★",
            "famous_tracks": famous_tracks,
            "factory_presets": [f"{synth_name} Bank 1", f"{synth_name} User Presets"],
            "wiki_text": (
                f"The {synth_name} by {brand} is a celebrated hardware synthesizer known for its distinct acoustic profile "
                f"and sonic flexibility. bipluk provides instant, zero-install Web MIDI SysEx library management, "
                f"soundbank diagnostics, and cloud preservation for the {synth_name} directly in your browser."
            ),
            "funny_anecdote": f"Known in studios worldwide for its unmistakable sound character and timeless hardware workflow."
        }

    return seo_data, wiki_data


# Cached singletons
_EXPANDED_SEO_CACHE = None
_EXPANDED_WIKI_CACHE = None

def get_expanded_seo_data(base_seo: Dict[str, Any] = None) -> Dict[str, Any]:
    global _EXPANDED_SEO_CACHE
    if _EXPANDED_SEO_CACHE is None:
        prog_seo, _ = build_programmatic_records()
        merged = dict(prog_seo)
        if base_seo:
            # User manual definitions take highest precedence
            merged.update(base_seo)
        _EXPANDED_SEO_CACHE = merged
    elif base_seo:
        _EXPANDED_SEO_CACHE.update(base_seo)
    return _EXPANDED_SEO_CACHE

def get_expanded_wiki_data(base_wiki: Dict[str, Any] = None) -> Dict[str, Any]:
    global _EXPANDED_WIKI_CACHE
    if _EXPANDED_WIKI_CACHE is None:
        _, prog_wiki = build_programmatic_records()
        merged = dict(prog_wiki)
        if base_wiki:
            # User manual definitions take highest precedence
            merged.update(base_wiki)
        _EXPANDED_WIKI_CACHE = merged
    elif base_wiki:
        _EXPANDED_WIKI_CACHE.update(base_wiki)
    return _EXPANDED_WIKI_CACHE

if __name__ == "__main__":
    s_data, w_data = build_programmatic_records()
    print(f"Generated {len(s_data)} programmatic synth SEO profiles and {len(w_data)} wiki entries.")
