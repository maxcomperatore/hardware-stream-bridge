"""Official rigluk FAQ corpus for AI Q&A and direct matching."""

import difflib
import re

FAQ_ENTRIES = [
    {
        "question": "What is rigluk?",
        "answer": (
            "rigluk is a browser-native cloud Web MIDI librarian and preset manager designed for "
            "guitar pedals, multi-effects, and amp modelers (Strymon, Eventide, Line 6, Boss, Kemper, Quad Cortex). "
            "It eliminates the need for legacy drivers or bloated desktop software (Strymon Nixie, HX Edit, Boss Tone Studio) "
            "by connecting your pedalboard directly to the web."
        ),
    },
    {
        "question": "How does browser-native Web MIDI work?",
        "answer": (
            "Modern browsers like Google Chrome, Microsoft Edge, and Opera support the Web MIDI API. "
            "This allows our website to communicate directly with your physical USB-to-MIDI pedalboard setup "
            "and hardware pedals without running any local background utilities or installing manual USB drivers."
        ),
    },
    {
        "question": "Is rigluk better than Strymon Nixie, HX Edit, or Boss Tone Studio?",
        "answer": (
            "Desktop utilities like Strymon Nixie, Line 6 HX Edit, or Boss Tone Studio require installing "
            "separate desktop applications for every pedal brand on your board. Beyond app sprawl and USB driver headaches, "
            "they don't offer a unified cross-brand cloud vault. rigluk runs directly in your browser with zero installation, "
            "automatically manages buffer sizing to prevent transfer crashes, and keeps your entire pedalboard synced in 1 click."
        ),
    },
    {
        "question": "Why use this instead of free utilities or desktop apps?",
        "answer": (
            "rigluk saves you time so you can focus on tone and playing music instead of fighting 4 different "
            "desktop utilities. Plus, you get zero setup, no app sprawl, a secure cloud library, and transparent "
            "one-time pricing."
        ),
    },
    {
        "question": "Who is behind rigluk?",
        "answer": (
            "rigluk is built by Half Radiation LLC, a small independent team of pedalboard nerds "
            "and software developers. We built this tool to solve the frustration of backing up and organizing "
            "our own pedalboard rigs."
        ),
    },
    {
        "question": "Are my presets private and secure?",
        "answer": (
            "Yes. All preset dumps and banks uploaded to rigluk are stored securely in your private cloud account. "
            "We only read the ASCII preset names to display them in your private searchable library, and your raw "
            "binary files are never shared."
        ),
    },
    {
        "question": "Is rigluk secure from a cybersecurity standpoint?",
        "answer": (
            "Yes. rigluk is designed with a defense-in-depth security model. Because it is completely "
            "browser-native, you do not need to install local desktop executables, background drivers, or untrusted "
            "utilities. On the backend, our processing engine runs in isolated environments with strict input "
            "sanitization. Additionally, all billing is securely managed via Stripe—no credit cards or payment "
            "credentials ever touch or reside on our servers."
        ),
    },
    {
        "question": "Can I export and download my preset files?",
        "answer": (
            "Absolutely. Every backup captured using rigluk can be downloaded as a standard .syx or binary file "
            "at any time. Your data is never locked in, allowing you to export and transfer your backups whenever you want."
        ),
    },
    {
        "question": "Is rigluk a subscription?",
        "aliases": [
            "is this a subscription",
            "monthly fee",
            "do i pay every month",
            "rent",
            "recurring",
            "saas",
        ],
        "answer": (
            "No. rigluk is not a subscription. rigluk+ is a simple $49 one-time lifetime purchase. "
            "Pay once, keep your vault, and download your files whenever you want. There are no monthly fees "
            "and no automatic renewals."
        ),
    },
    {
        "question": "What is the price of rigluk?",
        "aliases": [
            "how much does it cost",
            "how much is rigluk",
            "pricing",
            "what does it cost",
        ],
        "answer": (
            "rigluk+ is $49 one-time for lifetime access. Includes unlimited pedal preset backups, preset decoding, "
            "and full .syx/.zip/.csv exports. There are no recurring monthly fees."
        ),
    },
    {
        "question": "Will I ever lose access or be charged again?",
        "answer": (
            "No. Since this is a lifetime purchase, your account never expires and you will never be locked out of your "
            "dashboard. Your pedalboard presets will remain archived and accessible forever."
        ),
    },
    {
        "question": "Do you support browser-native MIDI on iOS or Android?",
        "answer": (
            "Yes! Android Chrome natively supports Web MIDI out of the box. On iOS, you can use specialized Web MIDI "
            "browsers (like WebMIDI Browser or WebBLE) to connect your iPhone or iPad to your pedals via USB-MIDI "
            "or Bluetooth-MIDI adapters."
        ),
    },
    {
        "question": "Which pedals and amp modelers are fully supported?",
        "aliases": ["supported pedals", "what pedals work", "compatible pedals", "supported synths", "what synths work"],
        "answer": (
            "We feature dedicated name-decoding parsers for Strymon (BigSky, Timeline, Mobius, Volante, NightSky), "
            "Eventide (H90, H9, Space, PitchFactor), Line 6 (HX Stomp, Helix, POD Go), Boss (GT-1000, 500 Series), "
            "Neural DSP (Quad Cortex), Kemper Profiler, Chase Bliss, and Meris (LVX, MercuryX). We also feature a "
            "universal Generic Scan that works with almost any MIDI-enabled pedal."
        ),
    },
    {
        "question": "Do I need a special MIDI interface or cable?",
        "answer": (
            "For USB pedals, plug in directly via USB. For 5-pin DIN pedals, any class-compliant USB-to-MIDI interface "
            "works. We recommend high-quality cables like the Roland UM-ONE or iConnectivity mio for rock-solid transfers."
        ),
    },
    {
        "question": "How do I prevent data transfer errors?",
        "answer": (
            "rigluk's MIDI transmission protocol is fine-tuned to throttle outbound dumps with calibrated timing, "
            "ensuring your pedal hardware writes the data to memory cleanly without dropping packets."
        ),
    },
]

SUGGESTED_QUESTIONS = [
    "What is rigluk?",
    "Is this a subscription?",
    "Which pedals are supported?",
    "What is the price?",
    "Are my presets private?",
    "Is it better than desktop apps?",
    "Do I need a special MIDI cable?",
]

FAQ_SUGGESTIONS = SUGGESTED_QUESTIONS


def find_faq_answer(user_query: str) -> str | None:
    query_clean = user_query.lower().strip()
    if not query_clean:
        return None

    for entry in FAQ_ENTRIES:
        if entry["question"].lower() == query_clean:
            return entry["answer"]
        for alias in entry.get("aliases", []):
            if alias.lower() == query_clean:
                return entry["answer"]

    questions = [e["question"] for e in FAQ_ENTRIES]
    for entry in FAQ_ENTRIES:
        for alias in entry.get("aliases", []):
            questions.append(alias)

    matches = difflib.get_close_matches(user_query, questions, n=1, cutoff=0.55)
    if matches:
        matched_str = matches[0]
        for entry in FAQ_ENTRIES:
            if entry["question"] == matched_str or matched_str in entry.get("aliases", []):
                return entry["answer"]

    return None
