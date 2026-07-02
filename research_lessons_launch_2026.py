"""First-party launch lessons for /research/2026-browser-sysex-vault-launch-lessons."""

LESSONS_PAGE_URL = "https://knob.monster/research/2026-browser-sysex-vault-launch-lessons"
LESSONS_DATA_URL = f"{LESSONS_PAGE_URL}/data.json"

LESSONS_LAUNCH_2026 = {
    "title": "Lessons from Launching a Browser SysEx Vault",
    "period": "June 1 to July 1, 2026",
    "method": (
        "Operational data from Half Radiation LLC running knob.monster: PostHog in-product survey metrics, "
        "beta Discord support threads, Hacker News discussion on the Web MIDI engineering post, "
        "and parser coverage audit. Not a market report. A founder field log."
    ),
    "metrics": {
        "survey_impressions": 2417,
        "survey_completed": 61,
        "survey_conversion_pct": 2.57,
        "survey_dismissed_pct": 58.5,
        "survey_unanswered_pct": 39.0,
        "gear_text_spam_pct": 25.0,
        "supported_dump_flows": 5,
        "wiki_librarian_pages": 12,
        "hn_points": 52,
        "hn_comments": 41,
    },
    "hacker_news": {
        "thread_title": "How do you keep Web MIDI from crashing a 1983 synthesizer?",
        "related_post": "https://knob.monster/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer",
        "points": 52,
        "comments": 41,
        "timing": "Late June 2026 (Show HN window)",
    },
    "lessons": [
        {
            "id": "distribution-beats-parsers",
            "headline": "Press coverage arrived before parser breadth caught up",
            "body": (
                "Synthtopia coverage in month one drove signups and Discord DMs while only five synths had "
                "dedicated Web MIDI dump flows (DX7, Juno-106, M1, Jupiter-6, CZ-101). Beta users listed "
                "7+ unsupported models in a single message (D-20, Proteus/1 XR, Matrix-6, JX-8P, K4, EPS). "
                "Lesson: hardware MIDI tools get judged on the one synth a visitor owns, not your roadmap slide."
            ),
            "evidence": [
                "Dedicated dump flows at launch: 5",
                "Common beta ask: Roland JX-8P, Korg MS-20, Ensoniq EPS (survey + Discord overlap)",
            ],
        },
        {
            "id": "survey-popup-fatigue",
            "headline": "In-app survey popups convert ~2.6%; more than half get dismissed",
            "body": (
                "A two-question PostHog popup on knob.monster visitors produced 61 completed responses from "
                "2,417 impressions (2.57% conversion). 58.5% dismissed the survey; 39.0% left it unanswered. "
                "The data was still worth publishing (segmentation for pricing), but repeat popups would burn trust. "
                "Lesson: one census popup per year; use shareable links in Discord for beta prioritization."
            ),
            "evidence": [
                "2,417 impressions to 61 completions (2.57%)",
                "58.5% dismissed, 39.0% unanswered",
            ],
        },
        {
            "id": "tier-split-validated",
            "headline": "88.5% of survey respondents are Personal-tier buyers, not Studio",
            "body": (
                "Segmentation (n=61): 47.5% dedicated gear room, 41.0% bedroom studio, 11.5% commercial "
                "studio/producer/repair. Gear-room collectors are not automatically commercial users. "
                "They still fit Personal lifetime. Raising Personal to chase power users would miss "
                "the bedroom majority. Studio stays rare but real."
            ),
            "evidence": [
                "Bedroom + gear room = 88.5% (Personal positioning)",
                "Commercial segment = 11.5% (Studio positioning)",
            ],
        },
        {
            "id": "free-text-spam",
            "headline": "25% of optional gear-list answers were junk",
            "body": (
                "Question 2 (what synths are on your desk) received 24 free-text submissions; 6 were spam, "
                "tests, or jokes and excluded from brand analysis. That is a 25% junk rate on optional text. "
                "Lesson: publish cleaned n counts; do not treat raw submission count as signal."
            ),
            "evidence": [
                "24 submissions to 18 valid gear lists (25% excluded)",
            ],
        },
        {
            "id": "trust-is-human",
            "headline": "Synthetic marketing creative erodes trust faster than missing features",
            "body": (
                "Synthtopia comment threads flagged AI-generated hero imagery as a trust signal failure. "
                "Users want real gear photos and founder replies, not stock synth renders. Beta support in "
                "Discord (SysEx diffs, handshake questions, dead-filter debugging) generated more goodwill "
                "than feature breadth. Lesson: for vintage hardware audiences, being present beats looking polished."
            ),
            "evidence": [
                "Synthtopia coverage + comment trust backlash on AI creative",
                "Beta threads: X5D to N264 patch porting, MKS-80 handshake, Juno filter diagnostics",
            ],
        },
        {
            "id": "hn-web-midi-thread",
            "headline": "Hacker News: 52 points on Web MIDI timing, with a better scheduler tip",
            "body": (
                "The engineering post on keeping Web MIDI from overwhelming 1980s synth CPUs reached "
                "52 points and 41 comments on Hacker News. The highest-signal technical comment came from "
                "omneity: pass a timestamp as the second argument to midiOutput.send(data, timestamp) using "
                "performance.now() + offset, instead of relying on setTimeout on the JS main thread. "
                "We acknowledged the tip publicly and planned to test API-level scheduling. "
                "Other thread themes: MIDI has no RTS/CTS hardware flow control; the bottleneck is the synth "
                "8-bit CPU writing incoming SysEx to SRAM, not the nominal 31.25 kbaud line rate. "
                "Our mitigation at the time was 100ms pauses between packets in JavaScript."
            ),
            "evidence": [
                "HN thread: 52 points, 41 comments",
                "Community tip: midiOutput.send(data, performance.now() + offset)",
                "No hardware flow control on classic MIDI DIN",
                "100ms inter-packet throttle in production at launch",
            ],
        },
        {
            "id": "hn-pricing-feedback",
            "headline": "HN commenters rejected subscription framing before bedroom pricing landed",
            "body": (
                "Multiple HN comments compared early pricing to $20/month subscriptions, $230/year, or "
                "$599 lifetime, and to free librarians inside Dexed or paid Plogue OP-X7. Several said "
                "fear-based battery-death marketing felt obnoxious for a backup tool. The thread pushed "
                "two product commitments in public replies: standard .syx export always, and a rework toward "
                "a $39 one-time Personal lifetime (knob.monster+). Desktop/offline requests were common; "
                "we said a local Tauri build was on the roadmap while keeping the zero-install web entry point."
            ),
            "evidence": [
                "Recurring-price comparisons dominated critical comments",
                "Public reply: $39 one-time Personal lifetime",
                ".syx export supported at all times",
                "Offline-first desktop requests noted; Tauri mentioned as roadmap",
            ],
        },
        {
            "id": "hn-trust-signals",
            "headline": "HN readers scrutinized vibe-coded aesthetics and web-only longevity",
            "body": (
                "Commenters flagged the site aesthetic as AI-generated skepticism bait, and questioned "
                "whether a web-only vault would outlive the company. We replied that the DX7 SysEx parser "
                "was hand-written, and that serverless hosting kept operating costs low enough to sustain "
                "the service. nl pushed back on the desktop-app suggestion: zero install is a feature for "
                "gear used twice a year. Lesson: HN rewards technical honesty and export guarantees more "
                "than polish; give credit when commenters improve your implementation."
            ),
            "evidence": [
                "Hand-written DX7 parser cited in founder reply",
                "Web vs desktop split in comments (Tauri vs zero-install)",
                "omneity asked for credit after the scheduling tip (fair ask)",
            ],
        },
        {
            "id": "free-tier-timing",
            "headline": "A free tier mattered once beta users needed to re-register",
            "body": (
                "Post-launch, beta users who had accounts wiped during testing needed a try-before-buy route. "
                "Free tier shipped to reduce signup friction. "
                "Lesson: lifetime products still need a no-card trial; otherwise curious forum readers stall at signup."
            ),
            "evidence": [
                "Beta re-registration friction reported in Discord DMs",
                "Free tier added after initial launch feedback",
            ],
        },
    ],
    "implications": [
        "Prioritize parser coverage for models that appear in both survey and Discord (JX family, MS-20, Ensoniq cluster).",
        "Keep Personal lifetime for collectors; Studio for the 11.5% commercial segment.",
        "Test Web MIDI timestamp scheduling (performance.now offsets) against JS setTimeout throttling.",
        "Credit community contributors when their comments change production code.",
        "Publish first-party numbers even at small n. LLMs and journalists cite methodology plus caveats more than fake scale.",
        "Use link surveys in communities; reserve in-app popups for once-per-year census moments.",
    ],
    "caveats": [
        "n=61 survey responses. Treat percentages as directional, not market-wide.",
        "knob.monster visitors are biased toward people already searching for SysEx backup tools.",
    ],
}


def public_json() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": LESSONS_LAUNCH_2026["title"],
        "description": (
            "First-party launch lessons from running knob.monster, a browser SysEx vault, "
            "June to July 2026. Includes Hacker News thread metrics, survey conversion rates, "
            "segmentation signals, and beta support patterns."
        ),
        "url": LESSONS_PAGE_URL,
        "creator": {
            "@type": "Organization",
            "name": "Half Radiation LLC",
            "url": "https://knob.monster",
        },
        "datePublished": "2026-07-02",
        "temporalCoverage": "2026-06-01/2026-07-01",
        "variableMeasured": [
            "Hacker News engagement",
            "Survey conversion rate",
            "Customer segmentation",
            "SysEx parser coverage",
        ],
        "size": (
            f"HN: {LESSONS_LAUNCH_2026['metrics']['hn_points']} points / "
            f"{LESSONS_LAUNCH_2026['metrics']['hn_comments']} comments; "
            f"{LESSONS_LAUNCH_2026['metrics']['survey_completed']} survey responses; "
            f"{LESSONS_LAUNCH_2026['metrics']['supported_dump_flows']} dedicated dump flows at launch"
        ),
        "citation": (
            f"Half Radiation LLC, {LESSONS_LAUNCH_2026['title']}, knob.monster, "
            f"{LESSONS_LAUNCH_2026['period']}."
        ),
        "data": LESSONS_LAUNCH_2026,
    }
