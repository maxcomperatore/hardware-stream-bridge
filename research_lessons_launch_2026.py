"""First-party launch lessons for /research/2026-browser-sysex-vault-launch-lessons."""

LESSONS_PAGE_URL = "https://bipluk.com/research/2026-browser-sysex-vault-launch-lessons"
LESSONS_DATA_URL = f"{LESSONS_PAGE_URL}/data.json"

LESSONS_LAUNCH_2026 = {
    "title": "Lessons from Launching a Browser SysEx Vault",
    "period": "June 1 to July 1, 2026",
    "method": (
        "Operational data from Half Radiation LLC running bipluk. Metrics include PostHog survey logs, "
        "beta Discord support threads, and feedback from the Web MIDI launch thread on Hacker News. "
        "No marketing fluff. Just a founder field log."
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
        "related_post": "https://bipluk.com/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer",
        "points": 52,
        "comments": 41,
        "timing": "Late June 2026 (Show HN window)",
    },
    "lessons": [
        {
            "id": "distribution-beats-parsers",
            "headline": "You'll get press before your parsers are ready",
            "body": (
                "Synthtopia wrote about us in week one. Traffic spiked, DMs blew up, and we only supported five "
                "synthesizers (DX7, Juno-106, M1, Jupiter-6, CZ-101). Our beta users didn't care about our clean "
                "roadmap slide. They pasted lists of seven unsupported models they owned and expected them to work instantly. "
                "Lesson: in hardware tools, you're judged on the single synth a visitor owns right now."
            ),
            "evidence": [
                "Dedicated dump flows at launch: 5",
                "Common beta asks: Roland JX-8P, Korg MS-20, Ensoniq EPS (survey + Discord overlap)",
            ],
        },
        {
            "id": "survey-popup-fatigue",
            "headline": "In-app popups convert at 2%, then they burn trust",
            "body": (
                "We set up a two-question PostHog popup. Out of 2,417 visitors, 61 filled it out. That's a 2.57% "
                "conversion rate. More than half dismissed it immediately. The feedback was valuable for pricing, "
                "but doing this repeatedly makes you look like enterprise SaaS spam. Run one census a year. "
                "For beta testing, stick to Discord links."
            ),
            "evidence": [
                "2,417 impressions to 61 completions (2.57%)",
                "58.5% dismissed, 39.0% unanswered",
            ],
        },
        {
            "id": "tier-split-validated",
            "headline": "Collectors aren't commercial users",
            "body": (
                "Our survey split the audience into three: 47.5% have a dedicated gear room, 41.0% have a bedroom setup, "
                "and 11.5% run a commercial studio or repair shop. It's tempting to think a guy with twelve vintage synths "
                "is a commercial power user you can charge enterprise rates. He isn't. He's a hobbyist. "
                "Keep the personal lifetime license, and leave the commercial tier for actual business tax write-offs."
            ),
            "evidence": [
                "Bedroom + gear room = 88.5% (Personal positioning)",
                "Commercial segment = 11.5% (Studio positioning)",
            ],
        },
        {
            "id": "free-text-spam",
            "headline": "One-quarter of free-text submissions are jokes",
            "body": (
                "We asked what synths were on people's desks as a free-text field. We got 24 responses. Six were spam, "
                "testing noise, or jokes about analog warmth. That's a 25% junk rate. If you don't clean your inputs, "
                "you're building your product roadmap on internet memes. Always audit raw survey submissions."
            ),
            "evidence": [
                "24 submissions to 18 valid gear lists (25% excluded)",
            ],
        },
        {
            "id": "trust-is-human",
            "headline": "AI-generated images destroy trust instantly",
            "body": (
                "When Synthtopia covered us, the comments section didn't complain about missing features. They "
                "complained about our stock-like synth graphics. In retro gear, AI graphics look like a scam. "
                "What saved us was running a Discord server and responding to bug reports in minutes. Helping a user "
                "debug a dead Roland filter builds more goodwill than polished marketing copy."
            ),
            "evidence": [
                "Synthtopia coverage comment backlash on AI creative",
                "Beta support threads: patch porting and filter diagnostics",
            ],
        },
        {
            "id": "hn-web-midi-thread",
            "headline": "Hacker News will rewrite your scheduling code",
            "body": (
                "Our post on Web MIDI hit 52 points on Hacker News. We explained how we paced packets using JavaScript "
                "setTimeout. Within hours, a commenter named omneity pointed out a better way: pass a performance.now() "
                "timestamp directly as the second argument to the Web MIDI send function. Let the browser handle the queue. "
                "They were right. The bottleneck isn't the wire speed; it's the synth's 8-bit CPU writing to SRAM."
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
            "headline": "People hate subscriptions for utility tools",
            "body": (
                "HN readers compared our early pricing ideas to $20/month subscriptions. They pointed to free alternatives "
                "like Dexed or Snoize. They also hated battery-death marketing. We immediately committed to two things: "
                "raw .syx exports will always be free, and we launched a $39 one-time lifetime license. If you charge "
                "a subscription for a tool someone uses twice a year, they will build an open-source clone out of spite."
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
            "headline": "Vibe-coded designs look like skepticism bait",
            "body": (
                "Commenters warned that sleek, vaporwave aesthetics made us look like a landing page that would "
                "disappear in six months. They asked if a web-only vault would outlive our startup. We told them "
                "our DX7 parser was custom-written and our hosting costs were near zero. Showing our work and offering "
                "a raw export guarantee turned the thread around. Technical honesty beats visual polish every time."
            ),
            "evidence": [
                "Hand-written DX7 parser cited in founder reply",
                "Web vs desktop split in comments (Tauri vs zero-install)",
                "omneity asked for credit after the scheduling tip (fair ask)",
            ],
        },
        {
            "id": "free-tier-timing",
            "headline": "Lifetime products still need a free tier",
            "body": (
                "When we cleared beta data, we forced early testers to sign up again. Without a free tier, they hit a wall. "
                "We shipped a zero-friction trial tier. If you sell a lifetime license, you still need a way for people "
                "to test the hardware connection before pulling out a credit card."
            ),
            "evidence": [
                "Beta re-registration friction reported in Discord DMs",
                "Free tier added after initial launch feedback",
            ],
        },
    ],
    "implications": [
        "Build for the synths people actually own, not your roadmap slide.",
        "Keep the $39 personal lifetime tier; leave the $399 studio tier for tax write-offs.",
        "Pace packets with performance.now() timestamps, not setTimeout.",
        "Credit community members when they fix your scheduling code.",
        "Delete AI-generated marketing illustrations and use real gear photos.",
        "Use in-app survey popups once a year at most. Otherwise, you're just annoying your users.",
    ],
    "caveats": [
        "n=61 survey responses. Treat percentages as directional, not market-wide.",
        "bipluk visitors are biased toward people already searching for SysEx backup tools.",
    ],
}


def public_json() -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": LESSONS_LAUNCH_2026["title"],
        "description": (
            "First-party launch lessons from running bipluk, a browser SysEx vault, "
            "June to July 2026. Includes Hacker News thread metrics, survey conversion rates, "
            "segmentation signals, and beta support patterns."
        ),
        "url": LESSONS_PAGE_URL,
        "creator": {
            "@type": "Organization",
            "name": "Half Radiation LLC",
            "url": "https://bipluk.com",
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
            f"Half Radiation LLC, {LESSONS_LAUNCH_2026['title']}, bipluk, "
            f"{LESSONS_LAUNCH_2026['period']}."
        ),
        "data": LESSONS_LAUNCH_2026,
    }
