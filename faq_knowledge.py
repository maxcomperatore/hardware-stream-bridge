"""Official bipluk FAQ corpus for AI Q&A and direct matching."""

import difflib
import re

FAQ_ENTRIES = [
    {
        "question": "What is bipluk?",
        "answer": (
            "bipluk is a browser-native cloud SysEx librarian and patch manager designed for "
            "vintage synthesizers from the 1980s and 90s. It eliminates the need for legacy drivers, "
            "desktop software, or complicated MIDI-OX configurations by connecting your instruments "
            "directly to the web."
        ),
    },
    {
        "question": "How does browser-native Web MIDI work?",
        "answer": (
            "Modern browsers like Google Chrome, Microsoft Edge, and Opera support the Web MIDI API. "
            "This allows our website to communicate directly with your physical USB-to-MIDI interface "
            "cables and hardware synths without running any local background utilities or installing "
            "manual USB drivers."
        ),
    },
    {
        "question": "Is bipluk better than Snoize or MIDI-OX?",
        "answer": (
            "Snoize (macOS) and MIDI-OX (Windows) were great in their day, but they are desktop relics. "
            "MIDI-OX hasn't been updated since 2011, runs on Windows 95/XP, and its official website "
            "currently triggers invalid SSL certificate warnings. Beyond the security risks, manually "
            "adjusting buffer settings on ancient desktop software is a headache. bipluk runs "
            "directly in your browser with zero installation, automatically manages buffer sizing to "
            "prevent transfer crashes, and keeps your library synced in the cloud."
        ),
    },
    {
        "question": "Why use this instead of free utilities or MIDI Quest?",
        "answer": (
            "Regardless of whether you understand the complex binary details of SysEx or have no clue "
            "what that even is, bipluk just works without any local installation or setup. It "
            "saves you time so you can focus on exploring soundbanks and making music. Plus, you get "
            "zero setup, no app sprawl, a secure cloud library, and transparent, fair pricing compared "
            "to legacy solutions like SoundQuest/MIDI Quest or SoundTower which cost hundreds of dollars."
        ),
    },
    {
        "question": "Who is behind bipluk?",
        "answer": (
            "bipluk is built by Half Radiation LLC, a small independent team of vintage synthesizer "
            "enthusiasts and software developers. We built this tool to solve the frustration of backing "
            "up and organizing our own classic hardware rigs."
        ),
    },
    {
        "question": "Are my patches private and secure?",
        "answer": (
            "Yes. All soundbanks and SysEx dumps uploaded to bipluk are stored securely in your "
            "private cloud account. We only read the ASCII patch names to display them in your private "
            "searchable library, and your raw .syx binary files are never shared."
        ),
    },
    {
        "question": "Is bipluk secure from a cybersecurity standpoint?",
        "answer": (
            "Yes. bipluk is designed with a defense-in-depth security model. Because it is "
            "completely browser-native, you do not need to install local desktop executables, background "
            "drivers, or untrusted utilities, keeping your operating system completely isolated from "
            "security risks. On the backend, our processing engine runs in isolated environments with "
            "strict input sanitization on all uploaded binary data to prevent SSRF vulnerabilities or "
            "buffer exploit attempts. Additionally, all billing is securely managed via Stripe—no credit "
            "cards or payment credentials ever touch or reside on our servers."
        ),
    },
    {
        "question": "Can I export and download my SysEx files?",
        "answer": (
            "Absolutely. Every backup captured using bipluk can be downloaded as a standard .syx "
            "binary file at any time. Your data is never locked in, allowing you to use your backups "
            "with classic tools like Snoize, MIDI-OX, or hardware sequencers."
        ),
    },
    {
        "question": "Is bipluk a subscription?",
        "aliases": [
            "is this a subscription",
            "monthly fee",
            "do i pay every month",
            "rent",
            "recurring",
            "saas",
        ],
        "answer": (
            "No. bipluk is not a subscription. bipluk+ is a simple $49 one-time lifetime "
            "purchase. Pay once, keep your vault, and download your .syx files whenever you want. There are no "
            "monthly fees and no automatic renewals."
        ),
    },
    {
        "question": "What is the price of bipluk?",
        "aliases": [
            "how much does it cost",
            "how much is bipluk",
            "pricing",
            "what does it cost",
        ],
        "answer": (
            "bipluk+ is $49 one-time for lifetime access. "
            "Includes unlimited soundbank backups, preset decoding, and full .syx/.zip/.csv exports. "
            "There are no recurring monthly fees."
        ),
    },
    {
        "question": "Will I ever lose access or be charged again?",
        "answer": (
            "No. Since this is a lifetime purchase, your account never expires and you will never be "
            "locked out of your dashboard. Your soundbanks will remain archived and accessible forever."
        ),
    },
    {
        "question": "Do you support browser-native MIDI on iOS or Android?",
        "answer": (
            "Yes! Android Chrome natively supports Web MIDI out of the box. On iOS, you can use "
            "specialized Web MIDI browsers (like WebMIDI Browser or WebBLE) to connect your iPhone or "
            "iPad to your synthesizers via USB-MIDI or Bluetooth-MIDI adapters."
        ),
    },
    {
        "question": "Which synthesizers are fully supported?",
        "aliases": ["supported synths", "what synths work", "compatible synthesizers"],
        "answer": (
            "We feature dedicated name-decoding parsers for the Yamaha DX7 (and compatible synths like "
            "DX7II, TX7, TX81Z), Roland Juno-106, Korg M1, Roland Jupiter-6 (Europa-modded), "
            "Sequential Prophet, and the Casio CZ series. We also feature a universal Generic Scan "
            "that works with almost any vintage synthesizer by scanning raw SysEx bulk dumps for "
            "readable ASCII character arrays to extract patch names automatically."
        ),
    },
    {
        "question": "Do I need a special MIDI interface or cable?",
        "answer": (
            "Any standard, class-compliant USB-to-MIDI interface will work. However, we highly recommend "
            "avoiding low-cost, unbranded interface cables, as they lack internal timing buffers and "
            "frequently drop or corrupt long SysEx byte blocks during large memory dumps."
        ),
    },
    {
        "question": "How do I prevent Buffer Overflow errors?",
        "answer": (
            "Older synthesizers utilize slow microprocessors and are easily overwhelmed by high-speed USB "
            "data. bipluk's MIDI transmission protocol is fine-tuned to throttle outbound dumps into "
            "small packages with 60ms pauses, ensuring your physical hardware can write the data to "
            "memory without dropping packets."
        ),
    },
    {
        "question": "Does it support editing patches in real time?",
        "answer": (
            "bipluk is primarily a librarian for backup, storage, organization, and quick retrieval "
            "of patch banks. While it does not feature a graphical synthesizer editor (with virtual "
            "sliders for every parameter), it allows you to audition and swap banks in one click."
        ),
    },
    {
        "question": "How robust is the patch parser?",
        "answer": (
            "The patch parser is built to be extremely robust. The specific defects identified in our "
            "analysis, including the Korg M1 name offset bugs, the Casio CZ-101 nibble-packing logic, "
            "the Roland Juno-106 switch parsing, and the Yamaha DX7 header validation, have been fully "
            "corrected and verified against standard synthesizer SysEx specifications. While the parser is "
            "now robust against standard MIDI dumps for these machines, some edge cases always remain: "
            "corrupted transfers if MIDI bytes are dropped, custom firmware that changes memory maps, "
            "and generic ASCII heuristics that can occasionally false-positive on binary data."
        ),
    },
]

FAQ_SUGGESTIONS = [
    "What is bipluk?",
    "Is this a subscription?",
    "Which synthesizers are supported?",
    "What is the price?",
    "Are my patches private?",
    "Is it better than MIDI-OX?",
    "Do I need a special MIDI cable?",
]

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "it",
        "do",
        "i",
        "my",
        "can",
        "you",
        "we",
        "what",
        "how",
        "are",
        "does",
        "of",
        "to",
        "in",
        "or",
        "and",
        "for",
        "this",
        "that",
        "with",
        "on",
        "be",
        "at",
        "from",
    }
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def _tokenize(text: str) -> set[str]:
    return {word for word in _normalize(text).split() if word and word not in _STOPWORDS}


def build_faq_corpus() -> str:
    blocks = []
    for entry in FAQ_ENTRIES:
        blocks.append(f"Q: {entry['question']}\nA: {entry['answer']}")
    return "\n\n".join(blocks)


def find_faq_match(question: str) -> dict | None:
    """Return the best matching FAQ entry, or None if no confident match."""
    q_norm = _normalize(question)
    if not q_norm:
        return None

    q_tokens = _tokenize(question)
    best_entry = None
    best_score = 0.0

    for entry in FAQ_ENTRIES:
        candidates = [entry["question"]] + entry.get("aliases", [])
        for candidate in candidates:
            e_q_norm = _normalize(candidate)
            seq_score = difflib.SequenceMatcher(None, q_norm, e_q_norm).ratio()
            e_tokens = _tokenize(candidate)
            overlap = 0.0
            if q_tokens and e_tokens:
                overlap = len(q_tokens & e_tokens) / max(len(q_tokens), len(e_tokens))

            score = max(seq_score, overlap * 0.95)
            if q_norm in e_q_norm or e_q_norm in q_norm:
                score = max(score, 0.9)

            if score > best_score:
                best_score = score
                best_entry = entry

    if best_entry and best_score >= 0.55:
        return best_entry
    return None
