import os
import re
import sys
import urllib.request
import urllib.parse
import json
from datetime import datetime

# Windows consoles often default to cp1252; emoji in print() then raises UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Set CWD to the directory of this script to avoid path issues
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# Add current dir to sys.path so we can import main
sys.path.insert(0, SCRIPT_DIR)

# main.py imports database.py at module load; CI has no secrets. Routes-only scan — no DB calls.
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/linkcheck")
os.environ.setdefault("SESSION_SECRET_KEY", "link-checker-ci-dummy-secret")

import settings

DISCORD_WEBHOOK_URL = settings.DISCORD_WEBHOOK_URL

try:
    from main import app, SEO_DATA
except Exception as e:
    print(f"Error importing main.py: {e}")
    # Fallback to hardcoded list if import fails
    class MockApp:
        routes = []
    app = MockApp()
    SEO_DATA = {}

# Extract valid literal paths from FastAPI app routes
VALID_LITERAL_PATHS = {
    "/",
    "/sysex-librarian-alternatives",
    "/sysex-librarian",
    "/knob-monster-vs-snoize-sysex-librarian",
    "/knob-monster-vs-midi-ox",
    "/terms",
    "/privacy",
    "/roadmap",
    "/library",
    "/resources",
    "/about",
    "/shop",
    "/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer",
    "/how-to-backup-yamaha-dx7-presets-sysex-transfer-guide",
    "/how-to-backup-roland-juno-106-presets-sysex-transfer-guide",
    "/how-to-backup-korg-m1-presets-sysex-transfer-guide",
    "/why-your-vintage-synth-battery-is-killing-your-sounds",
    "/how-to-fix-juno-106-memory-loss-troubleshooting-guide",
    "/vintage-synth-cloud-backup",
    "/audit/midiox",
    "/research/2026-vintage-synth-owner-survey",
    "/research/2026-vintage-synth-owner-survey/data.json",
    "/research/2026-browser-sysex-vault-launch-lessons",
    "/research/2026-browser-sysex-vault-launch-lessons/data.json",
    "/unsubscribe",
    "/milestones",
    "/changelog",
    "/payment-methods",
    "/status",
    "/api/geoip",
    "/login",
    "/signup",
    "/logout",
    "/home",
    "/banks",
    "/checkout",
    "/portal",
    "/sitemap.xml",
    "/robots.txt",
    "/llms.txt",
    "/.well-known/api-catalog",
    "/.well-known/oauth-authorization-server",
    "/.well-known/oauth-protected-resource",
    "/auth.md",
    "/.well-known/mcp/server-card.json",
    "/.well-known/agent-skills/index.json",
    "/openapi.json",
    "/.well-known/ucp",
    "/.well-known/acp.json"
}

# Add routes dynamically from FastAPI
for route in getattr(app, "routes", []):
    path = route.path
    # Ignore mounted static routes or path parameter routes
    if "{" not in path and "}" not in path:
        VALID_LITERAL_PATHS.add(path)

# Slugs from SEO_DATA
SEO_SLUGS = set(SEO_DATA.keys()) if SEO_DATA else {
    "dx7", "juno-106", "korg-m1", "jupiter-6", "casio-cz-101", 
    "yamaha-tx81z", "roland-d-50", "prophet-600", "oberheim-matrix-1000", 
    "yamaha-fb-01", "roland-juno-60", "korg-wavestation"
}

# Scan static directory to get valid static paths
STATIC_DIR = os.path.join(SCRIPT_DIR, "static")
VALID_STATIC_FILES = set()
if os.path.exists(STATIC_DIR):
    for root, _, files in os.walk(STATIC_DIR):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), STATIC_DIR)
            url_path = "/static/" + rel_path.replace(os.path.sep, "/")
            VALID_STATIC_FILES.add(url_path)

TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")

# Patterns to extract URLs
HREF_PATTERN = re.compile(r'href=["\']([^"\']+)["\']')
SRC_PATTERN = re.compile(r'src=["\']([^"\']+)["\']')

broken_links = []
valid_checked = 0

def check_local_path(path):
    # Parse path to strip off query parameters or hash fragments
    parsed = urllib.parse.urlparse(path)
    clean_path = parsed.path
    
    if not clean_path:
        return True # e.g. href="#features" or href="?param=1"
        
    # Check if it is a registered route
    if clean_path in VALID_LITERAL_PATHS:
        return True
        
    # Check if it is a dynamic SEO page
    slug = clean_path.lstrip("/")
    if slug in SEO_SLUGS:
        return True
        
    # Check if it is a valid static file
    if clean_path.startswith("/static/"):
        return clean_path in VALID_STATIC_FILES
        
    # Ignore dynamic templates code/variables
    if "{{" in path or "{%" in path or "request." in path or "bank." in path:
        return True
        
    # Dynamic parameterized routes
    if clean_path.startswith(("/checkout-pack/", "/banks/")):
        return True
        
    return False

# Scan templates
if os.path.exists(TEMPLATES_DIR):
    for file_name in os.listdir(TEMPLATES_DIR):
        if not file_name.endswith(".html"):
            continue
        file_path = os.path.join(TEMPLATES_DIR, file_name)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # Find all hrefs and srcs
        urls = HREF_PATTERN.findall(content) + SRC_PATTERN.findall(content)
        
        for url in urls:
            # Ignore mailto, javascript, external links (for internal integrity test), or empty/hash-only links
            if url.startswith(("mailto:", "javascript:", "#")) or not url.strip():
                continue
                
            # If it is a relative/absolute local path or domain relative
            if url.startswith("/") or not urllib.parse.urlparse(url).scheme:
                if not check_local_path(url):
                    broken_links.append({
                        "file": file_name,
                        "url": url,
                        "reason": "Not a registered route, static asset, or SEO page"
                    })
                else:
                    valid_checked += 1
            else:
                # External URL
                valid_checked += 1

print(f"Total valid links/assets checked: {valid_checked}")

if broken_links:
    print(f"\n🚨 Broken links found: {len(broken_links)}")
    for item in broken_links:
        print(f"- File: {item['file']} | Link: {item['url']} | Reason: {item['reason']}")
        
    # Construct Discord alert message
    embed_fields = []
    for item in broken_links[:10]:  # Limit to 10 to avoid Discord size limit
        embed_fields.append({
            "name": f"File: {item['file']}",
            "value": f"Link: `{item['url']}`\nReason: *{item['reason']}*",
            "inline": False
        })
        
    if len(broken_links) > 10:
        embed_fields.append({
            "name": "And more...",
            "value": f"Plus {len(broken_links) - 10} additional broken links.",
            "inline": False
        })

    payload = {
        "username": "bipluk Link Checker",
        "avatar_url": "https://bipluk/static/logo.png",
        "embeds": [{
            "title": "🚨 CI/CD Alert: Broken Links Detected!",
            "description": f"The scheduled link check found {len(broken_links)} broken internal link(s) or missing static assets in the templates.",
            "color": 15158332, # Red color
            "fields": embed_fields,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }]
    }

    try:
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
        print("Successfully sent failure alert to Discord.")
    except Exception as e:
        print(f"Failed to send alert to Discord: {e}")
        
    # Exit with code 1 to fail CI/CD build
    sys.exit(1)
else:
    print("✅ All internal links and static assets are valid!")
    sys.exit(0)
