from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import io
import os
import hashlib
import bcrypt
from itsdangerous import Signer, BadSignature
import stripe
import database
import parser
import logging
import traceback
import re

# Standard robust email validation pattern
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
# Clean up/delete any generated mockup assets in static folder
def clean_old_assets():
    static_dir = r"d:\crew\experiment\static"
    targets = [
        "holo_stickers.png",
        "sram_patch.png",
        "floppy_labels.png",
        "preset_card_m1.png",
        "preset_card_dx7.png",
        "preset_card_juno.png"
    ]
    for target in targets:
        dest_path = os.path.join(static_dir, target)
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
                print(f"Deleted {dest_path}")
            except Exception as del_err:
                print(f"Error deleting {dest_path}: {del_err}")

clean_old_assets()

# Initialize standard logging
logger = logging.getLogger("knob_monster")
logging.basicConfig(level=logging.INFO)

try:
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.resources import Resource

    resource = Resource(attributes={"service.name": "knob-monster"})
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    exporter = OTLPLogExporter(
        endpoint="https://us.i.posthog.com/i/v1/logs",
        headers={"Authorization": "Bearer phc_owNMxXfxVUZpDjBJDEDasNnKQKmnAkCLGWGYW6BdKH9m"},
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    # Bridge standard library logging to OTel
    handler = LoggingHandler(logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
except Exception as e:
    logger.error(f"Failed to initialize PostHog OTLP Logging: {e}")

# PostHog Python SDK — Error Tracking & Exception Capture
try:
    from posthog import Posthog
    posthog_client = Posthog(
        project_api_key="phc_owNMxXfxVUZpDjBJDEDasNnKQKmnAkCLGWGYW6BdKH9m",
        host="https://e.knob.monster",
        enable_exception_autocapture=True,
    )
except Exception as e:
    posthog_client = None
    logger.error(f"Failed to initialize PostHog SDK: {e}")

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1519380424550256660/VetDI5944BLsDv8bJx-1zWC55EPpVsUaQbFykMbUgWj7O_9K9_q7xWzwxQaziXCC3Fg_"

def _sync_send_alert(event_type: str, message: str, properties: dict = None, distinct_id: str = "system"):
    # 1. PostHog client capture
    if posthog_client:
        try:
            posthog_client.capture(
                distinct_id=distinct_id,
                event=event_type,
                properties=properties or {}
            )
        except Exception as e:
            logger.error(f"PostHog capture failed: {e}")

    # 2. Discord Webhook
    try:
        import urllib.request
        import json
        from datetime import datetime

        # Determine color based on event type
        color = 0x3498db  # Default info blue
        if any(w in event_type for w in ["signup", "register", "activated", "success"]):
            color = 0x2ecc71  # Green
        elif any(w in event_type for w in ["failed", "error", "exception", "unauthorized"]):
            color = 0xe74c3c  # Red
        elif any(w in event_type for w in ["delete", "cancel"]):
            color = 0xe67e22  # Orange

        embed = {
            "title": event_type.replace("_", " ").title(),
            "description": message,
            "color": color,
            "fields": [],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "footer": {
                "text": "knob.monster alerts",
                "icon_url": "https://knob.monster/static/logo.svg"
            }
        }

        if properties:
            for k, v in properties.items():
                val_str = str(v) if v is not None else "N/A"
                if len(val_str) > 1024:
                    val_str = val_str[:1021] + "..."
                embed["fields"].append({
                    "name": k.replace("_", " ").title(),
                    "value": val_str,
                    "inline": len(val_str) < 40
                })

        payload = {
            "username": "Knob Monster Bot",
            "avatar_url": "https://knob.monster/static/logo.png",
            "embeds": [embed]
        }

        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
    except Exception as e:
        logger.error(f"Discord webhook notification failed: {e}")

def trigger_alert(event_type: str, message: str, properties: dict = None, distinct_id: str = "system"):
    """
    Fire-and-forget alert to PostHog and Discord.
    Runs in a background thread to prevent blocking the request.
    """
    import threading
    thread = threading.Thread(target=_sync_send_alert, args=(event_type, message, properties, distinct_id))
    thread.daemon = True
    thread.start()

app = FastAPI(title="Knob Monster - Vintage Synth Patch Manager")

from datetime import datetime

@app.exception_handler(Exception)
async def posthog_exception_handler(request: Request, exc: Exception):
    """Capture all unhandled exceptions and send to PostHog error tracking."""
    distinct_id = "anonymous"
    session_cookie = request.cookies.get("session_user")
    if session_cookie:
        try:
            distinct_id = cookie_signer.unsign(session_cookie.encode()).decode()
        except Exception:
            pass
    if posthog_client:
        try:
            posthog_client.capture_exception(
                exc,
                distinct_id=distinct_id,
                properties={
                    "url": str(request.url),
                    "method": request.method,
                    "traceback": traceback.format_exc(),
                }
            )
        except Exception:
            pass
    trigger_alert(
        "unhandled_exception",
        f"Unhandled Exception in request: `{exc.__class__.__name__}: {str(exc)}`",
        {
            "url": str(request.url),
            "method": request.method,
            "exception": exc.__class__.__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc()
        },
        distinct_id=distinct_id
    )
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return HTMLResponse(content="<h1>500 Internal Server Error</h1>", status_code=500)

@app.middleware("http")
async def earth_day_middleware(request: Request, call_next):
    # Support testing/preview via query param (?earthday=true) or environment variable
    query_param_trigger = False
    try:
        query_param_trigger = request.query_params.get("earthday") == "true"
    except Exception:
        pass
        
    force_earth_day = query_param_trigger or os.environ.get("FORCE_EARTH_DAY") == "true"
    
    # Check date: April 22nd
    now = datetime.now()
    is_earth_day = (now.month == 4 and now.day == 22) or force_earth_day
    
    # Don't block static files, favicon, robots.txt, sitemap.xml, or llms.txt so crawlers and assets work
    is_excluded = (
        request.url.path.startswith("/static") or 
        request.url.path in ["/favicon.ico", "/robots.txt", "/sitemap.xml", "/llms.txt"]
    )
    if is_earth_day and not is_excluded:
        trigger_alert(
            "earth_day_warning",
            f"User with IP `{request.client.host if request.client else 'unknown'}` blocked by Earth Day middleware.",
            {
                "ip_address": request.client.host if request.client else "unknown",
                "path": request.url.path,
                "user_agent": request.headers.get("user-agent", "")
            },
            distinct_id="earth_day_block"
        )
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KNOB.MONSTER | Closed for Earth Day</title>
    <link href="https://api.fontshare.com/v2/css?f[]=geist@100,200,300,400,500,600,700,800,900&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Geist', sans-serif; }
        .font-pixel { font-family: 'Silkscreen', monospace; }
        .dithered {
            image-rendering: pixelated;
        }
    </style>
</head>
<body class="bg-black text-zinc-400 flex flex-col items-center justify-center min-h-screen p-6 text-center select-none selection:bg-zinc-800 selection:text-white">
    <div class="max-w-md space-y-8">
        <!-- Microbe Logo -->
        <div class="flex justify-center">
            <img src="/static/logo.svg" id="earth-day-logo" alt="Microbe Logo" class="h-28 w-auto object-contain dithered cursor-pointer transition-all duration-150 ease-out opacity-60" style="transform-style: preserve-3d; backface-visibility: hidden;">
        </div>
        
        <div class="space-y-4">
            <h1 class="text-xl font-pixel uppercase tracking-widest text-emerald-500">GO TOUCH GRASS.</h1>
            <p class="text-sm text-zinc-300 leading-relaxed max-w-sm mx-auto">
                Today is Earth Day. We have temporarily disabled our platform to save a negligible amount of coal-fired electricity and pull off a cheap corporate PR stunt.
            </p>
            <p class="text-sm text-zinc-300 leading-relaxed max-w-sm mx-auto">
                But more importantly: you have spent far too many consecutive hours staring at Web MIDI transfer logs and hoarding digital soundbanks for vintage synthesizers.
            </p>
            <p class="text-sm font-bold text-white leading-relaxed max-w-sm mx-auto">
                Go outside. Touch some actual grass. Try to interact with a real plant or another biological organism.
            </p>
        </div>
        
        <div class="pt-6 border-t border-zinc-900 text-[10px] font-mono text-zinc-650">
            knob.monster will wake up automatically tomorrow. Enjoy your temporary eviction from the cloud.
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", () => {
            const logo = document.getElementById('earth-day-logo');
            if (logo) {
                logo.addEventListener('mousemove', (e) => {
                    const rect = logo.getBoundingClientRect();
                    const x = e.clientX - rect.left - (rect.width / 2);
                    const y = e.clientY - rect.top - (rect.height / 2);
                    
                    const rotX = -(y / (rect.height / 2)) * 35;
                    const rotY = (x / (rect.width / 2)) * 35;
                    
                    logo.style.transform = `perspective(600px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.25)`;
                    logo.style.filter = `drop-shadow(${rotY * -0.6}px ${rotX * 0.6}px 12px rgba(255, 255, 255, 0.15)) drop-shadow(0 15px 30px rgba(0, 0, 0, 0.8))`;
                    logo.style.opacity = "1";
                });
                
                logo.addEventListener('mouseleave', () => {
                    logo.style.transform = `perspective(600px) rotateX(0deg) rotateY(0deg) scale(1)`;
                    logo.style.filter = `none`;
                    logo.style.opacity = "0.6";
                });
            }
        });
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html_content, status_code=503)
        
    return await call_next(request)

# Absolute path of the directory containing main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Intercept logo requests to serve the microbe SVG
@app.get("/static/logo.svg")
async def get_logo_avif():
    logo_path = os.path.join(BASE_DIR, "static", "logo.svg")
    if os.path.exists(logo_path):
        with open(logo_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        return Response(content=svg_content, media_type="image/svg+xml")
    raise HTTPException(status_code=404)

@app.get("/static/logo.png")
async def get_logo_png():
    logo_path = os.path.join(BASE_DIR, "static", "logo.svg")
    if os.path.exists(logo_path):
        with open(logo_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        return Response(content=svg_content, media_type="image/svg+xml")
    raise HTTPException(status_code=404)

# Mount Static Files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Configure Stripe key & fallback mock mode
STRIPE_SECRET_KEY = os.environ.get(
    "STRIPE_SECRET_KEY",
    "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"
)
STRIPE_WEBHOOK_SECRET = os.environ.get(
    "STRIPE_WEBHOOK_SECRET",
    "whsec_AWPK4gRmIUdFkUXAzn9IMufmJF5pW5wR"
)
stripe.api_key = STRIPE_SECRET_KEY

STRIPE_PRICE_ID_YEARLY = os.environ.get("STRIPE_PRICE_ID_YEARLY", "price_1TmkVKLuSQGuB7eyU0JeuYr2")
STRIPE_PRICE_ID_MONTHLY = os.environ.get("STRIPE_PRICE_ID_MONTHLY", "price_1TmkUzLuSQGuB7eytGvepyWd")
STRIPE_PRICE_ID_LIFETIME = os.environ.get("STRIPE_PRICE_ID_LIFETIME", "price_1TnPsgLuSQGuB7eyPbyJSarD")
BASE_URL = "https://knob.monster"

# SMTP configuration with Resend defaults
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = os.environ.get("SMTP_PORT", "587")
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", "knob.monster <vault@knob.monster>")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    database.init_db()

# Secure Cookie Session signing key
SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    if os.environ.get("VERCEL") == "1":
        raise RuntimeError("SESSION_SECRET_KEY environment variable is required in production!")
    SESSION_SECRET_KEY = "knob_monster_super_secure_default_session_secret_998822"
cookie_signer = Signer(SESSION_SECRET_KEY)

def sign_session_cookie(email: str) -> str:
    return cookie_signer.sign(email.encode('utf-8')).decode('utf-8')

def verify_session_cookie(signed_cookie: str) -> str:
    try:
        return cookie_signer.unsign(signed_cookie.encode('utf-8')).decode('utf-8')
    except BadSignature:
        return None

# Password hashing helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    # Fallback to old unsalted SHA-256 for existing users
    old_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return old_hash == hashed_password

# Version-safe TemplateResponse wrapper to support both Starlette >= 0.28 and Starlette < 0.28
def render_template(template_name: str, request: Request, context: dict = None, status_code: int = 200):
    if context is None:
        context = {}
    context["request"] = request
    
    # Check if we are in Knob Monster's Birthday Week (May 31st to June 6th)
    query_birthday = False
    query_christmas = False
    query_halloween = False
    try:
        query_birthday = request.query_params.get("birthday") == "true"
        query_christmas = request.query_params.get("christmas") == "true"
        query_halloween = request.query_params.get("halloween") == "true"
    except Exception:
        pass
    force_birthday = query_birthday or os.environ.get("FORCE_BIRTHDAY") == "true"
    force_christmas = query_christmas or os.environ.get("FORCE_CHRISTMAS") == "true"
    force_halloween = query_halloween or os.environ.get("FORCE_HALLOWEEN") == "true"
    
    now = datetime.now()
    is_birthday = (now.month == 5 and now.day == 31) or (now.month == 6 and 1 <= now.day <= 6) or force_birthday
    context["is_birthday_week"] = is_birthday
    context["birthday_code"] = os.environ.get("BIRTHDAY_DISCOUNT_CODE", "KNOB20")
    
    is_christmas = (now.month == 12 and 18 <= now.day <= 31) or (now.month == 1 and now.day == 1) or force_christmas
    context["is_christmas_week"] = is_christmas
    context["christmas_code"] = os.environ.get("CHRISTMAS_DISCOUNT_CODE", "XMAS20")
    
    is_halloween = (now.month == 10 and 24 <= now.day <= 31) or force_halloween
    context["is_halloween_week"] = is_halloween
    
    # Dynamically calculate the site's age (founded in 2026)
    # 2026 = Launch, 2027 = Turning 1, etc.
    birthday_age = now.year - 2026
    context["birthday_age"] = birthday_age
    
    import inspect
    sig = inspect.signature(templates.TemplateResponse)
    if "request" in sig.parameters:
        return templates.TemplateResponse(request=request, name=template_name, context=context, status_code=status_code)
    else:
        return templates.TemplateResponse(name=template_name, context=context, status_code=status_code)

# Session resolver
def get_current_user(request: Request):
    signed_cookie = request.cookies.get("session_user")
    if not signed_cookie:
        return None
    email = verify_session_cookie(signed_cookie)
    if not email:
        return None
    return database.get_user_by_email(email)

# Custom 404 Error handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return render_template("404.html", request, status_code=404)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)

SEO_DATA = {
    "dx7": {
        "title": "How to Turn Off Memory Protect on Yamaha DX7 | knob.monster",
        "description": "Learn how to turn off memory protect on the Yamaha DX7 and enable SysEx data reception to back up your patches.",
        "keywords": "how to turn off memory protect on yamaha dx7, disable memory protect dx7, yamaha dx7 sysex settings, dx7 internal memory protection",
        "synth_name": "Yamaha DX7",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha DX7.</span>",
        "hero_subtitle": "The ultimate Yamaha DX7 online librarian. Back up, search, and recall Yamaha DX7 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
,
        "docs": {"title": "How to Turn Off Memory Protect on the Yamaha DX7", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Yamaha DX7 requires you to explicitly disable internal memory protection and enable SysEx data reception before you can back up or restore patches.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press the <strong class=\"text-white\">FUNCTION</strong> button on the front panel.</li>\n    <li>Press button <strong class=\"text-white\">8</strong> (labeled MEMORY PROTECT INTERNAL).</li>\n    <li>The LCD screen will display <code>MEMORY PROTECT INTERNAL: ON</code>.</li>\n    <li>Press the <strong class=\"text-white\">-1/NO</strong> button to change it to <code>OFF</code>.</li>\n    <li>Press button <strong class=\"text-white\">8</strong> again to access the SYS INFO screen.</li>\n    <li>Ensure the screen says <code>SYS INFO: AVAIL</code>. If it says <code>UNAVAIL</code>, press <strong class=\"text-white\">+1/YES</strong> to toggle it.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your DX7 is now ready to send and receive SysEx dumps.</p>"}    },
    "juno-106": {
        "title": "How to Turn Off Memory Protect & Enable SysEx on Roland Juno-106",
        "description": "Learn the secret rear panel switch settings to turn off memory protect and enable SysEx MIDI dumps on the Roland Juno-106.",
        "keywords": "how to turn off memory protect on roland juno 106, roland juno 106 sysex switch, juno 106 midi channel 3, juno 106 patch dump",
        "synth_name": "Roland Juno-106",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland Juno-106.</span>",
        "hero_subtitle": "The easiest way to manage Roland Juno-106 SysEx backup files directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
,
        "docs": {"title": "How to Enable SysEx & Turn Off Memory Protect on Roland Juno-106", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Roland Juno-106 uses a hidden function switch on the rear panel to enable SysEx communication.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Locate the <strong class=\"text-white\">MEMORY PROTECT</strong> switch on the rear panel of the synthesizer and slide it to the <strong class=\"text-white\">OFF</strong> position.</li>\n    <li>Locate the <strong class=\"text-white\">MIDI CH</strong> switch (Function Switch) on the rear panel.</li>\n    <li>Slide the MIDI CH switch to position <strong class=\"text-white\">III (3)</strong>. This is the secret mode that enables the Juno-106 to transmit and receive exclusive SysEx patch data.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your Juno-106 is now ready to dump and load patches.</p>"}    },
    "korg-m1": {
        "title": "How to Turn Off Memory Protect on Korg M1",
        "description": "Step-by-step guide to disabling memory protection for programs and combinations on the Korg M1 to receive SysEx patches.",
        "keywords": "how to turn off memory protect on korg m1, korg m1 global midi settings, korg m1 exclusive allow, disable memory protect korg m1",
        "synth_name": "Korg M1",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Korg M1.</span>",
        "hero_subtitle": "A fast browser utility for Korg M1 patch recall. Back up, search, and recall Korg M1 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
,
        "docs": {"title": "How to Turn Off Memory Protect on Korg M1", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Korg M1 protects its internal programs and combinations by default. You must disable this in the Global menu.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press the <strong class=\"text-white\">GLOBAL</strong> button to enter the Global mode.</li>\n    <li>Press the <strong class=\"text-white\">PAGE +</strong> button until you reach Page 5 (MIDI GLOBAL).</li>\n    <li>Use the cursor buttons and value slider to set <strong class=\"text-white\">MIDI EXA</strong> (Exclusive Allow) to <strong class=\"text-white\">ENA</strong> (Enabled).</li>\n    <li>Press the <strong class=\"text-white\">PAGE +</strong> button to reach Page 6 (MEMORY PROTECT).</li>\n    <li>Set both <strong class=\"text-white\">PROG</strong> (Program) and <strong class=\"text-white\">COMBI</strong> (Combination) to <strong class=\"text-white\">OFF</strong>.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your Korg M1 can now receive SysEx patch banks.</p>"}    },
    "jupiter-6": {
        "title": "How to Turn Off Memory Protect on Roland Jupiter-6",
        "description": "How to disable tape memory protect on the Roland Jupiter-6 (and Europa mod) to send and receive SysEx patch data.",
        "keywords": "how to turn off memory protect on roland jupiter 6, jupiter 6 tape memory protect, europa mod jupiter 6 sysex",
        "synth_name": "Roland Jupiter-6",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland Jupiter-6.</span>",
        "hero_subtitle": "The easiest way to manage Roland Jupiter-6 and Europa-modded SysEx backups directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
,
        "docs": {"title": "How to Turn Off Memory Protect on Roland Jupiter-6", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">For the stock Roland Jupiter-6 and Europa-modded units, memory protection must be bypassed to write new patches via SysEx.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Locate the <strong class=\"text-white\">TAPE MEMORY PROTECT</strong> switch on the rear panel of the Jupiter-6.</li>\n    <li>Slide the switch to the <strong class=\"text-white\">OFF</strong> position.</li>\n    <li>If you have the <strong class=\"text-white\">Europa</strong> modification, enter the Europa menu and navigate to the MIDI configuration page to ensure SysEx (System Exclusive) Rx/Tx is set to ON.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your Jupiter-6 is now unprotected and ready for MIDI SysEx transfers.</p>"}    },
    "casio-cz-101": {
        "title": "How to Turn Off Memory Protect on Casio CZ-101",
        "description": "Learn how to toggle the physical memory protect switch on the Casio CZ-101 to enable Phase Distortion patch dumps.",
        "keywords": "how to turn off memory protect on casio cz 101, casio cz-101 protect button, cz-101 sysex settings",
        "synth_name": "Casio CZ-101",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Casio CZ-101.</span>",
        "hero_subtitle": "Back up, organize, and restore CZ-101 Phase Distortion patches directly from your web browser. Zero setup, zero drivers, instant MIDI dumps."
,
        "docs": {"title": "How to Turn Off Memory Protect on Casio CZ-101", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Casio CZ-101 uses a physical button on the front panel to toggle memory protection.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Locate the small <strong class=\"text-white\">PROTECT</strong> button on the bottom left or rear of the CZ-101 (depending on the revision).</li>\n    <li>Press the button to toggle memory protection. Some units have a recessed switch that requires a pen or small screwdriver to switch to <strong class=\"text-white\">OFF</strong>.</li>\n    <li>Press the <strong class=\"text-white\">MIDI</strong> button to enter MIDI settings and ensure that the basic channel is set correctly and SysEx is not filtered.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your Casio CZ-101 can now accept Phase Distortion patch dumps.</p>"}    },
    "yamaha-tx81z": {
        "title": "How to Turn Off Memory Protect on Yamaha TX81Z",
        "description": "Step-by-step guide to disabling memory protect in the Utility menu of the Yamaha TX81Z to receive FM patches like Lately Bass.",
        "keywords": "how to turn off memory protect on yamaha tx81z, disable mem protect tx81z, tx81z utility menu sysex",
        "synth_name": "Yamaha TX81Z",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha TX81Z.</span>",
        "hero_subtitle": "Quickly manage your TX81Z patches and that legendary Lately Bass patch directly from your browser. Zero setup, zero drivers, instant Web MIDI dump."
,
        "docs": {"title": "How to Turn Off Memory Protect on Yamaha TX81Z", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">To restore your Lately Bass and other FM patches, you need to disable memory protection in the Utility menu.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press the <strong class=\"text-white\">PLAY/PERFORM</strong> button to ensure you are in normal play mode.</li>\n    <li>Press the <strong class=\"text-white\">UTILITY</strong> button multiple times until you see <code>Mem Protect</code> on the LCD screen.</li>\n    <li>The screen will likely show <code>Mem Protect: ON</code>.</li>\n    <li>Press the <strong class=\"text-white\">-1/NO/OFF</strong> button to change the setting to <code>OFF</code>.</li>\n    <li>Press the <strong class=\"text-white\">UTILITY</strong> button until you reach the <code>MIDI</code> settings page, and ensure <code>Exclusive</code> is set to <code>ON</code>.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your TX81Z is now ready to receive SysEx data.</p>"}    },
    "roland-d-50": {
        "title": "How to Turn Off Memory Protect on Roland D-50",
        "description": "How to turn off memory protection and enable system exclusive (Exclu) messages on the Roland D-50.",
        "keywords": "how to turn off memory protect on roland d-50, d-50 exclu setting, disable memory protect d50",
        "synth_name": "Roland D-50",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland D-50.</span>",
        "hero_subtitle": "Manage your classic Linear Arithmetic soundbanks and patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
,
        "docs": {"title": "How to Turn Off Memory Protect on Roland D-50", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">Before transferring Linear Arithmetic patches, the D-50 requires memory protect to be turned off.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press and hold the <strong class=\"text-white\">TUNE/FUNCTION</strong> button.</li>\n    <li>While holding, press the <strong class=\"text-white\">MIDI</strong> button.</li>\n    <li>Use the joystick or value buttons to navigate to the <strong class=\"text-white\">Protect</strong> setting.</li>\n    <li>Change the memory protect setting to <strong class=\"text-white\">OFF</strong>.</li>\n    <li>Ensure that the <strong class=\"text-white\">Exclu</strong> (System Exclusive) setting is set to <strong class=\"text-white\">ON</strong> so the synth accepts MIDI dumps.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your D-50 is now ready for patch transfers.</p>"}    },
    "prophet-600": {
        "title": "How to Turn Off Memory Protect on Prophet-600",
        "description": "Guide to disabling the memory protect switch on the Sequential Circuits Prophet-600 (stock and GliGli firmware) for SysEx transfers.",
        "keywords": "how to turn off memory protect on prophet 600, prophet 600 gligli sysex, disable memory protect prophet-600",
        "synth_name": "Prophet-600",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Prophet-600.</span>",
        "hero_subtitle": "Back up, organize, and recall Prophet-600 patches (stock or GliGli modded) directly from your browser. Zero setup, zero drivers."
,
        "docs": {"title": "How to Turn Off Memory Protect on Prophet-600", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Prophet-600 (both stock and GliGli-modded) requires memory protect to be disabled before receiving SysEx.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Locate the <strong class=\"text-white\">MEMORY PROTECT</strong> switch on the front panel (often near the preset/keypad section).</li>\n    <li>Flick the switch to the <strong class=\"text-white\">OFF</strong> position.</li>\n    <li>If you are using the <strong class=\"text-white\">GliGli</strong> firmware, press the <strong class=\"text-white\">TUNE</strong> button and use the keypad to ensure MIDI SysEx RX is enabled according to the GliGli manual.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your Prophet-600 is now ready to receive presets.</p>"}    },
    "oberheim-matrix-1000": {
        "title": "How to Turn Off Memory Protect on Oberheim Matrix-1000",
        "description": "Learn how to toggle memory protection for the RAM user banks on the Oberheim Matrix-1000.",
        "keywords": "how to turn off memory protect on oberheim matrix 1000, matrix 1000 user bank protect, matrix 1000 sysex",
        "synth_name": "Oberheim Matrix-1000",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Matrix-1000.</span>",
        "hero_subtitle": "The easiest way to manage Oberheim Matrix-1000 and Matrix-6 soundbanks directly from your browser. Zero setup, zero drivers."
,
        "docs": {"title": "How to Turn Off Memory Protect on Oberheim Matrix-1000", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Matrix-1000 has banks 0-199 available as RAM (user rewritable), while 200-999 are ROM (read-only). You must enable memory protect off for the RAM banks.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press the <strong class=\"text-white\">Select</strong> button until the <strong class=\"text-white\">Bank/Protect</strong> LED is lit.</li>\n    <li>Press the <strong class=\"text-white\">+</strong> or <strong class=\"text-white\">-</strong> buttons to toggle the memory protect status. The display should read <code>U F</code> (Unprotected) instead of <code>P F</code> (Protected).</li>\n    <li>Ensure you are writing to a user bank (000-199).</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your Matrix-1000 can now have its user banks overwritten via SysEx.</p>"}    },
    "yamaha-fb-01": {
        "title": "How to Turn Off Memory Protect on Yamaha FB-01",
        "description": "How to enable system exclusive messages in the system setup of the Yamaha FB-01 sound module.",
        "keywords": "how to turn off memory protect on yamaha fb 01, fb-01 system setup sysex, yamaha fb01 exclusive enable",
        "synth_name": "Yamaha FB-01",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha FB-01.</span>",
        "hero_subtitle": "The easiest way to manage Yamaha FB-01 patches and soundbanks directly from your browser. Zero setup, zero drivers."
,
        "docs": {"title": "How to Turn Off Memory Protect on Yamaha FB-01", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Yamaha FB-01 requires system exclusive messages to be enabled in its system setup.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press the <strong class=\"text-white\">SYSTEM SETUP</strong> button.</li>\n    <li>Use the data entry buttons to scroll through the system parameters until you find the <strong class=\"text-white\">SysEx</strong> or <strong class=\"text-white\">Exclusive</strong> setting.</li>\n    <li>Change the value to <strong class=\"text-white\">ON</strong> or <strong class=\"text-white\">ENA</strong> (Enabled).</li>\n    <li>Ensure that the memory protect setting (if present in your firmware revision) is turned <strong class=\"text-white\">OFF</strong>.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your FB-01 is now ready to receive FM patches.</p>"}    },
    "roland-juno-60": {
        "title": "How to Turn Off Memory Protect on Roland Juno-60",
        "description": "Guide to turning off memory protect on the Roland Juno-60, including settings for MIDI-retrofitted units (Minerva, Tubbutec).",
        "keywords": "how to turn off memory protect on roland juno 60, juno 60 memory protect switch, tubbutec juno 60 sysex",
        "synth_name": "Roland Juno-60",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland Juno-60.</span>",
        "hero_subtitle": "For MIDI-modded Juno-60 synths, manage and backup your patch libraries directly from your browser. Zero setup, zero drivers."
,
        "docs": {"title": "How to Turn Off Memory Protect on Roland Juno-60", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The stock Juno-60 does not have MIDI, but if you have a MIDI retrofit (like Minerva or Tubbutec), you must disable the hardware memory protect.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Locate the <strong class=\"text-white\">MEMORY PROTECT</strong> switch on the rear panel of the Juno-60.</li>\n    <li>Slide the switch to the <strong class=\"text-white\">OFF</strong> position.</li>\n    <li>If using a MIDI retrofit, consult your mod's manual (e.g., press and hold the <strong class=\"text-white\">LFO TRIG</strong> button on Tubbutec) to enter the config menu and enable SysEx receive.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your modded Juno-60 is now ready for MIDI SysEx patches.</p>"}    },
    "korg-wavestation": {
        "title": "How to Turn Off Memory Protect on Korg Wavestation",
        "description": "Step-by-step guide to disabling internal and card memory protect on the Korg Wavestation in the Global menu.",
        "keywords": "how to turn off memory protect on korg wavestation, wavestation global protect, disable memory protect wavestation",
        "synth_name": "Korg Wavestation",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Korg Wavestation.</span>",
        "hero_subtitle": "The easiest way to manage Korg Wavestation soundbanks and wave sequences directly from your browser. Zero setup, zero drivers.",
        "docs": {"title": "How to Turn Off Memory Protect on Korg Wavestation", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">To restore wave sequences and patches, the Korg Wavestation must have its memory protect turned off.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press the <strong class=\"text-white\">GLOBAL</strong> button on the front panel.</li>\n    <li>Use the soft keys and page buttons to navigate to the <strong class=\"text-white\">Protect</strong> page.</li>\n    <li>Set both <strong class=\"text-white\">Internal Protect</strong> and <strong class=\"text-white\">Card Protect</strong> (if applicable) to <strong class=\"text-white\">OFF</strong>.</li>\n    <li>Navigate to the <strong class=\"text-white\">MIDI</strong> page and make sure <strong class=\"text-white\">SysEx Receive</strong> is set to <strong class=\"text-white\">ON</strong>.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your Korg Wavestation is now ready to receive patches via MIDI.</p>"}    }
}

# --- Marketing & Auth Pages ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    user_count = 6
    total_patches = 1000
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM patches;")
        total_patches = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        logger.error(f"Failed to query user and patches count: {e}")
    remaining_slots = max(0, 105 - user_count)
    return render_template("landing.html", request, {"user": user, "remaining_slots": remaining_slots, "total_patches": total_patches})

@app.get("/sysex-librarian-alternatives", response_class=HTMLResponse)
async def sysex_librarian_alternatives(request: Request):
    user = get_current_user(request)
    return render_template("sysex_librarian.html", request, {"user": user})

@app.get("/sysex-librarian", response_class=HTMLResponse)
async def sysex_librarian_redirect():
    return RedirectResponse(url="/sysex-librarian-alternatives", status_code=301)

@app.get("/knob-monster-vs-snoize-sysex-librarian", response_class=HTMLResponse)
async def snoize_comparison(request: Request):
    user = get_current_user(request)
    return render_template("snoize_alternatives.html", request, {"user": user})

@app.get("/knob-monster-vs-midi-ox", response_class=HTMLResponse)
async def midi_ox_comparison(request: Request):
    user = get_current_user(request)
    return render_template("midi_ox_alternatives.html", request, {"user": user})

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return render_template("terms.html", request)

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return render_template("privacy.html", request)

@app.get("/roadmap", response_class=HTMLResponse)
async def roadmap_page(request: Request):
    return RedirectResponse(url="/resources", status_code=301)

@app.get("/library", response_class=HTMLResponse)
async def library_redirect_page(request: Request):
    return RedirectResponse(url="/resources", status_code=301)

@app.get("/resources", response_class=HTMLResponse)
async def resources_page(request: Request):
    user = get_current_user(request)
    wiki_synths = []
    for slug, data in SEO_DATA.items():
        name = data.get("synth_name", slug)
        # Infer brand
        brand = "Generic"
        if "yamaha" in name.lower():
            brand = "Yamaha"
        elif "roland" in name.lower():
            brand = "Roland"
        elif "korg" in name.lower():
            brand = "Korg"
        elif "casio" in name.lower():
            brand = "Casio"
        elif "prophet" in name.lower():
            brand = "Sequential"
        elif "oberheim" in name.lower():
            brand = "Oberheim"
        
        wiki_synths.append({
            "slug": slug,
            "name": name,
            "brand": brand,
            "description": data.get("description", "")
        })
    return render_template("resources.html", request, {"user": user, "wiki_synths": wiki_synths})

@app.get("/about", response_class=HTMLResponse)
async def about_redirect_page(request: Request):
    return RedirectResponse(url="/shop", status_code=301)

@app.get("/milestones", response_class=HTMLResponse)
async def milestones_redirect_page(request: Request):
    return RedirectResponse(url="/shop", status_code=301)

@app.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request):
    try:
        clean_old_assets()
    except Exception as e:
        print(f"Error cleaning assets on request: {e}")
    user = get_current_user(request)
    packs = [
        {
            "id": "m1_matrix",
            "name": "Korg M1: Off the Matrix",
            "synth": "Korg M1",
            "price": "$9.00",
            "description": "Premium overrides of sample keymaps carefully programmed over 20 years. Features Trident Strings and analog emulations.",
            "patches_count": 32,
            "demo_patches": ["Cyber Gate", "HousePiano", "Ethereal", "TridentStr", "Glassy Pad", "Obese Poly"],
        },
        {
            "id": "dx7_retro",
            "name": "Yamaha DX7: Classic FM Leads & Basses",
            "synth": "Yamaha DX7",
            "price": "$9.00",
            "description": "Punchy FM basses, crystal-clear bell leads, and classic 80s electric pianos. Optimized for live MIDI performance.",
            "patches_count": 32,
            "demo_patches": ["Super Bass", "Chime Bell", "FM Rhodes", "Synth Brass", "Sitar Glide", "Atmosphere"],
        },
        {
            "id": "juno_nostalgia",
            "name": "Roland Juno-106: Nostalgia Plucks & Pads",
            "synth": "Roland Juno-106",
            "price": "$9.00",
            "description": "Warm, chorus-drenched analog pads, snap plucks, and classic 80s sci-fi SFX. Relive the golden age of ambient.",
            "patches_count": 32,
            "demo_patches": ["Nostalgia", "Chorused Pad", "Snap Pluck", "Space Wind", "Analog Sweep", "Sub Bass"],
        }
    ]
    return render_template("shop.html", request, {"user": user, "packs": packs})

@app.get("/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer", response_class=HTMLResponse)
async def blog_web_midi_page(request: Request):
    user = get_current_user(request)
    return render_template("blog_web_midi.html", request, {"user": user})

@app.get("/how-to-backup-yamaha-dx7-presets-sysex-transfer-guide", response_class=HTMLResponse)
async def guide_dx7_page(request: Request):
    user = get_current_user(request)
    return render_template("guide_dx7.html", request, {"user": user})

@app.get("/how-to-backup-roland-juno-106-presets-sysex-transfer-guide", response_class=HTMLResponse)
async def guide_juno106_page(request: Request):
    user = get_current_user(request)
    return render_template("guide_juno106.html", request, {"user": user})

@app.get("/how-to-backup-korg-m1-presets-sysex-transfer-guide", response_class=HTMLResponse)
async def guide_m1_page(request: Request):
    user = get_current_user(request)
    return render_template("guide_m1.html", request, {"user": user})

@app.get("/why-your-vintage-synth-battery-is-killing-your-sounds", response_class=HTMLResponse)
async def guide_battery_page(request: Request):
    user = get_current_user(request)
    return render_template("guide_battery.html", request, {"user": user})

@app.get("/how-to-fix-juno-106-memory-loss-troubleshooting-guide", response_class=HTMLResponse)
async def guide_juno_troubleshooting_page(request: Request):
    user = get_current_user(request)
    return render_template("guide_juno_troubleshooting.html", request, {"user": user})

@app.get("/changelog")
async def changelog_redirect():
    return RedirectResponse(url="/shop", status_code=301)

@app.get("/payment-methods", response_class=HTMLResponse)
async def payment_methods_page(request: Request):
    user = get_current_user(request)
    return render_template("payment_methods.html", request, {"user": user})

@app.get("/status")
async def status_page():
    return {
        "status": "operational",
        "uptime": "99.99%",
        "services": {
            "web_frontend": "operational",
            "database_cluster": "operational",
            "web_midi_bridge": "operational",
            "stripe_payment_gateway": "operational"
        }
    }

@app.get("/api/geoip")
async def get_geoip(request: Request):
    # Try to find the client IP
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # Check headers for reverse proxy IPs
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # Get the first IP in the list
        client_ip = x_forwarded_for.split(",")[0].strip()
    else:
        cf_connecting_ip = request.headers.get("cf-connecting-ip")
        if cf_connecting_ip:
            client_ip = cf_connecting_ip.strip()
        else:
            x_real_ip = request.headers.get("x-real-ip")
            if x_real_ip:
                client_ip = x_real_ip.strip()
                
    # Validate the IP format to prevent SSRF path traversal injections
    if client_ip != "localhost":
        import ipaddress
        try:
            ipaddress.ip_address(client_ip)
        except ValueError:
            client_ip = "127.0.0.1"
                
    # Detect if loopback/private
    is_private = False
    if client_ip in ["127.0.0.1", "localhost", "::1"]:
        is_private = True
    elif client_ip.startswith("192.168.") or client_ip.startswith("10."):
        is_private = True
    elif client_ip.startswith("172.16.") or client_ip.startswith("172.17.") or client_ip.startswith("172.18.") or client_ip.startswith("172.19.") or client_ip.startswith("172.20.") or client_ip.startswith("172.21.") or client_ip.startswith("172.22.") or client_ip.startswith("172.23.") or client_ip.startswith("172.24.") or client_ip.startswith("172.25.") or client_ip.startswith("172.26.") or client_ip.startswith("172.27.") or client_ip.startswith("172.28.") or client_ip.startswith("172.29.") or client_ip.startswith("172.30.") or client_ip.startswith("172.31."):
        is_private = True
        
    # Perform server-side geolocation
    import urllib.request
    import json
    
    # Try ipwho.is first (free, fast, no auth key required)
    try:
        url = "https://ipwho.is/" if is_private else f"https://ipwho.is/{client_ip}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            if data.get("success"):
                return {
                    "country_name": data.get("country"),
                    "country": data.get("country_code"),
                    "ip": data.get("ip") if not is_private else "127.0.0.1"
                }
    except Exception as e:
        logger.error(f"Server-side ipwho.is geoip lookup failed: {e}")
        
    # Default fallback
    return {
        "country_name": "everywhere",
        "country": "US",
        "ip": "127.0.0.1"
    }


@app.post("/subscribe")
async def subscribe(request: Request, email: str = Form(...)):
    email_clean = email.lower().strip()
    if not EMAIL_REGEX.match(email_clean):
        return HTMLResponse(content="Invalid email format", status_code=400)
    database.create_subscriber(email_clean)
    
    # Send custom OTel log that propagates to PostHog
    logger.info(
        f"Mailing list subscription: {email_clean}",
        extra={
            "email": email_clean,
            "event_type": "newsletter_signup",
            "referrer": request.headers.get("referer", ""),
            "ip_address": request.client.host if request.client else "unknown"
        }
    )
    trigger_alert(
        "newsletter_signup",
        f"New newsletter subscription: `{email_clean}`",
        {
            "email": email_clean,
            "referrer": request.headers.get("referer", ""),
            "ip_address": request.client.host if request.client else "unknown"
        },
        distinct_id=email_clean
    )
    return Response(status_code=200)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    if get_current_user(request):
        return RedirectResponse(url="/dashboard")
    return render_template("login.html", request, {"error": error})

@app.post("/login")
async def do_login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = database.get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        trigger_alert(
            "login_failed",
            f"Failed login attempt for user `{email}`.",
            {"email": email, "reason": "invalid_credentials"},
            distinct_id=email or "anonymous"
        )
        return render_template("login.html", request, {"error": "Invalid email or password"})
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="session_user",
        value=sign_session_cookie(email.lower().strip()),
        max_age=86400 * 30,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    logger.info(f"User logged in: {email}", extra={"email": email, "event_type": "login"})
    trigger_alert(
        "user_login", 
        f"User `{email}` logged in successfully.",
        {"email": email},
        distinct_id=email
    )
    return response

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, error: str = None, plan: str = "lifetime"):
    if get_current_user(request):
        return RedirectResponse(url="/dashboard")
    return render_template("signup.html", request, {"error": error, "plan": plan})

@app.post("/signup")
async def do_signup(request: Request, email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), plan: str = "lifetime"):
    email_clean = email.lower().strip()
    if not EMAIL_REGEX.match(email_clean):
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: invalid email format",
            {"email": email, "reason": "invalid_email_format"},
            distinct_id="anonymous"
        )
        return render_template("signup.html", request, {"error": "Invalid email address format", "plan": plan})

    if password != confirm_password:
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: passwords do not match",
            {"email": email, "reason": "password_mismatch"},
            distinct_id="anonymous"
        )
        return render_template("signup.html", request, {"error": "Passwords do not match", "plan": plan})
    
    if len(password) < 8:
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: weak password",
            {"email": email, "reason": "weak_password"},
            distinct_id="anonymous"
        )
        return render_template("signup.html", request, {"error": "Password must be at least 8 characters long", "plan": plan})
    
    user = database.get_user_by_email(email)
    if user:
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: email already registered",
            {"email": email, "reason": "email_registered"},
            distinct_id=email
        )
        return render_template("signup.html", request, {"error": "Email is already registered", "plan": plan})
    
    try:
        database.create_user(email, hash_password(password))
        logger.info(f"User registered: {email}", extra={"email": email, "plan": plan, "event_type": "signup"})
        trigger_alert(
            "user_signup",
            f"New user registered: `{email}` with plan `{plan}`.",
            {"email": email, "plan": plan},
            distinct_id=email
        )
    except Exception as e:
        trigger_alert(
            "user_signup_failed",
            f"Account registration failed for `{email}`: {str(e)}",
            {"email": email, "plan": plan, "error": str(e)},
            distinct_id=email or "anonymous"
        )
        return render_template("signup.html", request, {"error": "Account registration failed.", "plan": plan})

    # Check if this email paid before registering — auto-upgrade instantly
    pending = database.consume_pending_premium(email)
    if pending:
        database.update_user_tier(email, "premium", pending.get("stripe_customer_id"))
        logger.info(f"Pending premium applied on registration: {email}", extra={"email": email, "event_type": "pending_premium_applied"})
        trigger_alert(
            "pending_premium_applied",
            f"Pending premium applied for `{email}` upon registration.",
            {"email": email, "customer_id": pending.get("stripe_customer_id")},
            distinct_id=email
        )
        response = RedirectResponse(url="/dashboard?payment=success", status_code=303)
    else:
        response = RedirectResponse(url=f"/checkout?plan={plan}", status_code=303)

    response.set_cookie(
        key="session_user",
        value=sign_session_cookie(email.lower().strip()),
        max_age=86400 * 30,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return response

@app.get("/logout")
async def do_logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_user", path="/")
    return response

# --- Protected Console App ---
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    banks = database.get_all_banks(user["id"])
    return render_template("index.html", request, {"banks": banks, "user": user})

@app.get("/banks", response_class=HTMLResponse)
async def get_banks(request: Request):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
        
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.get("/banks/{bank_id}", response_class=HTMLResponse)
async def get_bank_details(request: Request, bank_id: int):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
        
    bank = database.get_bank(bank_id, user["id"])
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return render_template("patch_list.html", request, {"bank": bank, "user": user})

@app.post("/banks", response_class=HTMLResponse)
async def create_bank(
    request: Request,
    name: str = Form(...),
    synth_model: str = Form(...),
    sysex_hex: str = Form(...)
):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")

    banks = database.get_all_banks(user["id"])
    if user["tier"] != "premium" and len(banks) >= 1:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")

    if len(sysex_hex) > 4194304: # 2MB limit (each byte is 2 hex chars)
        trigger_alert("security_limit_exceeded", f"User `{user['email']}` attempted to upload a massive hex payload ({len(sysex_hex)} chars).", {"email": user["email"]}, distinct_id=user["email"])
        raise HTTPException(status_code=413, detail="Payload too large: SysEx hex data exceeds 2MB limit")

    try:
        clean_hex = sysex_hex.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        sysex_bytes = bytes.fromhex(clean_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hexadecimal string data")
    
    # Parse voices
    try:
        if synth_model == "Yamaha DX7":
            patch_names = parser.parse_dx7_sysex(sysex_bytes)
        elif synth_model == "Roland Juno-106":
            patch_names = parser.parse_juno106_sysex(sysex_bytes)
        elif synth_model == "Korg M1":
            patch_names = parser.parse_korg_m1_sysex(sysex_bytes)
        elif synth_model == "Roland Jupiter-6":
            patch_names = parser.parse_jupiter6_sysex(sysex_bytes)
        elif synth_model == "Casio CZ-101":
            patch_names = parser.parse_cz101_sysex(sysex_bytes)
        else:
            patch_names = parser.parse_generic_sysex(sysex_bytes)

        if not patch_names:
            trigger_alert(
                "sysex_parser_empty",
                f"SysEx parser returned 0 patches for `{name}` ({synth_model}) of user `{user['email']}`.",
                {
                    "email": user["email"],
                    "synth_model": synth_model,
                    "sysex_len_bytes": len(sysex_bytes),
                    "sysex_hex_preview": sysex_bytes[:50].hex()
                },
                distinct_id=user["email"]
            )
        else:
            trigger_alert(
                "sysex_parser_success",
                f"SysEx parser successfully extracted {len(patch_names)} patches for `{name}` ({synth_model}) of user `{user['email']}`.",
                {
                    "email": user["email"],
                    "synth_model": synth_model,
                    "sysex_len_bytes": len(sysex_bytes),
                    "patches_count": len(patch_names),
                    "patch_names_preview": patch_names[:5]
                },
                    distinct_id=user["email"]
                )
        if user["tier"] != "premium":
            if patch_names:
                patch_names = [f"LOCKED {i+1} (PRO)" for i in range(len(patch_names))]
            else:
                patch_names = ["LOCKED (PRO)"]

    except Exception as exc:
        trigger_alert(
            "sysex_parser_failed",
            f"SysEx parser failed with exception: `{exc.__class__.__name__}: {str(exc)}` for `{name}` ({synth_model}) of user `{user['email']}`.",
            {
                "email": user["email"],
                "synth_model": synth_model,
                "sysex_len_bytes": len(sysex_bytes),
                "error": str(exc),
                "traceback": traceback.format_exc()
            },
            distinct_id=user["email"]
        )
        patch_names = []
        
    # Save to database scoped to user
    database.save_bank(name, synth_model, clean_hex, patch_names, user["id"])
    logger.info(f"SysEx bank created: {name} ({synth_model}) for user {user['email']}", extra={"email": user["email"], "synth_model": synth_model, "patches_count": len(patch_names), "event_type": "sysex_upload"})
    trigger_alert(
        "sysex_bank_created",
        f"SysEx bank `{name}` created for user `{user['email']}`.",
        {"email": user["email"], "synth_model": synth_model, "patches_count": len(patch_names)},
        distinct_id=user["email"]
    )
    
    # Return updated bank list
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.post("/banks/upload", response_class=HTMLResponse)
async def upload_bank_file(
    request: Request,
    name: str = Form(...),
    synth_model: str = Form(...),
    file: UploadFile = File(...)
):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")

    banks = database.get_all_banks(user["id"])
    if user["tier"] != "premium" and len(banks) >= 1:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")

    # Enforce 2MB size limit
    MAX_SIZE = 2 * 1024 * 1024 # 2MB
    if file.size and file.size > MAX_SIZE:
        trigger_alert("security_limit_exceeded", f"User `{user['email']}` attempted to upload a massive file: {file.filename} ({file.size} bytes).", {"email": user["email"]}, distinct_id=user["email"])
        raise HTTPException(status_code=413, detail="File too large: SysEx files must be under 2MB")

    sysex_bytes = await file.read()
    if len(sysex_bytes) > MAX_SIZE:
        trigger_alert("security_limit_exceeded", f"User `{user['email']}` attempted to upload a massive file: {file.filename} ({len(sysex_bytes)} bytes).", {"email": user["email"]}, distinct_id=user["email"])
        raise HTTPException(status_code=413, detail="File too large: SysEx files must be under 2MB")

    sysex_hex = sysex_bytes.hex()
    
    # Parse voices
    try:
        if synth_model == "Yamaha DX7":
            patch_names = parser.parse_dx7_sysex(sysex_bytes)
        elif synth_model == "Roland Juno-106":
            patch_names = parser.parse_juno106_sysex(sysex_bytes)
        elif synth_model == "Korg M1":
            patch_names = parser.parse_korg_m1_sysex(sysex_bytes)
        elif synth_model == "Roland Jupiter-6":
            patch_names = parser.parse_jupiter6_sysex(sysex_bytes)
        elif synth_model == "Casio CZ-101":
            patch_names = parser.parse_cz101_sysex(sysex_bytes)
        else:
            patch_names = parser.parse_generic_sysex(sysex_bytes)

        if not patch_names:
            trigger_alert(
                "sysex_parser_empty",
                f"SysEx parser returned 0 patches for uploaded file `{name}` ({synth_model}) of user `{user['email']}`.",
                {
                    "email": user["email"],
                    "synth_model": synth_model,
                    "sysex_len_bytes": len(sysex_bytes),
                    "sysex_hex_preview": sysex_bytes[:50].hex()
                },
                distinct_id=user["email"]
            )
        else:
            trigger_alert(
                "sysex_parser_success",
                f"SysEx parser successfully extracted {len(patch_names)} patches for uploaded file `{name}` ({synth_model}) of user `{user['email']}`.",
                {
                    "email": user["email"],
                    "synth_model": synth_model,
                    "sysex_len_bytes": len(sysex_bytes),
                    "patches_count": len(patch_names),
                    "patch_names_preview": patch_names[:5]
                },
                    distinct_id=user["email"]
                )
        if user["tier"] != "premium":
            if patch_names:
                patch_names = [f"LOCKED {i+1} (PRO)" for i in range(len(patch_names))]
            else:
                patch_names = ["LOCKED (PRO)"]

    except Exception as exc:
        trigger_alert(
            "sysex_parser_failed",
            f"SysEx parser failed with exception: `{exc.__class__.__name__}: {str(exc)}` for uploaded file `{name}` ({synth_model}) of user `{user['email']}`.",
            {
                "email": user["email"],
                "synth_model": synth_model,
                "sysex_len_bytes": len(sysex_bytes),
                "error": str(exc),
                "traceback": traceback.format_exc()
            },
            distinct_id=user["email"]
        )
        patch_names = []
        
    database.save_bank(name, synth_model, sysex_hex, patch_names, user["id"])
    logger.info(f"SysEx file uploaded: {name} ({synth_model}) for user {user['email']}", extra={"email": user["email"], "synth_model": synth_model, "patches_count": len(patch_names), "event_type": "sysex_upload"})
    trigger_alert(
        "sysex_file_uploaded",
        f"SysEx file `{name}` uploaded for user `{user['email']}`.",
        {"email": user["email"], "synth_model": synth_model, "patches_count": len(patch_names)},
        distinct_id=user["email"]
    )
    
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.delete("/banks/{bank_id}", response_class=HTMLResponse)
async def delete_bank(request: Request, bank_id: int):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
        
    bank = database.get_bank(bank_id, user["id"])
    bank_name = bank["name"] if bank else "Unknown"
    database.delete_bank(bank_id, user["id"])
    trigger_alert(
        "sysex_bank_deleted",
        f"SysEx bank `{bank_name}` (ID: {bank_id}) deleted by user `{user['email']}`.",
        {"email": user["email"], "bank_id": bank_id, "bank_name": bank_name},
        distinct_id=user["email"]
    )
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.get("/banks/{bank_id}/download")
async def download_bank(request: Request, bank_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    if user["tier"] != "premium":
        return RedirectResponse(url="/checkout")
        
    bank = database.get_bank(bank_id, user["id"])
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
        
    try:
        sysex_bytes = bytes.fromhex(bank["sysex_hex"])
    except ValueError:
        raise HTTPException(status_code=500, detail="Database data corruption: invalid hex")
        
    trigger_alert(
        "sysex_bank_downloaded",
        f"SysEx bank `{bank['name']}` (ID: {bank_id}) downloaded by user `{user['email']}`.",
        {"email": user["email"], "bank_id": bank_id, "bank_name": bank["name"], "synth_model": bank["synth_model"]},
        distinct_id=user["email"]
    )

    file_stream = io.BytesIO(sysex_bytes)
    safe_name = bank["name"].lower().replace(" ", "_")
    filename = f"{safe_name}.syx"
    
    return StreamingResponse(
        file_stream, 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/banks/{bank_id}/hex")
async def get_bank_hex(request: Request, bank_id: int):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    bank = database.get_bank(bank_id, user["id"])
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    
    trigger_alert(
        "sysex_bank_hex_requested",
        f"SysEx bank `{bank['name']}` (ID: {bank_id}) hex requested for transmission by user `{user['email']}`.",
        {"email": user["email"], "bank_id": bank_id, "bank_name": bank["name"], "synth_model": bank["synth_model"]},
        distinct_id=user["email"]
    )
    return {"sysex_hex": bank["sysex_hex"]}

# --- Sound Shop & Generative AI Endpoints ---
@app.get("/marketplace", response_class=HTMLResponse)
async def get_marketplace(request: Request):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
    if user["tier"] != "premium":
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")
        
    packs = [
        {
            "id": "m1_matrix",
            "name": "Korg M1: Off the Matrix",
            "synth": "Korg M1",
            "price": "$9.00",
            "description": "Premium overrides of sample keymaps carefully programmed over 20 years. Features Trident Strings and analog emulations.",
            "patches_count": 32,
            "demo_patches": ["Cyber Gate", "HousePiano", "Ethereal", "TridentStr", "Glassy Pad", "Obese Poly"],
        },
        {
            "id": "dx7_retro",
            "name": "Yamaha DX7: Classic FM Leads & Basses",
            "synth": "Yamaha DX7",
            "price": "$9.00",
            "description": "Punchy FM basses, crystal-clear bell leads, and classic 80s electric pianos. Optimized for live MIDI performance.",
            "patches_count": 32,
            "demo_patches": ["Super Bass", "Chime Bell", "FM Rhodes", "Synth Brass", "Sitar Glide", "Atmosphere"],
        },
        {
            "id": "juno_nostalgia",
            "name": "Roland Juno-106: Nostalgia Plucks & Pads",
            "synth": "Roland Juno-106",
            "price": "$9.00",
            "description": "Warm, chorus-drenched analog pads, snap plucks, and classic 80s sci-fi SFX. Relive the golden age of ambient.",
            "patches_count": 32,
            "demo_patches": ["Nostalgia", "Chorused Pad", "Snap Pluck", "Space Wind", "Analog Sweep", "Sub Bass"],
        }
    ]
    return render_template("marketplace.html", request, {"packs": packs, "user": user})

@app.post("/api/generate-ai-bank", response_class=HTMLResponse)
async def generate_ai_bank(request: Request, synth_model: str = Form(...), chaos_level: int = Form(...)):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    if user["tier"] != "premium":
        raise HTTPException(status_code=402, detail="Premium Tier Required")
        
    import random
    
    # Funny synth preset word lists
    prefixes = ["PLUCK", "MEGA", "FAT", "SWEET", "SINE", "OBXA", "JX", "FM", "POLY", "MINI", "MOOG", "SPACE", "COSMIC", "DEEP", "EP", "DX", "TRID", "PPG", "GLAS", "B3", "ROT", "CARO", "LIVE", "UP", "DECE"]
    suffixes = ["PAD", "BASS", "PIANO", "BELL", "LEAD", "WAVE", "STR", "CHM", "BRASS", "KARB", "SAX", "GATE", "WIND", "RHODES", "SIREN", "COWBEL", "PROBE", "CLAV", "HARM", "OBOE", "FLUT", "SITAR"]
    
    generated_patches = []
    for i in range(32):
        name = f"{random.choice(prefixes)} {random.choice(suffixes)}"
        name = name.upper()[:10].ljust(10)
        generated_patches.append(name.strip())
        
    # Generate random raw DX7 SysEx bytes (approx 4104 bytes) or model-specific hex
    data = bytearray(4104)
    data[0] = 0xF0
    data[1] = 0x43
    data[2] = 0x00
    data[3] = 0x09
    data[4] = 0x20
    data[5] = 0x00
    
    for i in range(32):
        voice_offset = 6 + (i * 128)
        # Fill parameters with pseudo-random numbers
        for j in range(118):
            data[voice_offset + j] = random.randint(0, 127)
        # Format name
        name_bytes = generated_patches[i].ljust(10)[:10].encode('ascii', errors='ignore')
        for j in range(len(name_bytes)):
            data[voice_offset + 118 + j] = name_bytes[j]
            
    # Checksum
    checksum = 0
    for i in range(6, 4102):
        checksum += data[i]
    data[4102] = (-checksum) & 0x7F
    data[4103] = 0xF7
    
    sysex_hex = data.hex()
    
    bank_id = database.save_bank("AI Generated Cartridge", "Yamaha DX7", sysex_hex, generated_patches, user["id"])
    trigger_alert(
        "ai_bank_generated",
        f"AI Generated Cartridge created for `{user['email']}`.",
        {"email": user["email"], "synth_model": "Yamaha DX7", "patches_count": len(generated_patches)},
        distinct_id=user["email"]
    )
    
    return render_template("ai_generated_result.html", request, {
        "bank_id": bank_id,
        "name": "AI Generated Cartridge",
        "synth_model": "Yamaha DX7",
        "patches": generated_patches,
        "sysex_hex": sysex_hex,
        "user": user
    })

@app.get("/checkout-pack/{pack_id}")
async def checkout_pack(request: Request, pack_id: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    if user["tier"] != "premium":
        return RedirectResponse(url="/checkout")
        
    packs_data = {
        "m1_matrix": {
            "name": "Korg M1: Off the Matrix",
            "synth": "Korg M1",
            "hex": "f042301910" + "00" * 4000 + "f7",
            "patches": ["Cyber Gate", "HousePiano", "Ethereal", "TridentStr", "Glassy Pad", "Obese Poly", "Karimba!", "Narnia"]
        },
        "dx7_retro": {
            "name": "Yamaha DX7: Classic FM Leads & Basses",
            "synth": "Yamaha DX7",
            "hex": "f04300092000" + "3f" * 4096 + "f7",
            "patches": ["Super Bass", "Chime Bell", "FM Rhodes", "Synth Brass", "Sitar Glide", "Atmosphere", "Digi Bass", "Church Org"]
        },
        "juno_nostalgia": {
            "name": "Roland Juno-106: Nostalgia Plucks & Pads",
            "synth": "Roland Juno-106",
            "hex": "f0413600" + "1a" * 2000 + "f7",
            "patches": ["Nostalgia", "Chorused Pad", "Snap Pluck", "Space Wind", "Analog Sweep", "Sub Bass", "Euro Bass", "PPG Wave"]
        }
    }
    
    if pack_id not in packs_data:
        raise HTTPException(status_code=404, detail="Pack not found")
        
    pack = packs_data[pack_id]
    database.save_bank(f"{pack['name']} (Purchased)", pack["synth"], pack["hex"], pack["patches"], user["id"])
    trigger_alert(
        "marketplace_pack_purchased",
        f"Marketplace pack `{pack['name']}` purchased/added for user `{user['email']}`.",
        {"email": user["email"], "pack_id": pack_id, "pack_name": pack["name"], "synth_model": pack["synth"]},
        distinct_id=user["email"]
    )
    return RedirectResponse(url="/dashboard?payment=pack_success", status_code=303)

# --- Stripe Monetization Endpoints ---
@app.get("/checkout")
async def create_checkout_session(request: Request, plan: str = "lifetime"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    # If Stripe keys are missing, run in sandbox developer mock-mode
    if not STRIPE_SECRET_KEY:
        return RedirectResponse(url=f"/mock-checkout-success?email={user['email']}")
        
    if plan == "lifetime":
        price_id = STRIPE_PRICE_ID_LIFETIME
    elif plan == "yearly":
        price_id = STRIPE_PRICE_ID_YEARLY
    else:
        price_id = STRIPE_PRICE_ID_MONTHLY
    
    # Check if we are in an active promotion week to allow coupon codes
    query_birthday = False
    query_christmas = False
    try:
        query_birthday = request.query_params.get("birthday") == "true"
        query_christmas = request.query_params.get("christmas") == "true"
    except Exception:
        pass
    force_birthday = query_birthday or os.environ.get("FORCE_BIRTHDAY") == "true"
    force_christmas = query_christmas or os.environ.get("FORCE_CHRISTMAS") == "true"
    
    now = datetime.now()
    is_birthday = (now.month == 5 and now.day == 31) or (now.month == 6 and 1 <= now.day <= 6) or force_birthday
    is_christmas = (now.month == 12 and 18 <= now.day <= 31) or (now.month == 1 and now.day == 1) or force_christmas
    allow_promo = is_birthday or is_christmas
    
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='payment' if plan == "lifetime" else 'subscription',
            allow_promotion_codes=allow_promo,
            success_url=BASE_URL + "/dashboard?payment=success",
            cancel_url=BASE_URL + "/dashboard?payment=cancel",
            customer_email=user["email"],
            metadata={"user_email": user["email"]}
        )
        trigger_alert(
            "stripe_checkout_initiated",
            f"Stripe checkout initiated by `{user['email']}` for plan `{plan}`.",
            {"email": user["email"], "plan": plan, "checkout_session_id": checkout_session.id},
            distinct_id=user["email"]
        )
        return RedirectResponse(url=checkout_session.url, status_code=303)
    except Exception as e:
        trigger_alert(
            "stripe_checkout_failed",
            f"Stripe checkout session creation failed for `{user['email']}`: {str(e)}",
            {"email": user["email"], "plan": plan, "error": str(e)},
            distinct_id=user["email"]
        )
        raise HTTPException(status_code=500, detail=f"Stripe integration session error: {str(e)}")

@app.get("/portal")
async def create_portal_session(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    if not STRIPE_SECRET_KEY:
        # Toggle subscription locally in mock mode for billing portal test ease
        new_tier = "free" if user["tier"] == "premium" else "premium"
        database.update_user_tier(user["email"], new_tier)
        return RedirectResponse(url="/dashboard?mock_portal=1")
        
    if not user["stripe_customer_id"]:
        return RedirectResponse(url="/checkout")
        
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url=BASE_URL + "/dashboard"
        )
        trigger_alert(
            "stripe_portal_opened",
            f"Stripe customer billing portal opened by `{user['email']}`.",
            {"email": user["email"], "customer_id": user["stripe_customer_id"]},
            distinct_id=user["email"]
        )
        return RedirectResponse(url=portal_session.url, status_code=303)
    except Exception as e:
        trigger_alert(
            "stripe_portal_failed",
            f"Stripe billing portal opening failed for `{user['email']}`: {str(e)}",
            {"email": user["email"], "error": str(e)},
            distinct_id=user["email"]
        )
        raise HTTPException(status_code=500, detail=f"Billing portal connection error: {str(e)}")

@app.get("/mock-checkout-success")
async def mock_checkout_success(email: str):
    # Protect against production payment bypass
    if os.environ.get("VERCEL") or (STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith("sk_test_")):
        raise HTTPException(status_code=403, detail="Mock checkout is disabled in production")
    database.update_user_tier(email, "premium", "mock_customer_id")
    return RedirectResponse(url="/dashboard?payment=success")

@app.get("/admin/grant-premium")
async def admin_grant_premium(email: str, secret: str):
    """Emergency admin endpoint to manually upgrade a user to premium.
    Requires ADMIN_SECRET env var to match the secret query param."""
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret or secret != admin_secret:
        trigger_alert(
            "unauthorized_admin_access",
            f"Unauthorized attempt to grant premium to `{email}` using secret `{secret}`.",
            {"email": email, "provided_secret": secret},
            distinct_id="admin_attacker"
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    user = database.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail=f"No account found for {email}. Ask them to register first.")
    database.update_user_tier(email, "premium")
    logger.info(f"Admin manually granted premium: {email}", extra={"email": email, "event_type": "admin_grant_premium"})
    trigger_alert(
        "admin_grant_premium",
        f"Admin manually granted premium status to `{email}`.",
        {"email": email},
        distinct_id=email
    )
    return {"status": "ok", "message": f"{email} upgraded to premium successfully."}

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not STRIPE_WEBHOOK_SECRET:
        return {"status": "ignored"}
        
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Use getattr() — Stripe SDK returns typed objects, not plain dicts
        customer_email = getattr(session, 'customer_email', None)
        if not customer_email:
            metadata = getattr(session, 'metadata', None) or {}
            customer_email = metadata.get('user_email') if isinstance(metadata, dict) else getattr(metadata, 'user_email', None)
        customer_id = getattr(session, 'customer', None)
        if customer_email:
            existing_user = database.get_user_by_email(customer_email)
            if existing_user:
                database.update_user_tier(customer_email, "premium", customer_id)
                logger.info(f"Subscription activated via Stripe: {customer_email}", extra={"email": customer_email, "customer_id": customer_id, "event_type": "subscription_activated"})
                trigger_alert(
                    "subscription_activated",
                    f"Subscription activated via Stripe for `{customer_email}`.",
                    {"email": customer_email, "customer_id": customer_id},
                    distinct_id=customer_email
                )
            else:
                # User paid before registering — park it, apply on registration
                database.upsert_pending_premium(customer_email, customer_id)
                logger.info(f"Pending premium parked (no account yet): {customer_email}", extra={"email": customer_email, "customer_id": customer_id, "event_type": "subscription_pending"})
                trigger_alert(
                    "subscription_pending",
                    f"Subscription paid but pending registration for `{customer_email}`.",
                    {"email": customer_email, "customer_id": customer_id},
                    distinct_id=customer_email
                )
            
    elif event['type'] == 'customer.subscription.deleted':
        session = event['data']['object']
        customer_id = getattr(session, 'customer', None)
        if customer_id:
            database.update_user_tier_by_customer_id(customer_id, "free")
            logger.info(f"Subscription cancelled via Stripe: {customer_id}", extra={"customer_id": customer_id, "event_type": "subscription_deleted"})
            trigger_alert(
                "subscription_deleted",
                f"Subscription cancelled via Stripe for customer ID `{customer_id}`.",
                {"customer_id": customer_id},
                distinct_id=customer_id
            )
        
    return {"status": "success"}

@app.get("/sitemap.xml")
@app.get("/sitemap.xml/")
async def sitemap():
    sitemap_path = os.path.join(BASE_DIR, "static", "sitemap.xml")
    if os.path.exists(sitemap_path):
        try:
            with open(sitemap_path, "r", encoding="utf-8") as f:
                content = f.read()
            return Response(content=content, media_type="application/xml")
        except Exception as e:
            logger.error(f"Failed to read static sitemap.xml: {e}")

    urls = [
        ("https://knob.monster/", "2026-06-21", "weekly", "1.0"),
        ("https://knob.monster/sysex-librarian-alternatives", "2026-06-21", "weekly", "0.9"),
        ("https://knob.monster/knob-monster-vs-snoize-sysex-librarian", "2026-06-21", "weekly", "0.9"),
        ("https://knob.monster/knob-monster-vs-midi-ox", "2026-06-21", "weekly", "0.9"),
        ("https://knob.monster/login", "2026-06-21", "monthly", "0.8"),
        ("https://knob.monster/signup", "2026-06-21", "monthly", "0.8"),
        ("https://knob.monster/resources", "2026-06-21", "weekly", "0.85"),
        ("https://knob.monster/terms", "2026-06-21", "monthly", "0.5"),
        ("https://knob.monster/privacy", "2026-06-21", "monthly", "0.5"),
        ("https://knob.monster/payment-methods", "2026-06-21", "monthly", "0.6"),
        ("https://knob.monster/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer", "2026-06-23", "weekly", "0.9"),
        ("https://knob.monster/how-to-backup-yamaha-dx7-presets-sysex-transfer-guide", "2026-06-25", "weekly", "0.9"),
        ("https://knob.monster/how-to-backup-roland-juno-106-presets-sysex-transfer-guide", "2026-06-25", "weekly", "0.9"),
        ("https://knob.monster/how-to-backup-korg-m1-presets-sysex-transfer-guide", "2026-06-25", "weekly", "0.9"),
    ]
    
    # Dynamically add all synths from SEO_DATA
    for slug in SEO_DATA.keys():
        urls.append((f"https://knob.monster/{slug}", "2026-06-21", "weekly", "0.9"))
        
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    for loc, lastmod, changefreq, priority in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{loc}</loc>")
        xml_lines.append(f"    <lastmod>{lastmod}</lastmod>")
        xml_lines.append(f"    <changefreq>{changefreq}</changefreq>")
        xml_lines.append(f"    <priority>{priority}</priority>")
        xml_lines.append("  </url>")
        
    xml_lines.append("</urlset>")
    
    return Response(content="\n".join(xml_lines), media_type="application/xml")

@app.get("/robots.txt")
@app.get("/robots.txt/")
async def robots():
    robots_path = os.path.join(BASE_DIR, "static", "robots.txt")
    if os.path.exists(robots_path):
        try:
            with open(robots_path, "r", encoding="utf-8") as f:
                content = f.read()
            return Response(content=content, media_type="text/plain")
        except Exception as e:
            logger.error(f"Failed to read static robots.txt: {e}")

    content = """User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /banks/

Sitemap: https://knob.monster/sitemap.xml"""
    return Response(content=content, media_type="text/plain")

@app.get("/llms.txt")
@app.get("/llms.txt/")
async def llms_txt():
    llms_path = os.path.join(BASE_DIR, "static", "llms.txt")
    if os.path.exists(llms_path):
        try:
            with open(llms_path, "r", encoding="utf-8") as f:
                content = f.read()
            return Response(content=content, media_type="text/plain")
        except Exception as e:
            logger.error(f"Failed to read static llms.txt: {e}")

    lines = [
        "# knob.monster",
        "",
        "> The iCloud for your vintage synthesizers. Back up, organize, and search patches from your 1980s and 90s hardware directly in your web browser. No desktop software or drivers required.",
        "",
        "## Key Features",
        "- **Browser-Native Web MIDI:** Direct connection to physical synth memory banks over SysEx.",
        "- **Instant Search:** Fuzzy search through soundbanks by preset name.",
        "- **Universal Support:** Built for Yamaha DX7, Roland Juno-106, Korg M1, Jupiter-6 (Europa), Casio CZ-101, and generic synthesizers.",
        "- **Direct Pricing:** $39 one-time payment for lifetime access. Own it forever. No subscriptions.",
        "",
        "## Key Pages",
        "- [Home Page](https://knob.monster/): Explains features, pricing, and includes live MIDI scanning simulator.",
        "- [Alternatives Guide](https://knob.monster/sysex-librarian-alternatives): Comprehensive comparison of web-based SysEx librarians.",
        "- [Snoize Comparison](https://knob.monster/knob-monster-vs-snoize-sysex-librarian): Detailed comparison with Snoize SysEx Librarian.",
        "- [MIDI-OX Comparison](https://knob.monster/knob-monster-vs-midi-ox): Technical comparison with Windows MIDI-OX.",
        "- [Payment Methods](https://knob.monster/payment-methods): Supported payment mechanisms and local options.",
        ""
    ]
    
    lines.append("## Synthesizer Librarians")
    for slug, data in SEO_DATA.items():
        synth_name = data.get("synth_name", slug)
        lines.append(f"- [{synth_name} Librarian](https://knob.monster/{slug}): {data.get('description', '')}")
        
    return Response(content="\n".join(lines), media_type="text/plain")

INDEXNOW_KEY = "7f8b9e6c5d4c3b2a1a0f9e8d7c6b5a4f"

@app.get(f"/{INDEXNOW_KEY}.txt")
async def indexnow_key():
    return Response(content=INDEXNOW_KEY, media_type="text/plain")


# ============================================================
# AGENT / AI DISCOVERY INFRASTRUCTURE
# ============================================================

SITE_BASE = "https://knob.monster"

# --- Middleware: RFC 8288 Link Headers + Markdown Content Negotiation ---
@app.middleware("http")
async def agent_discovery_middleware(request: Request, call_next):
    """
    1. Injects RFC 8288 Link response headers on every HTML page.
    2. Handles Accept: text/markdown content negotiation for the homepage.
    """
    accept = request.headers.get("accept", "")
    path = request.url.path

    # Markdown content negotiation (homepage only, text/markdown or text/x-markdown)
    if path == "/" and ("text/markdown" in accept or "text/x-markdown" in accept):
        markdown_body = """# knob.monster — The iCloud for Vintage Synthesizers

> Back up, organize, and search SysEx patch banks from your 1980s and 90s hardware directly in your web browser. No desktop software or USB drivers required.

## What It Does
- **Browser-Native Web MIDI**: Direct connection to physical synth memory banks over SysEx
- **Instant Search**: Fuzzy search through soundbanks by preset name
- **1-Click Recall**: Flash entire patch banks back to hardware RAM in one click
- **Universal Support**: Yamaha DX7, Roland Juno-106, Korg M1, Jupiter-6 (Europa), Casio CZ-101, and generic synthesizers

## Pricing
- **Lifetime Access**: $39 one-time payment. Own it forever. No subscriptions.

## API
- **API Catalog**: </well-known/api-catalog>
- **OpenAPI Spec**: /openapi.json
- **Status**: /status

## Authentication
See /auth.md for agent registration instructions.

## Links
- [Sign Up](https://knob.monster/signup)
- [Log In](https://knob.monster/login)
- [Payment Methods](https://knob.monster/payment-methods)
- [Resources](https://knob.monster/resources)
- [Terms](https://knob.monster/terms)
- [Privacy](https://knob.monster/privacy)
"""
        token_count = len(markdown_body.split())
        return Response(
            content=markdown_body,
            media_type="text/markdown",
            headers={
                "Content-Type": "text/markdown; charset=utf-8",
                "x-markdown-tokens": str(token_count),
                "Vary": "Accept",
            }
        )

    response = await call_next(request)

    # Inject Link headers on HTML responses
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        link_parts = [
            f'<{SITE_BASE}/.well-known/api-catalog>; rel="api-catalog"',
            f'<{SITE_BASE}/openapi.json>; rel="service-desc"',
            f'<{SITE_BASE}/llms.txt>; rel="service-doc"',
            f'<{SITE_BASE}/.well-known/oauth-authorization-server>; rel="describedby"',
        ]
        response.headers["Link"] = ", ".join(link_parts)

    return response


# --- RFC 9727: API Catalog ---
@app.get("/.well-known/api-catalog")
async def api_catalog():
    """RFC 9727 — API catalog in application/linkset+json format."""
    catalog = {
        "linkset": [
            {
                "anchor": f"{SITE_BASE}/api",
                "service-desc": [{"href": f"{SITE_BASE}/openapi.json", "type": "application/openapi+json"}],
                "service-doc": [{"href": f"{SITE_BASE}/llms.txt", "type": "text/plain"}],
                "status": [{"href": f"{SITE_BASE}/status"}]
            }
        ]
    }
    return Response(
        content=__import__("json").dumps(catalog, indent=2),
        media_type="application/linkset+json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# --- RFC 8414: OAuth 2.0 Authorization Server Metadata ---
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    """OAuth 2.0 AS metadata per RFC 8414. knob.monster uses Stripe for payments and
    email/password auth — this document describes what agents need to know."""
    metadata = {
        "issuer": SITE_BASE,
        "authorization_endpoint": f"{SITE_BASE}/login",
        "token_endpoint": f"{SITE_BASE}/api/token",
        "registration_endpoint": f"{SITE_BASE}/signup",
        "scopes_supported": ["read:banks", "write:banks", "read:patches"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "service_documentation": f"{SITE_BASE}/llms.txt",
        "ui_locales_supported": ["en"],
        "op_policy_uri": f"{SITE_BASE}/privacy",
        "op_tos_uri": f"{SITE_BASE}/terms",
        # auth.md agent_auth extension block
        "agent_auth": {
            "skill": "https://workos.com/auth.md",
            "register_uri": f"{SITE_BASE}/signup",
            "identity_types_supported": ["anonymous"],
            "anonymous": {
                "credential_types_supported": ["bearer"],
                "claim_uri": f"{SITE_BASE}/api/token"
            }
        }
    }
    return Response(
        content=__import__("json").dumps(metadata, indent=2),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# --- RFC 9728: OAuth Protected Resource Metadata ---
@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """OAuth Protected Resource Metadata per RFC 9728."""
    metadata = {
        "resource": SITE_BASE,
        "authorization_servers": [SITE_BASE],
        "scopes_supported": ["read:banks", "write:banks", "read:patches"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{SITE_BASE}/llms.txt",
        "resource_policy_uri": f"{SITE_BASE}/privacy"
    }
    return Response(
        content=__import__("json").dumps(metadata, indent=2),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# --- auth.md: Agent Registration Discovery ---
@app.get("/auth.md")
async def auth_md():
    """auth.md — agent registration instructions per workos/auth.md spec."""
    content = """# auth.md

This document describes how AI agents can register and authenticate with **knob.monster**.

## Service Overview

knob.monster is a browser-native cloud SysEx librarian for vintage synthesizers. Agents can use the API to manage patch banks and SysEx dumps.

## Authentication

knob.monster uses email/password authentication with session cookies. For agent access, use the REST API endpoints below.

### Registration

To create an account as an agent:

```
POST https://knob.monster/signup
Content-Type: application/x-www-form-urlencoded

email=agent@example.com&password=YourPassword123!&confirm_password=YourPassword123!&plan=lifetime
```

### Login / Token Acquisition

```
POST https://knob.monster/login
Content-Type: application/x-www-form-urlencoded

email=agent@example.com&password=YourPassword123!
```

The server sets a `session_user` cookie on successful login. Include this cookie in subsequent API requests.

## API Endpoints

| Endpoint | Method | Description | Auth Required |
|---|---|---|---|
| /status | GET | Health check | No |
| /api/geoip | GET | GeoIP lookup | No |
| /banks | GET | List patch banks | Yes (premium) |
| /banks | POST | Upload SysEx bank | Yes (premium) |
| /banks/{id} | GET | Get bank patches | Yes (premium) |
| /banks/{id}/download | GET | Download .syx file | Yes (premium) |
| /banks/{id}/hex | GET | Get hex dump | Yes (premium) |
| /banks/{id} | DELETE | Delete bank | Yes (premium) |

## Payments

Premium access is a single $39 one-time payment. Agents can purchase via Stripe checkout at `/checkout`.

## Discovery Documents

- OAuth AS Metadata: `/.well-known/oauth-authorization-server`
- OAuth Protected Resource: `/.well-known/oauth-protected-resource`
- API Catalog: `/.well-known/api-catalog`
- OpenAPI Spec: `/openapi.json`
- Agent Skills: `/.well-known/agent-skills/index.json`
- MCP Server Card: `/.well-known/mcp/server-card.json`
"""
    return Response(content=content, media_type="text/markdown; charset=utf-8")


# --- MCP Server Card (SEP-1649) ---
@app.get("/.well-known/mcp/server-card.json")
async def mcp_server_card():
    """MCP Server Card per SEP-1649 draft standard."""
    import json
    card = {
        "schemaVersion": "1.0",
        "serverInfo": {
            "name": "knob.monster",
            "version": "1.0.0",
            "description": "Cloud SysEx librarian for vintage synthesizers. Back up, organize, and recall MIDI patch banks via Web MIDI.",
            "homepage": SITE_BASE,
            "logo": f"{SITE_BASE}/static/logo.svg"
        },
        "transport": {
            "type": "http",
            "endpoint": f"{SITE_BASE}/mcp"
        },
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": False,
            "sampling": False
        },
        "tools": [
            {
                "name": "list_banks",
                "description": "List all SysEx patch banks in the authenticated user's library",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_bank",
                "description": "Get the patches in a specific SysEx bank by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bank_id": {"type": "integer", "description": "The bank ID to retrieve"}
                    },
                    "required": ["bank_id"]
                }
            }
        ],
        "authentication": {
            "type": "session_cookie",
            "loginEndpoint": f"{SITE_BASE}/login",
            "registerEndpoint": f"{SITE_BASE}/signup"
        },
        "contact": {
            "url": f"{SITE_BASE}/shop"
        }
    }
    return Response(
        content=json.dumps(card, indent=2),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# --- Agent Skills Discovery Index (Cloudflare RFC v0.2.0) ---
@app.get("/.well-known/agent-skills/index.json")
async def agent_skills_index():
    """Agent Skills Discovery Index per Cloudflare RFC v0.2.0."""
    import json
    index = {
        "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
        "skills": [
            {
                "name": "sysex-backup",
                "type": "skill-md",
                "description": "Back up SysEx patch banks from vintage synthesizers to the cloud via Web MIDI",
                "url": f"{SITE_BASE}/llms.txt",
                "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            },
            {
                "name": "patch-search",
                "type": "skill-md",
                "description": "Search and retrieve specific named patches from stored SysEx bank archives",
                "url": f"{SITE_BASE}/llms.txt",
                "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            },
            {
                "name": "bank-recall",
                "type": "skill-md",
                "description": "Flash a complete SysEx bank back to synthesizer hardware RAM in one operation",
                "url": f"{SITE_BASE}/llms.txt",
                "digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
            }
        ]
    }
    return Response(
        content=json.dumps(index, indent=2),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# --- MPP / OpenAPI spec with x-payment-info extensions ---
@app.get("/openapi.json")
async def openapi_spec():
    """OpenAPI 3.1 spec with MPP x-payment-info extensions on premium endpoints."""
    import json
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "knob.monster API",
            "version": "1.0.0",
            "description": "Cloud SysEx librarian API for vintage synthesizers. Manage MIDI patch banks and SysEx dumps.",
            "contact": {"url": SITE_BASE},
            "license": {"name": "Proprietary", "url": f"{SITE_BASE}/terms"}
        },
        "servers": [{"url": SITE_BASE, "description": "Production"}],
        "paths": {
            "/status": {
                "get": {
                    "operationId": "getStatus",
                    "summary": "Health check",
                    "description": "Returns operational status of all services",
                    "responses": {
                        "200": {"description": "Service is operational"}
                    }
                }
            },
            "/banks": {
                "get": {
                    "operationId": "listBanks",
                    "summary": "List all SysEx patch banks",
                    "description": "Returns all SysEx banks in the authenticated user's library. Requires premium lifetime access.",
                    "x-payment-info": {
                        "intent": "session",
                        "method": "stripe",
                        "amount": 3900,
                        "currency": "USD",
                        "description": "Premium lifetime access required ($39 one-time)"
                    },
                    "security": [{"sessionCookie": []}],
                    "responses": {
                        "200": {"description": "List of banks"},
                        "401": {"description": "Not authenticated"},
                        "402": {"description": "Premium lifetime access required"}
                    }
                },
                "post": {
                    "operationId": "createBank",
                    "summary": "Upload a SysEx patch bank",
                    "description": "Upload a new SysEx bank (hex string). Requires premium lifetime access.",
                    "x-payment-info": {
                        "intent": "session",
                        "method": "stripe",
                        "amount": 3900,
                        "currency": "USD",
                        "description": "Premium lifetime access required ($39 one-time)"
                    },
                    "security": [{"sessionCookie": []}],
                    "requestBody": {
                        "content": {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "synth_model": {"type": "string"},
                                        "sysex_hex": {"type": "string"}
                                    },
                                    "required": ["name", "synth_model", "sysex_hex"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Bank created"},
                        "402": {"description": "Premium lifetime access required"}
                    }
                }
            },
            "/banks/{bank_id}": {
                "get": {
                    "operationId": "getBank",
                    "summary": "Get patches in a SysEx bank",
                    "security": [{"sessionCookie": []}],
                    "parameters": [{"name": "bank_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Bank patches"}, "404": {"description": "Not found"}}
                },
                "delete": {
                    "operationId": "deleteBank",
                    "summary": "Delete a SysEx bank",
                    "security": [{"sessionCookie": []}],
                    "parameters": [{"name": "bank_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Deleted"}}
                }
            },
            "/banks/{bank_id}/download": {
                "get": {
                    "operationId": "downloadBank",
                    "summary": "Download bank as .syx binary file",
                    "security": [{"sessionCookie": []}],
                    "parameters": [{"name": "bank_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "SysEx binary file"}}
                }
            },
            "/api/geoip": {
                "get": {
                    "operationId": "getGeoip",
                    "summary": "GeoIP country lookup",
                    "responses": {"200": {"description": "Country info"}}
                }
            }
        },
        "components": {
            "securitySchemes": {
                "sessionCookie": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session_user",
                    "description": "Signed session cookie obtained via POST /login"
                }
            }
        }
    }
    return Response(
        content=json.dumps(spec, indent=2),
        media_type="application/openapi+json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# --- UCP: Universal Commerce Protocol discovery ---
@app.get("/.well-known/ucp")
async def ucp_discovery():
    """Universal Commerce Protocol discovery document."""
    import json
    doc = {
        "protocol": "ucp",
        "version": "1.0",
        "services": ["checkout", "subscription"],
        "capabilities": ["stripe_checkout", "recurring_billing"],
        "endpoints": {
            "checkout": f"{SITE_BASE}/checkout",
            "portal": f"{SITE_BASE}/portal",
            "status": f"{SITE_BASE}/status"
        },
        "spec": "https://ucp.dev/specification/overview/"
    }
    return Response(
        content=json.dumps(doc, indent=2),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# --- ACP: Agentic Commerce Protocol discovery ---
@app.get("/.well-known/acp.json")
async def acp_discovery():
    """Agentic Commerce Protocol discovery document per agenticcommerce.dev."""
    import json
    doc = {
        "protocol": {
            "name": "acp",
            "version": "1.0"
        },
        "api_base_url": SITE_BASE,
        "transports": ["https"],
        "capabilities": {
            "services": ["one-time"],
            "payment_methods": ["card", "apple_pay", "google_pay", "cashapp", "pix", "naver_pay", "usdc"],
            "currencies": ["USD", "BRL", "KRW"],
            "billing_periods": ["lifetime"]
        },
        "endpoints": {
            "checkout": f"{SITE_BASE}/checkout",
            "portal": f"{SITE_BASE}/portal",
            "status": f"{SITE_BASE}/status"
        },
        "pricing": {
            "lifetime": {"amount": 2900, "currency": "USD", "interval": "one-time"}
        }
    }
    return Response(
        content=json.dumps(doc, indent=2),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"}
    )


# ============================================================
# Wildcard fallback route for Programmatic SEO Synthesizer landing pages
# MUST remain the last route
# ============================================================
WIKI_DATA = {
    "dx7": {
        "brand": "Yamaha",
        "name": "Yamaha DX7",
        "year": "1983",
        "engine": "FM Synthesis (6 Operators, 32 Algorithms)",
        "polyphony": "16 voices",
        "dac": "12-bit (Burr-Brown YM21280 + YM3012)",
        "presets_count": "32 Internal, 64 ROM",
        "rarity": "⭐⭐★★★ (Common but iconic)",
        "famous_tracks": ["A-ha - Take On Me", "Kenny Loggins - Danger Zone", "Whitney Houston - Saving All My Love For You", "Harold Faltermeyer - Axel F"],
        "factory_presets": ["1 - ROM1A Brass 1", "2 - ROM1A Brass 2", "3 - ROM1A E.Piano 1", "4 - ROM1A E.Piano 2", "5 - ROM1A Pipes 1", "6 - ROM1A Harpsichord 1", "7 - ROM1A Clav 1", "8 - ROM1A Organ 1", "9 - ROM1A Lead 1", "10 - ROM1A Bass 1", "11 - ROM1A Synth 1", "12 - ROM1A Strings 1", "13 - ROM1A Flute 1", "14 - ROM1A Marimba", "15 - ROM1A Tubular Bells", "16 - ROM1A Train"],
        "wiki_text": "Launched in 1983, the Yamaha DX7 was the first commercially successful digital synthesizer, completely transforming the sound of 1980s pop music. Powered by Frequency Modulation (FM) synthesis designed by John Chowning at Stanford, it offered glassy electric pianos, punchy brass, and digital bell sounds that analog subtractive synths of the era simply could not replicate. Programming the DX7 is notoriously difficult due to its tiny LCD screen and lack of physical sliders, making custom librarians and patch backups highly essential.",
        "funny_anecdote": "During the 1984 recording of a popular power ballad, the session keyboardist got his tie caught in the floppy disk drive of a nearby emulator, panic-slapped the DX7's membrane buttons with his chin, and accidentally programmed the famous glassy electric piano preset ('E.PIANO 1'). The producer loved it so much he kept the take and bought the keyboardist a clip-on tie."
    },
    "juno-106": {
        "brand": "Roland",
        "name": "Roland Juno-106",
        "year": "1984",
        "engine": "Subtractive Analog (1 DCO per voice, 24dB LPF)",
        "polyphony": "6 voices",
        "dac": "Analog Voice Cards (80017a VCF/VCA chips)",
        "presets_count": "128 Patches (Group A/B)",
        "rarity": "⭐⭐⭐★★ (Classic & sought-after)",
        "famous_tracks": ["Daft Punk - Around the World", "Tame Impala - Feels Like We Only Go Backwards", "Duran Duran - Save a Prayer", "Depeche Mode - Personal Jesus"],
        "factory_presets": ["A11 - Group Strings 1", "A12 - Warm Brass", "A13 - E.Piano 1", "A14 - Funky Clav", "A15 - Cathedral Organ", "A16 - Acoustic Harp", "A17 - Bell Pad", "A18 - Reso Lead", "A21 - Poly Synth Bass", "A22 - Sub Bass", "A23 - Sync Lead", "A24 - Space Flute"],
        "wiki_text": "The Roland Juno-106 is a legendary 6-voice polyphonic analog synthesizer released in 1984. It is widely praised for its lush, warm sound, driven by a gorgeous built-in stereo chorus circuit and digital-controlled analog oscillators (DCOs). The Juno-106 is famously prone to voice-chip failures due to deteriorating resin on its custom 80017A chips, requiring regular diagnostic monitoring and calibration. It features a complete MIDI implementation, allowing full parameter control and patch dumps via SysEx.",
        "funny_anecdote": "In 1986, a British synth-pop duo discovered that putting their Juno-106 next to a running commercial microwave oven caused the failing voice chips to temporarily self-align via electromagnetic interference, but only when cooking a microwave burrito. They spent their entire tour budget on burritos to keep the synth in tune."
    },
    "korg-m1": {
        "brand": "Korg",
        "name": "Korg M1",
        "year": "1988",
        "engine": "AI Synthesis (PCM Sample Playback)",
        "polyphony": "16 voices",
        "dac": "16-bit",
        "presets_count": "100 Programs, 100 Combinations",
        "rarity": "⭐⭐★★★ (Mass-produced classic)",
        "famous_tracks": ["Madonna - Vogue", "Robin S. - Show Me Love", "Queen - Innuendo", "Pet Shop Boys - It's a Sin"],
        "factory_presets": ["00 - Universe", "01 - Piano 16'", "02 - Brass Section", "03 - Organ 2", "04 - Guitar 1", "05 - Overture", "06 - Pan Flute", "07 - Choir", "08 - Bass & Lead", "09 - Lore"],
        "wiki_text": "Released in 1988, the Korg M1 is widely recognized as the first defining digital music workstation, outselling even the Yamaha DX7. It combined multi-sampled PCM ROM waveforms with built-in digital effects, sequencer, and drum sounds, letting composers produce complete tracks on a single machine. The M1's signature 'Universe' pad, 'Piano 16'' preset, and house organ patch have shaped electronic and pop music for decades.",
        "funny_anecdote": "The iconic 'Universe' preset pad was allegedly created when a sound designer accidentally left a microphone active next to a boiling kettle while sample-looping a choir waveform. The resulting steam hiss blended so perfectly with the digital PCM wave that Korg engineers declared it a 'transcendental acoustic event' and kept it."
    },
    "jupiter-6": {
        "brand": "Roland",
        "name": "Roland Jupiter-6",
        "year": "1983",
        "engine": "Subtractive Analog (2 VCOs per voice, Multi-mode Filter)",
        "polyphony": "6 voices",
        "dac": "Pure Analog",
        "presets_count": "72 Patches",
        "rarity": "⭐⭐⭐⭐★ (Rare & expensive)",
        "famous_tracks": ["Philip Glass - Glassworks", "Moby - Go", "Orbital - Halcyon on and on"],
        "factory_presets": ["11 - Poly Brass", "12 - Sync Lead", "13 - Reso Clav", "14 - String Choir", "15 - Square Pad", "16 - Noise FX"],
        "wiki_text": "The Roland Jupiter-6 (1983) is an iconic, aggressive subtractive analog synthesizer. It was one of the very first commercial synthesizers to feature the newly established MIDI protocol. Famous for its multi-mode resonant filter (offering LP, HP, and Bandpass options) and stable CEM3340 oscillators, it excels at metallic FX, soaring sync leads, and glassy soundscapes.",
        "funny_anecdote": "Rumor has it that a famous ambient artist tried to clean the slider dust on his Jupiter-6 using a vacuum cleaner set to high. The suction pulled the resonance parameters so far beyond factory specs that it started picking up a local amateur radio broadcast of a football game. He recorded it, called it 'Radioactive Dust,' and sold 50,000 copies."
    },
    "casio-cz-101": {
        "brand": "Casio",
        "name": "Casio CZ-101",
        "year": "1984",
        "engine": "Phase Distortion (PD) Synthesis",
        "polyphony": "4 voices (8 in mono)",
        "dac": "12-bit Digital",
        "presets_count": "16 Factory, 16 Memory",
        "rarity": "⭐⭐★★★ (Affordable classic)",
        "famous_tracks": ["Vince Clarke - Erasure projects", "Moby - early techno tracks", "They Might Be Giants - various tracks"],
        "factory_presets": ["1 - Brass Ensemble", "2 - Trumpet", "3 - Violin", "4 - Flute", "5 - Elec Piano", "6 - Jazz Organ", "7 - Synth Harpsichord", "8 - Synth Bass"],
        "wiki_text": "The Casio CZ-101 (1984) brought digital synthesis to the masses using Casio's proprietary Phase Distortion (PD) engine. PD synthesis mimics analog filters by dynamically distorting the phase angle of a sine wave carrier. The CZ-101 is compact, features micro-keys, and is highly valued for quirky leads, digital organs, and punchy synth basses.",
        "funny_anecdote": "The CZ-101 was so small it was frequently mistaken for a toy. One famous keyboard player accidentally packed it in his 6-year-old daughter's school lunchbox instead of her plastic keyboard toy. She ended up performing a noise-gate improv session at show-and-tell that reportedly frightened three teachers."
    },
    "yamaha-tx81z": {
        "brand": "Yamaha",
        "name": "Yamaha TX81Z",
        "year": "1986",
        "engine": "4-Operator FM Synthesis (8 Waveforms)",
        "polyphony": "8 voices (8-part multitimbral)",
        "dac": "12-bit",
        "presets_count": "128 Factory, 32 User",
        "rarity": "⭐⭐★★★ (Ubiquitous rack module)",
        "famous_tracks": ["Baby D - Let Me Be Your Fantasy", "LFO - LFO", "Fluke - various house tracks"],
        "factory_presets": ["I11 - Lately Bass", "I12 - E.Grand", "I13 - Toy Box", "I14 - Tubular", "I15 - Flat Flute", "I16 - Wire Str"],
        "wiki_text": "The Yamaha TX81Z (1986) is a legendary 1U rack-mount FM expander module. While it only features 4 operators, it was the first FM synth to offer non-sinusoidal waveforms, allowing for aggressive and gritty timbres. Its 'Lately Bass' patch is arguably the most famous FM bass sound in history, defining early UK house and techno.",
        "funny_anecdote": "The legendary 'Lately Bass' patch was originally named 'Accidentally Bass'. The sound designer was attempting to program a bell sound but fell asleep on the keypad. When he woke up, his forehead had pressed the operator ratios into a weird sub-octave configuration. He decided not to delete it."
    },
    "roland-d-50": {
        "brand": "Roland",
        "name": "Roland D-50",
        "year": "1987",
        "engine": "Linear Arithmetic (LA) Synthesis",
        "polyphony": "16 voices",
        "dac": "16-bit Custom DAC",
        "presets_count": "64 Patches",
        "rarity": "⭐⭐⭐★★ (Classic 80s titan)",
        "famous_tracks": ["Enya - Orinoco Flow", "Michael Jackson - Bad", "Jean-Michel Jarre - Revolutions"],
        "factory_presets": ["11 - Fantasia", "12 - Digital Native Dance", "13 - Staccato Heaven", "14 - Cathedral Organ", "15 - Soundtrack", "16 - Glass Voices"],
        "wiki_text": "Released in 1987 to rival the DX7, the Roland D-50 introduced Linear Arithmetic (LA) synthesis. LA synthesis combined short PCM acoustic samples (like the transient strike of a bell or flute chuff) with digital subtractive synthesis. This hybrid approach created rich, complex, and evolving textures like 'Fantasia' and 'Digital Native Dance'.",
        "funny_anecdote": "The 'Digital Native Dance' patch was so popular that a TV studio once sued a local supermarket, claiming the supermarket's checkout scanners were ripping off the patch's opening transient click. The lawsuit was dismissed when it was revealed both the scanner and the patch used the exact same 8-bit PCM click sample from a public library."
    },
    "prophet-600": {
        "brand": "Sequential",
        "name": "Prophet-600",
        "year": "1982",
        "engine": "Subtractive Analog (2 VCOs per voice)",
        "polyphony": "6 voices",
        "dac": "Pure Analog (Z80 microprocessor for envelopes)",
        "presets_count": "100 Patches",
        "rarity": "⭐⭐⭐⭐★ (Highly desirable)",
        "famous_tracks": ["Front 242 - early tracks", "Hardfloor - acid house classics"],
        "factory_presets": ["00 - Brass 1", "01 - String Pad", "02 - Reso Sweep", "03 - Sync Lead", "04 - Organ 1", "05 - FX Growl"],
        "wiki_text": "The Sequential Circuits Prophet-600, released in late 1982, holds the historic distinction of being the first commercial synthesizer equipped with MIDI. It features 6 analog voices utilizing Curtis CEM3340 oscillators and CEM3372 filter chips. Today, many users install the custom GliGli firmware upgrade to improve envelope speeds and add full SysEx control.",
        "funny_anecdote": "During the historic first-ever public demonstration of MIDI between the Prophet-600 and a Roland Jupiter-6 in 1983, the connection initially failed because someone plugged the MIDI cable into a headphone jack. The loud feedback loop was mistaken by the audience for a cutting-edge avant-garde solo, resulting in a standing ovation."
    },
    "oberheim-matrix-1000": {
        "brand": "Oberheim",
        "name": "Oberheim Matrix-1000",
        "year": "1988",
        "engine": "Subtractive Analog (DCO-based Matrix Modulation)",
        "polyphony": "6 voices",
        "dac": "Pure Analog Voice Path",
        "presets_count": "800 ROM, 200 RAM (User)",
        "rarity": "⭐⭐⭐★★ (Sought-after analog rack)",
        "famous_tracks": ["Aphex Twin - Selected Ambient Works", "Juno Reactor - early trance"],
        "factory_presets": ["000 - Classic Brass", "001 - Reso Bass", "002 - Soft Pad", "003 - Sync Wave", "004 - Bell Synth", "005 - Space String"],
        "wiki_text": "The Oberheim Matrix-1000 (1988) packed 1,000 analog synth patches into a single rack space. Driven by CEM3396 chips, it features Oberheim's powerful matrix modulation routing system. Because the front panel has no editing controls, managing user RAM banks and designing patches is completely dependent on external MIDI SysEx editors.",
        "funny_anecdote": "Since the Matrix-1000 has 1,000 presets and no physical editing knobs, a musician once spent four days clicking the 'preset up' button to find his favorite lead patch. On press 843, he suffered a finger cramp, skipped it, and had to click another 157 times to cycle back. He sold the rack unit the next morning."
    },
    "yamaha-fb-01": {
        "brand": "Yamaha",
        "name": "Yamaha FB-01",
        "year": "1986",
        "engine": "4-Operator FM Synthesis (YM2164 chip)",
        "polyphony": "8 voices (8-part multitimbral)",
        "dac": "10-bit FM",
        "presets_count": "240 ROM, 96 RAM (User)",
        "rarity": "⭐⭐★★★ (Affordable rack space-saver)",
        "famous_tracks": ["Early DOS/PC game soundtracks", "underground Detroit techno tracks"],
        "factory_presets": ["Bank 1: 1 - E.Piano", "Bank 1: 2 - Brass", "Bank 1: 3 - Flute", "Bank 1: 4 - Bass 1", "Bank 1: 5 - Bell", "Bank 1: 6 - Strings"],
        "wiki_text": "The Yamaha FB-01 (1986) is a budget-friendly 4-operator FM sound module. It lacks a front panel display for editing parameters, relying entirely on external computer editors and MIDI SysEx patch dumps. It is highly multitimbral, making it a popular choice for budget 80s MIDI studios and retro PC gaming setups.",
        "funny_anecdote": "The FB-01 looked so much like a black brick that a stage crew member once used it to prop open a fire exit door during a festival. It spent three hours under rain and mud, but when plugged back in, it still booted up and played the FM brass patches perfectly, albeit with a slight damp hum."
    },
    "roland-juno-60": {
        "brand": "Roland",
        "name": "Roland Juno-60",
        "year": "1982",
        "engine": "Subtractive Analog (1 DCO with Sub-oscillator)",
        "polyphony": "6 voices",
        "dac": "Pure Analog voice architecture",
        "presets_count": "56 Patches",
        "rarity": "⭐⭐⭐⭐★ (Prestige collector synth)",
        "famous_tracks": ["Eurythmics - Sweet Dreams", "Billy Joel - Pressure", "Howard Jones - various hits"],
        "factory_presets": ["11 - Poly Brass", "12 - Organ", "13 - E.Piano", "14 - Clav", "15 - Cathedral", "16 - Strings 1", "21 - Reso Bass", "22 - Flute"],
        "wiki_text": "The Roland Juno-60 (1982) is famous for its punchy sound, solid bass, and stunning analog chorus circuit. Unlike the Juno-106, the Juno-60 uses a proprietary DCB interface rather than standard MIDI. However, units with retrofits (like Minerva or Tubbutec) can be fully controlled via modern MIDI and SysEx, unlocking patch backup and automation capabilities.",
        "funny_anecdote": "A keyboard player once claimed his Juno-60 was haunted because it would play random arpeggiator patterns at night. It was later discovered that his pet hamster had escaped and was running back and forth across the keybed, sync'd perfectly to the external clock of a drum machine."
    },
    "korg-wavestation": {
        "brand": "Korg",
        "name": "Korg Wavestation",
        "year": "1990",
        "engine": "Vector Synthesis & Wave Sequencing",
        "polyphony": "32 voices",
        "dac": "16-bit",
        "presets_count": "150 Performances, 105 Patches",
        "rarity": "⭐⭐⭐★★ (Classic 90s digital powerhouse)",
        "famous_tracks": ["Tony Banks (Genesis) - We Can't Dance", "Phil Collins - various tracks", "Gary Numan - Sacrifice"],
        "factory_presets": ["ROM1: 0 - Ski Jam", "ROM1: 1 - Deep Atmosphere", "ROM1: 2 - Wave Song", "ROM1: 3 - Vector Pad", "ROM1: 4 - Bell Vox"],
        "wiki_text": "The Korg Wavestation (1990) introduced vector synthesis and wave sequencing, allowing users to cross-fade between multiple waveforms using a vector joystick. This allowed for long, evolving pads, rhythmic sequences, and morphing digital textures. Backing up Korg Wavestation performances requires careful SysEx channel assignment and memory protect overrides.",
        "funny_anecdote": "The Wavestation's complex wave sequences were so long that a sound designer once left a sequence looping while he went out for lunch. When he returned, the building was surrounded by police because neighbors reported hearing 'evolving alien messages' communicating from the second-floor window."
    }
}


from pydantic import BaseModel
class FAQRequest(BaseModel):
    question: str

@app.post("/api/ask-faq")
def ask_faq(faq_request: FAQRequest, request: Request):
    """
    Endpoint to answer user FAQs using OpenRouter with Mistral Nemo.
    """
    question = faq_request.question

    # Log to PostHog
    if posthog_client:
        client_ip = request.client.host if request.client else "127.0.0.1"
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()

        posthog_client.capture(
            distinct_id=client_ip,
            event="faq_asked",
            properties={"question": question}
        )

    api_key = os.environ.get(
        "OPENROUTER_API_KEY",
        "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"
    )
    model = os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-nemo")

    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://knob.monster",
                "X-Title": "knob.monster FAQ Bot"
            },
            data=json.dumps({
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful, knowledgeable AI assistant for knob.monster, a browser-native cloud SysEx librarian and patch manager designed for vintage synthesizers from the 1980s and 90s. Keep your answers brief, clear, and focused on helping users with their questions. Mention that we support native Web MIDI on modern browsers, meaning no local desktop utilities or drivers are required. We offer a lifetime access plan for a simple $39 one-time payment. We support synths like Yamaha DX7, Roland Juno-106, Korg M1, etc."
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            }).encode('utf-8'),
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode())
            answer = result["choices"][0]["message"]["content"].strip()
            return {"answer": answer}
    except Exception as e:
        logger.error(f"Error querying OpenRouter for FAQ: {e}")
        return {"answer": "Sorry, I'm having trouble connecting to my knowledge base right now. Please try again later."}


@app.get("/{synth_slug}", response_class=HTMLResponse)
async def dynamic_synth_seo(synth_slug: str, request: Request):
    if synth_slug in SEO_DATA:
        user = get_current_user(request)
        wiki_info = WIKI_DATA.get(synth_slug, {
            "brand": "Unknown",
            "name": SEO_DATA[synth_slug].get("synth_name", synth_slug),
            "year": "N/A",
            "engine": "N/A",
            "polyphony": "N/A",
            "dac": "N/A",
            "presets_count": "N/A",
            "rarity": "⭐⭐★★★",
            "famous_tracks": [],
            "factory_presets": [],
            "wiki_text": SEO_DATA[synth_slug].get("description", "")
        })

        return render_template("wiki_detail.html", request, {
            "user": user,
            "seo": SEO_DATA[synth_slug],
            "seo_slug": synth_slug,
            "wiki": wiki_info
        })
    raise HTTPException(status_code=404)


# --- Automated Drip Email Operations (Local & Vercel Cron compatible) ---
async def run_drip_check() -> int:
    """
    Checks for free tier users registered > 1 hour ago who haven't
    received the drip email, sends the email via SMTP, triggers alerts,
    and updates the database. Returns the number of emails sent.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    sent_count = 0
    try:
        # Fetch pending users (force dynamic reload if module has caching issues from startup)
        if not hasattr(database, "get_pending_drip_users"):
            try:
                import importlib
                importlib.reload(database)
                logger.info("Programmatically reloaded database module to load new functions.")
            except Exception as reload_err:
                logger.error(f"Failed to programmatically reload database module: {reload_err}")
        users = database.get_pending_drip_users()
        now = datetime.utcnow()
        
        for u in users:
            try:
                # Parse created_at ISO string
                created_at = datetime.fromisoformat(u["created_at"])
                elapsed = datetime.now() - created_at
                
                # If registered more than 1 hour ago (3600 seconds)
                if elapsed.total_seconds() >= 3600:
                    email = u["email"]
                    user_id = u["id"]
                    
                    # Prepare drip email contents in all small caps (lowercase)
                    subject = "your studio vault is locked"
                    body = f"""hey there,

you signed up for knob monster, but you are currently on the free tier.

right now, your vault is restricted. you can't download your sysex banks back to your computer, upload a second soundbank, or use preset name decoding.

if you successfully tested your synth connection and want to protect your entire collection, it's time to upgrade. knob monster is a professional tool built exclusively for producers who want a bulletproof cloud archive for their vintage synthesizers.

if you have a juno-106, dx7, or m1 sitting in your studio right now, those sounds are vulnerable. all it takes is one internal battery failure or local drive crash to wipe your custom patches forever.

unlock your vault and get full, unlimited access to knob monster today:

👉 https://knob.monster/dashboard

keep the analog alive,

knob monster support

p.s. if you ran into issues setting up your midi connection or parsing your sysex bank, just reply directly to this email and let me know.
"""
                    
                    # Reference global SMTP configuration constants
                    smtp_host = SMTP_HOST
                    smtp_port = SMTP_PORT
                    smtp_user = SMTP_USER
                    smtp_pass = SMTP_PASSWORD
                    smtp_from = SMTP_FROM
                    
                    sent_via_smtp = False
                    if smtp_host and smtp_user and smtp_pass:
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = smtp_from
                            msg['To'] = email
                            msg['Subject'] = subject
                            msg['Reply-To'] = "halfradiationllc@gmail.com"
                            msg.attach(MIMEText(body, 'plain'))
                            
                            server = smtplib.SMTP(smtp_host, int(smtp_port))
                            server.starttls()
                            server.login(smtp_user, smtp_pass)
                            server.sendmail(smtp_from, email, msg.as_string())
                            server.quit()
                            sent_via_smtp = True
                            logger.info(f"drip email successfully sent via smtp to {email}")
                        except Exception as smtp_err:
                            logger.error(f"smtp send failed for {email}: {smtp_err}")
                            
                    # Log/Simulate and send Discord warning/alert
                    if not sent_via_smtp:
                        logger.info(f"[simulated drip email] to: {email}\nsubject: {subject}\nbody:\n{body}")
                        
                    # Send alert to Discord
                    trigger_alert(
                        "drip_email_sent",
                        f"automated paywall drip email sent to `{email}` (via smtp: {sent_via_smtp}).",
                        {
                            "email": email,
                            "elapsed_seconds": int(elapsed.total_seconds()),
                            "smtp_active": bool(smtp_host),
                            "simulated_only": not sent_via_smtp
                        },
                        distinct_id=email
                    )
                    
                    # Mark as sent in DB
                    database.mark_drip_sent(user_id)
                    sent_count += 1
            except Exception as user_err:
                logger.error(f"failed processing drip email for user {u.get('email')}: {user_err}")
    except Exception as e:
        logger.error(f"error during run_drip_check: {e}")
        
    return sent_count

@app.get("/api/cron/send-drips")
async def trigger_drip_cron(request: Request):
    """
    Vercel Cron endpoint to run the drip campaign periodically.
    """
    cron_header = request.headers.get("x-vercel-cron")
    if not cron_header and os.environ.get("VERCEL") == "1":
        raise HTTPException(status_code=401, detail="Unauthorized to trigger cron manually")
        
    sent_count = await run_drip_check()
    return {"status": "success", "emails_sent": sent_count}

NEWSLETTER_TOPICS = [
    "why the DX7 FM synthesis is notoriously hard to program and how to think about operators",
    "the ticking timebomb of NiCad batteries in vintage synths and the horror of ruined mainboards",
    "how vintage floppy disk libraries were organized and the sound of a floppy drive seek",
    "the charm of early digital-to-analog converters like 12-bit DACs in the DSS-1 or Prophet-VS",
    "how Web MIDI communicates directly from the browser without any drivers",
    "the legendary Lately Bass patch on the TX81Z and why it defined 90s dance music",
    "the secret sauce of the Roland Juno-106 chorus circuit and its noisy buckets",
    "the struggle of saving patches to cassette tapes in the early 80s and the high-pitched screech",
    "why sysex dumps fail midway due to buffer overflows on old MIDI interfaces",
    "the Korg M1 Universe preset and how PCM samples changed the industry overnight"
]

def generate_newsletter_content_via_gemini() -> dict:
    import urllib.request
    import urllib.error
    import json
    import random
    
    # Retrieve OpenRouter configuration from environment or fallback defaults
    api_key = os.environ.get(
        "OPENROUTER_API_KEY", 
        "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"
    )
    model = os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-nemo")
    
    fallback_newsletter = {
        "subject": "the ticking timebomb inside your 80s synthesizers",
        "body": """hey there,

if you own a roland juno-106, a korg poly-61, or a yamaha dx7, there is a silent killer sitting on the mainboard right now. it's the internal nickel-cadmium (NiCad) or lithium backup battery.

over time, these old batteries leak corrosive acid that eats through copper traces, destroying mainboards beyond repair. and even if it doesn't leak, once that battery dies, all your custom patches are wiped instantly.

protect your history. connect your synth to knob.monster, back up your custom patches to the cloud in one click, and rest easy knowing they are preserved forever.

upload your patches now:
👉 https://knob.monster/dashboard

keep the analog alive,
knob.monster preservation vault

---
to stop receiving these, you can unsubscribe instantly at:
https://knob.monster/unsubscribe?email={{recipient_email}}
"""
    }

    if not api_key:
        logger.warning("OpenRouter API key is not set. Generating fallback mockup newsletter.")
        return fallback_newsletter

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    selected_topic = random.choice(NEWSLETTER_TOPICS)
    logger.info(f"Selected weekly newsletter topic: {selected_topic}")
    
    prompt = f"""
    You are the automated email system for knob.monster, the premium cloud SysEx librarian for 1983-1995 vintage hardware synthesizers (Juno-106, DX7, Korg M1, etc.).
    Every week you generate a highly engaging, raw, opinionated, or nostalgic email newsletter for vintage synth collectors and hardware musicians (our ICP).
    The tone should be: raw, highly opinionated, nostalgic, slightly cynical about modern software, completely hardware-obsessed, and writing in a lowercase/conversational style.
    Write like a seasoned vintage synth repair technician or a dedicated collector who has spent too many late nights soldering, breathing flux fumes, and dealing with flaky MIDI cables. Use gearhead terms like 'SysEx dumps', 'bucket-brigades', 'VCFs', 'FM hell', 'leaky batteries'. Avoid any happy marketing-speak or standard corporate introduction.

    Generate a JSON object with:
    1. "subject": A catchy, lower-case/conversational email subject line.
    2. "body": A raw, conversational plain text email body.

    Guidelines for "body":
    - Do NOT use HTML tags. Keep it strictly raw plain text.
    - Focus this week's newsletter specifically on this topic: {selected_topic}.
    - Write a brief, punchy post (2 short paragraphs, around 100-150 words). Go deep into a fascinating anecdote, historical hardware fact, opinion, or tip & trick about this topic.
    - Use manual line breaks and spacing between paragraphs. Keep everything clean and lowercase.
    - Start the email with a very casual, lower-case greeting like 'hey,' or 'quick thought,' or just dive straight into the narrative without any greeting.
    - NEVER end the email with a signature, placeholder names, sign-offs, or generic closing salutations like 'Cheers, [Your Name]', 'Sincerely', 'The knob.monster team', 'Best regards', or 'Keep making noise'. Just end with the core thoughts and the dashboard call-to-action.
    - Include a clear link pointing to "https://knob.monster/dashboard" to upload new SysEx banks.
    - Include the exact text at the bottom: "To stop receiving these, you can unsubscribe instantly at: https://knob.monster/unsubscribe?email={{{{recipient_email}}}}"
    """

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "response_format": {
            "type": "json_object"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://knob.monster",
            "X-Title": "knob.monster"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            response_data = json.loads(res.read().decode("utf-8"))
            text_response = response_data["choices"][0]["message"]["content"]
            try:
                # Strip markdown code blocks if the model wrapped it
                cleaned_response = text_response.strip()
                if cleaned_response.startswith("```"):
                    lines = cleaned_response.splitlines()
                    if len(lines) > 2 and lines[-1].startswith("```"):
                        cleaned_response = "\n".join(lines[1:-1]).strip()
                    else:
                        cleaned_response = cleaned_response.strip("`").strip()
                parsed = json.loads(cleaned_response)
                return {
                    "subject": parsed.get("subject", "vintage synth preservation updates").lower(),
                    "body": parsed.get("body", "")
                }
            except Exception as json_err:
                logger.error(f"JSON parsing failed for OpenRouter response: {json_err}. Raw response was:\n{text_response}")
                raise json_err
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {e}")
        return fallback_newsletter

def run_newsletter_broadcast_sync(override_subject: str = None, override_body: str = None):
    try:
        import importlib
        try:
            importlib.reload(database)
        except Exception:
            pass
            
        recipients = database.get_all_newsletter_recipients()
        if not recipients:
            logger.info("No recipients found for newsletter broadcast.")
            return

        if override_subject and override_body:
            subject = override_subject
            body = override_body
        else:
            logger.info("Generating newsletter via Gemini...")
            content = generate_newsletter_content_via_gemini()
            subject = content["subject"]
            body = content["body"]

        # Alert Discord: Broadcast Started
        trigger_alert(
            "newsletter_broadcast_started",
            f"🚀 starting newsletter broadcast to {len(recipients)} recipients.\nsubject: `{subject}`",
            {"recipient_count": len(recipients), "subject": subject},
            distinct_id="newsletter_cron"
        )

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_host = SMTP_HOST
        smtp_port = SMTP_PORT
        smtp_user = SMTP_USER
        smtp_pass = SMTP_PASSWORD
        smtp_from = SMTP_FROM

        sent_count = 0
        failed_count = 0

        server = None
        if smtp_host and smtp_user and smtp_pass:
            try:
                server = smtplib.SMTP(smtp_host, int(smtp_port))
                server.starttls()
                server.login(smtp_user, smtp_pass)
            except Exception as conn_err:
                logger.error(f"Failed to connect to SMTP server for newsletter broadcast: {conn_err}")
                server = None

        for email in recipients:
            personal_body = body.replace("{{recipient_email}}", email)
            
            sent_via_smtp = False
            if server:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = smtp_from
                    msg['To'] = email
                    msg['Subject'] = subject
                    msg['Reply-To'] = "halfradiationllc@gmail.com"
                    msg['List-Unsubscribe'] = f"<https://knob.monster/unsubscribe?email={email}>"
                    msg['Precedence'] = "bulk"
                    msg.attach(MIMEText(personal_body, 'plain'))
                    
                    server.sendmail(smtp_from, email, msg.as_string())
                    sent_via_smtp = True
                    sent_count += 1
                except Exception as send_err:
                    logger.error(f"failed to send newsletter to {email}: {send_err}")
                    failed_count += 1
            else:
                logger.info(f"[simulated newsletter email] to: {email}\nsubject: {subject}")
                sent_count += 1

        if server:
            try:
                server.quit()
            except Exception:
                pass

        # Alert Discord: Broadcast Finished
        trigger_alert(
            "newsletter_broadcast_finished",
            f"✅ finished newsletter broadcast. sent: {sent_count}, failed: {failed_count}.",
            {
                "sent_count": sent_count,
                "failed_count": failed_count,
                "subject": subject
            },
            distinct_id="newsletter_cron"
        )
    except Exception as e:
        logger.error(f"Error during newsletter broadcast worker: {e}")
        trigger_alert(
            "newsletter_broadcast_error",
            f"❌ error during newsletter broadcast: {e}",
            {"error": str(e)},
            distinct_id="newsletter_cron"
        )

@app.get("/api/cron/newsletter")
async def trigger_newsletter_cron(request: Request):
    """
    Vercel Cron endpoint to run the weekly newsletter campaign.
    """
    cron_header = request.headers.get("x-vercel-cron")
    if not cron_header and os.environ.get("VERCEL") == "1":
        raise HTTPException(status_code=401, detail="Unauthorized to trigger cron manually")
        
    import threading
    thread = threading.Thread(target=run_newsletter_broadcast_sync)
    thread.start()
    
    return {"status": "broadcast_initiated"}

@app.post("/admin/broadcast-override")
async def admin_broadcast_override(secret: str, override_subject: str = None, override_body: str = None):
    """
    Manual override endpoint to trigger a newsletter broadcast immediately.
    """
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret or secret != admin_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    import threading
    thread = threading.Thread(
        target=run_newsletter_broadcast_sync,
        args=(override_subject, override_body)
    )
    thread.start()
    
    return {"status": "broadcast_initiated"}

@app.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_page(request: Request, email: str = ""):
    """
    Unsubscribe page to allow users to opt-out from the newsletter.
    """
    if email:
        database.add_to_unsubscribed(email)
        trigger_alert(
            "newsletter_unsubscribed",
            f"User `{email}` has unsubscribed from the newsletter.",
            {"email": email},
            distinct_id=email
        )
    return render_template("unsubscribe.html", request, {"email": email})

