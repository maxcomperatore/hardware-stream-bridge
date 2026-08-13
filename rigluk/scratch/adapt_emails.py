import os
import glob

templates_dir = r"d:\crew\experiment\rigluk\templates"
email_files = glob.glob(os.path.join(templates_dir, "email_*.html"))

replacements = [
    ("synth owners", "pedalboard owners & guitarists"),
    ("synth collection", "pedalboard collection"),
    ("synth vaults", "pedalboard vaults"),
    ("synth vault", "pedalboard vault"),
    ("hardware synths", "pedalboard gear"),
    ("hardware synth", "guitar pedal & amp modeler"),
    ("vintage synths", "digital pedals & modelers"),
    ("vintage synth", "guitar pedal"),
    ("synthesizer collection", "pedalboard collection"),
    ("synthesizers", "guitar pedals & amp modelers"),
    ("synthesizer", "guitar pedal"),
    ("synths", "pedals"),
    ("DX7, Juno-106, Korg M1, and 83+ synths", "Strymon, Eventide, Line 6, Boss, and 100+ pedals"),
    ("DX7, Juno-106, Korg M1, or modern Sequential Prophet", "Strymon, Eventide, Line 6, Boss, or Quad Cortex"),
    ("Roland Juno-106, Yamaha DX7, Korg M1, and Oberheim Matrix-1000", "Strymon BigSky, Eventide H90, Line 6 HX Stomp, and Boss GT-1000"),
    ("Backup every synthesizer in your studio", "Backup every pedal on your board"),
    ("Back Up Your Synth Now", "Back Up Your Rig Now"),
    ("Capture Soundbank", "Capture Preset Bank"),
    ("press SEND on your synthesizer", "press SEND on your pedalboard"),
    ("Plug in your synth using any class-compliant USB-MIDI interface cable", "Plug in your pedal using a USB cable or MIDI interface"),
    ("Auto-Detect Synth Engine", "Auto-Detect Pedal Model"),
    ("identifies your hardware synth", "identifies your pedal hardware"),
]

modified_count = 0
for fpath in email_files:
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
        new_content = new_content.replace(old.capitalize(), new.capitalize())

    if new_content != content:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        modified_count += 1
        print(f"Updated: {os.path.basename(fpath)}")

print(f"Total email templates updated: {modified_count}")
