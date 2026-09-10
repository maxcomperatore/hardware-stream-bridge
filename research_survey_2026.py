"""First-party survey data for /research/2026-vintage-synth-owner-survey."""

SURVEY_PAGE_URL = "https://bipluk.com/research/2026-vintage-synth-owner-survey"
SURVEY_DATA_URL = f"{SURVEY_PAGE_URL}/data.json"

SURVEY_2026 = {    "title": "2026 Vintage Synth Owner Survey",
    "period": "June 25 – July 1, 2026",
    "method": "In-product survey (PostHog) shown to bipluk visitors. Question 1 required; Question 2 optional free text.",
    "shown": 2417,
    "responses_q1": 61,
    "responses_q2": 24,
    "responses_q2_valid": 18,
    "conversion_pct": 2.57,
    "segments": [
        {
            "id": "gear_room",
            "label": "Dedicated gear room (5+ hardware boards)",
            "count": 29,
            "pct": 47.5,
        },
        {
            "id": "bedroom",
            "label": "Bedroom studio (1–2 vintage synths)",
            "count": 25,
            "pct": 41.0,
        },
        {
            "id": "commercial",
            "label": "Commercial studio, producer, or repair technician",
            "count": 7,
            "pct": 11.5,
        },
    ],
    "brands": [
        {"name": "Roland", "responses": 8, "pct": 44},
        {"name": "Korg", "responses": 7, "pct": 39},
        {"name": "Moog", "responses": 5, "pct": 28},
        {"name": "Ensoniq", "responses": 4, "pct": 22},
        {"name": "Sequential / DSI", "responses": 4, "pct": 22},
        {"name": "Yamaha", "responses": 3, "pct": 17},
        {"name": "Waldorf", "responses": 2, "pct": 11},
        {"name": "Access (Virus)", "responses": 2, "pct": 11},
        {"name": "Oberheim", "responses": 2, "pct": 11},
        {"name": "Casio", "responses": 1, "pct": 6},
        {"name": "ARP", "responses": 1, "pct": 6},
    ],
    "models": [
        {"name": "Roland Juno-60 / Juno-106", "mentions": 5, "knob_support": True},
        {"name": "Korg MS-20", "mentions": 4, "knob_support": False},
        {"name": "Roland Alpha Juno", "mentions": 3, "knob_support": False},
        {"name": "Moog Voyager / Memorymoog", "mentions": 3, "knob_support": False},
        {"name": "Yamaha DX7", "mentions": 2, "knob_support": True},
        {"name": "Ensoniq Fizmo / SQ-80", "mentions": 3, "knob_support": False},
        {"name": "Sequential Prophet-5 family", "mentions": 3, "knob_support": "partial"},
        {"name": "Roland D-50", "mentions": 2, "knob_support": True},
        {"name": "Roland MKS-80", "mentions": 1, "knob_support": False, "note": "Handshake request"},
        {"name": "Korg Polysix", "mentions": 1, "knob_support": False},
        {"name": "Casio CZ-1000", "mentions": 1, "knob_support": "partial"},
        {"name": "Yamaha TX81Z", "mentions": 1, "knob_support": True},
        {"name": "Korg Wavestation", "mentions": 1, "knob_support": True},
    ],
    "roadmap_signals": [
        "Roland MKS-80: respondent asked for module handshake support before bulk dumps.",
        "Roland Juno-60 appears often; many units need MIDI retrofit context.",
        "Korg MS-20 / Polysix: classic analog desks still common in bedroom segment.",
        "Ensoniq ESQ-1 / EPS / SQ-80 cluster in commercial repair-style lists.",
        "Roland JX-3P / JX-8P mentioned alongside Juno lines.",
    ],
    "pricing_notes": [
        "88.5% of respondents self-identify as personal collectors (bedroom + gear room).",
        "11.5% commercial aligns with Studio-tier positioning ($399 lifetime).",
        "Gear-room segment (47.5%) is not price-sensitive like bedroom (41%) — tier split beats a single higher Personal price.",
    ],
    "caveats": [
        "n=61 for segmentation; treat percentages as directional, not market-wide.",
        "Question 2 had 24 submissions; 6 were spam, tests, or jokes and excluded from gear analysis.",
        "Survey shown only to bipluk visitors (2.57% conversion) — biased toward people already curious about SysEx tools.",
    ],
}


def public_json() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": SURVEY_2026["title"],
        "description": (
            "First-party vintage synth owner segmentation and gear mentions "
            "from bipluk, June 25 to July 1, 2026."
        ),
        "url": SURVEY_PAGE_URL,
        "creator": {
            "@type": "Organization",
            "name": "Half Radiation LLC",
            "url": "https://bipluk",
        },
        "datePublished": "2026-07-01",
        "temporalCoverage": "2026-06-25/2026-07-01",
        "variableMeasured": ["Studio setup type", "Vintage synthesizer models on desk"],
        "size": f"{SURVEY_2026['responses_q1']} segmentation responses, "
        f"{SURVEY_2026['responses_q2_valid']} valid gear lists",
        "citation": (
            f"Half Radiation LLC, {SURVEY_2026['title']}, bipluk, {SURVEY_2026['period']}."
        ),
        "data": SURVEY_2026,
    }
