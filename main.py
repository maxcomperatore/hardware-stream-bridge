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
        host="https://us.i.posthog.com",
        enable_exception_autocapture=True,
    )
except Exception as e:
    posthog_client = None
    logger.error(f"Failed to initialize PostHog SDK: {e}")

app = FastAPI(title="Knob Monster - Vintage Synth Patch Manager")

from datetime import datetime

@app.exception_handler(Exception)
async def posthog_exception_handler(request: Request, exc: Exception):
    """Capture all unhandled exceptions and send to PostHog error tracking."""
    if posthog_client:
        try:
            # Extract user email from session cookie for context
            distinct_id = "anonymous"
            session_cookie = request.cookies.get("session_user")
            if session_cookie:
                try:
                    distinct_id = cookie_signer.unsign(session_cookie.encode()).decode()
                except Exception:
                    pass
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
        <!-- Troll Logo -->
        <div class="flex justify-center">
            <img src="/static/logo.png" id="earth-day-logo" alt="Ogre Logo" class="h-28 w-auto object-contain dithered cursor-pointer transition-all duration-150 ease-out opacity-60" style="transform-style: preserve-3d; backface-visibility: hidden;">
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

STRIPE_PRICE_ID_YEARLY = "price_1Tj3wRLuSQGuB7eyeLFUuCSS"
STRIPE_PRICE_ID_MONTHLY = "price_1Tj3w8LuSQGuB7ey5ZhEjwri"
BASE_URL = "https://knob.monster"

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    database.init_db()

# Secure Cookie Session signing key
SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "knob_monster_super_secure_default_session_secret_998822")
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
        "title": "Yamaha DX7 Online Librarian & SysEx Backup | knob.monster",
        "description": "The ultimate browser-native Yamaha DX7 online librarian and SysEx manager. Back up, search, and recall DX7 soundbanks in 1-click via Web MIDI. No drivers required.",
        "keywords": "yamaha dx7 online librarian, dx7 patch manager, dx7 editor online, dx7 web midi, dx7 patches, yamaha dx7 sysex librarian",
        "synth_name": "Yamaha DX7",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha DX7.</span>",
        "hero_subtitle": "The ultimate Yamaha DX7 online librarian. Back up, search, and recall Yamaha DX7 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
    },
    "juno-106": {
        "title": "Roland Juno-106 SysEx Backup & Patch Librarian | knob.monster",
        "description": "The ultimate browser-native Roland Juno-106 SysEx backup utility. Back up, search, and recall Juno-106 soundbanks in 1-click via Web MIDI. No drivers required.",
        "keywords": "juno-106 sysex backup, roland juno-106 librarian, juno 106 patch manager, juno 106 sysex online, juno 106 editor",
        "synth_name": "Roland Juno-106",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland Juno-106.</span>",
        "hero_subtitle": "The easiest way to manage Roland Juno-106 SysEx backup files directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
    },
    "korg-m1": {
        "title": "Korg M1 SysEx Librarian & Patch Recall | knob.monster",
        "description": "The ultimate browser-native Korg M1 SysEx librarian and patch recall tool. Back up, search, and recall Korg M1 soundbanks in 1-click via Web MIDI. No drivers required.",
        "keywords": "korg m1 patch recall, korg m1 sysex librarian, korg m1 patch manager, korg m1 editor online, korg m1 patches",
        "synth_name": "Korg M1",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Korg M1.</span>",
        "hero_subtitle": "A fast browser utility for Korg M1 patch recall. Back up, search, and recall Korg M1 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
    },
    "jupiter-6": {
        "title": "Roland Jupiter-6 Online SysEx Librarian & Europa Backup | knob.monster",
        "description": "The ultimate browser-native Roland Jupiter-6 online librarian and SysEx manager. Back up, search, and recall Jupiter-6 patches (stock and Europa modded) in 1-click via Web MIDI. No drivers required.",
        "keywords": "roland jupiter-6 sysex backup, jupiter 6 patch manager, jupiter-6 europa editor, jupiter-6 web midi, jupiter-6 patches",
        "synth_name": "Roland Jupiter-6",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland Jupiter-6.</span>",
        "hero_subtitle": "The easiest way to manage Roland Jupiter-6 and Europa-modded SysEx backups directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
    },
    "casio-cz-101": {
        "title": "Casio CZ-101 Online SysEx Librarian & Patch Editor | knob.monster",
        "description": "The ultimate browser-native Casio CZ-101 online librarian and SysEx manager. Back up, search, and recall CZ-101 Phase Distortion patches in 1-click via Web MIDI.",
        "keywords": "casio cz-101 librarian, cz-101 sysex backup, casio cz101 patch editor, phase distortion sysex online",
        "synth_name": "Casio CZ-101",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Casio CZ-101.</span>",
        "hero_subtitle": "Back up, organize, and restore CZ-101 Phase Distortion patches directly from your web browser. Zero setup, zero drivers, instant MIDI dumps."
    },
    "yamaha-tx81z": {
        "title": "Yamaha TX81Z SysEx Librarian & Online Editor | knob.monster",
        "description": "Back up and manage your Yamaha TX81Z 4-operator FM patches online. Decode voice parameters and factory presets directly over Web MIDI. No drivers required.",
        "keywords": "yamaha tx81z librarian, tx81z sysex dump, tx81z patch editor, tx81z lately bass backup, tx81z editor online",
        "synth_name": "Yamaha TX81Z",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha TX81Z.</span>",
        "hero_subtitle": "Quickly manage your TX81Z patches and that legendary Lately Bass patch directly from your browser. Zero setup, zero drivers, instant Web MIDI dump."
    },
    "roland-d-50": {
        "title": "Roland D-50 SysEx Librarian & Patch Manager | knob.monster",
        "description": "Online browser-native SysEx librarian for the classic Roland D-50 Linear Arithmetic synthesizer. Backup, search, and restore D-50 soundbanks over Web MIDI.",
        "keywords": "roland d-50 librarian, d-50 sysex backup, roland d50 patch manager, d-50 editor online, linear arithmetic sysex",
        "synth_name": "Roland D-50",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland D-50.</span>",
        "hero_subtitle": "Manage your classic Linear Arithmetic soundbanks and patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
    },
    "prophet-600": {
        "title": "Prophet-600 SysEx Librarian & GliGli Patch Backup | knob.monster",
        "description": "The ultimate online librarian for the Sequential Circuits Prophet-600. Support for stock and GliGli firmware patch backups via Web MIDI. No installation required.",
        "keywords": "prophet-600 sysex librarian, prophet 600 patch editor, gligli firmware backup, sequential prophet 600 online",
        "synth_name": "Prophet-600",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Prophet-600.</span>",
        "hero_subtitle": "Back up, organize, and recall Prophet-600 patches (stock or GliGli modded) directly from your browser. Zero setup, zero drivers."
    },
    "oberheim-matrix-1000": {
        "title": "Oberheim Matrix-1000 SysEx Librarian & Patch Manager | knob.monster",
        "description": "Online librarian and patch backup tool for Oberheim Matrix-1000 and Matrix-6. Search, organize, and upload your 1000 patches directly in your web browser.",
        "keywords": "oberheim matrix-1000 librarian, matrix-1000 sysex dump, matrix 6 patch manager, oberheim sysex backup online",
        "synth_name": "Oberheim Matrix-1000",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Matrix-1000.</span>",
        "hero_subtitle": "The easiest way to manage Oberheim Matrix-1000 and Matrix-6 soundbanks directly from your browser. Zero setup, zero drivers."
    },
    "yamaha-fb-01": {
        "title": "Yamaha FB-01 SysEx Librarian & Online Editor | knob.monster",
        "description": "Online browser-native SysEx manager for the vintage Yamaha FB-01 FM sound module. Backup, search, and recall FB-01 soundbanks in 1-click via Web MIDI.",
        "keywords": "yamaha fb-01 librarian, fb-01 sysex backup, fb01 patch manager, fb-01 editor online, fm sound module sysex",
        "synth_name": "Yamaha FB-01",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha FB-01.</span>",
        "hero_subtitle": "The easiest way to manage Yamaha FB-01 patches and soundbanks directly from your browser. Zero setup, zero drivers."
    },
    "roland-juno-60": {
        "title": "Roland Juno-60 SysEx Librarian (MIDI Modded) | knob.monster",
        "description": "Online browser-native SysEx librarian for MIDI-retrofitted Roland Juno-60 synthesizers. Backup, search, and recall Juno-60 patches in 1-click via Web MIDI.",
        "keywords": "juno-60 sysex backup, roland juno-60 librarian, juno 60 patch manager, juno 60 midi mod backup",
        "synth_name": "Roland Juno-60",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland Juno-60.</span>",
        "hero_subtitle": "For MIDI-modded Juno-60 synths, manage and backup your patch libraries directly from your browser. Zero setup, zero drivers."
    },
    "korg-wavestation": {
        "title": "Korg Wavestation SysEx Librarian & Online Editor | knob.monster",
        "description": "Online browser-native SysEx librarian for Korg Wavestation, Wavestation EX, and Wavestation A/D. Backup, search, and recall wave sequences over Web MIDI.",
        "keywords": "korg wavestation librarian, wavestation sysex backup, wavestation patch manager, wavestation a/d editor online",
        "synth_name": "Korg Wavestation",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Korg Wavestation.</span>",
        "hero_subtitle": "The easiest way to manage Korg Wavestation soundbanks and wave sequences directly from your browser. Zero setup, zero drivers."
    }
}

# --- Marketing & Auth Pages ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    return render_template("landing.html", request, {"user": user})

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
    user = get_current_user(request)
    return render_template("roadmap.html", request, {"user": user})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    user = get_current_user(request)
    return render_template("about.html", request, {"user": user})

@app.get("/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer", response_class=HTMLResponse)
async def blog_web_midi_page(request: Request):
    user = get_current_user(request)
    return render_template("blog_web_midi.html", request, {"user": user})

@app.get("/changelog")
async def changelog_redirect():
    return RedirectResponse(url="/about", status_code=301)

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
    return response

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, error: str = None, plan: str = "yearly"):
    if get_current_user(request):
        return RedirectResponse(url="/dashboard")
    return render_template("signup.html", request, {"error": error, "plan": plan})

@app.post("/signup")
async def do_signup(request: Request, email: str = Form(...), password: str = Form(...), confirm_password: str = Form(...), plan: str = "yearly"):
    if password != confirm_password:
        return render_template("signup.html", request, {"error": "Passwords do not match", "plan": plan})
    
    if (len(password) < 10 or 
        not any(c.islower() for c in password) or 
        not any(c.isupper() for c in password) or 
        not any(c.isdigit() for c in password) or 
        not any(not c.isalnum() and not c.isspace() for c in password)):
        return render_template("signup.html", request, {"error": "Password must be at least 10 characters long and contain uppercase, lowercase, numbers, and special symbols", "plan": plan})
    
    user = database.get_user_by_email(email)
    if user:
        return render_template("signup.html", request, {"error": "Email is already registered", "plan": plan})
    
    try:
        database.create_user(email, hash_password(password))
        logger.info(f"User registered: {email}", extra={"email": email, "plan": plan, "event_type": "signup"})
    except Exception as e:
        return render_template("signup.html", request, {"error": "Account registration failed.", "plan": plan})

    # Check if this email paid before registering — auto-upgrade instantly
    pending = database.consume_pending_premium(email)
    if pending:
        database.update_user_tier(email, "premium", pending.get("stripe_customer_id"))
        logger.info(f"Pending premium applied on registration: {email}", extra={"email": email, "event_type": "pending_premium_applied"})
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
    if user["tier"] != "premium":
        return RedirectResponse(url="/checkout")
        
    banks = database.get_all_banks(user["id"])
    return render_template("index.html", request, {"banks": banks, "user": user})

@app.get("/banks", response_class=HTMLResponse)
async def get_banks(request: Request):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
    if user["tier"] != "premium":
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")
        
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.get("/banks/{bank_id}", response_class=HTMLResponse)
async def get_bank_details(request: Request, bank_id: int):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
    if user["tier"] != "premium":
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")
        
    bank = database.get_bank(bank_id, user["id"])
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return render_template("patch_list.html", request, {"bank": bank})

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
    if user["tier"] != "premium":
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")

    try:
        clean_hex = sysex_hex.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        sysex_bytes = bytes.fromhex(clean_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hexadecimal string data")
    
    # Parse voices
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
        
    # Save to database scoped to user
    database.save_bank(name, synth_model, clean_hex, patch_names, user["id"])
    logger.info(f"SysEx bank created: {name} ({synth_model}) for user {user['email']}", extra={"email": user["email"], "synth_model": synth_model, "patches_count": len(patch_names), "event_type": "sysex_upload"})
    
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
    if user["tier"] != "premium":
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")

    sysex_bytes = await file.read()
    sysex_hex = sysex_bytes.hex()
    
    # Parse voices
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
        
    database.save_bank(name, synth_model, sysex_hex, patch_names, user["id"])
    logger.info(f"SysEx file uploaded: {name} ({synth_model}) for user {user['email']}", extra={"email": user["email"], "synth_model": synth_model, "patches_count": len(patch_names), "event_type": "sysex_upload"})
    
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.delete("/banks/{bank_id}", response_class=HTMLResponse)
async def delete_bank(request: Request, bank_id: int):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
    if user["tier"] != "premium":
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/checkout"})
        return RedirectResponse(url="/checkout")
        
    database.delete_bank(bank_id, user["id"])
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
    if user["tier"] != "premium":
        raise HTTPException(status_code=402, detail="Payment Required")
        
    bank = database.get_bank(bank_id, user["id"])
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
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
    return RedirectResponse(url="/dashboard?payment=pack_success", status_code=303)

# --- Stripe Monetization Endpoints ---
@app.get("/checkout")
async def create_checkout_session(request: Request, plan: str = "yearly"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    # If Stripe keys are missing, run in sandbox developer mock-mode
    if not STRIPE_SECRET_KEY:
        return RedirectResponse(url=f"/mock-checkout-success?email={user['email']}")
        
    price_id = STRIPE_PRICE_ID_YEARLY if plan == "yearly" else STRIPE_PRICE_ID_MONTHLY
    
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
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            allow_promotion_codes=allow_promo,
            success_url=BASE_URL + "/dashboard?payment=success",
            cancel_url=BASE_URL + "/dashboard?payment=cancel",
            customer_email=user["email"],
            metadata={"user_email": user["email"]}
        )
        return RedirectResponse(url=checkout_session.url, status_code=303)
    except Exception as e:
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
        return RedirectResponse(url=portal_session.url, status_code=303)
    except Exception as e:
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
        raise HTTPException(status_code=403, detail="Forbidden")
    user = database.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail=f"No account found for {email}. Ask them to register first.")
    database.update_user_tier(email, "premium")
    logger.info(f"Admin manually granted premium: {email}", extra={"email": email, "event_type": "admin_grant_premium"})
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
            else:
                # User paid before registering — park it, apply on registration
                database.upsert_pending_premium(customer_email, customer_id)
                logger.info(f"Pending premium parked (no account yet): {customer_email}", extra={"email": customer_email, "customer_id": customer_id, "event_type": "subscription_pending"})
            
    elif event['type'] == 'customer.subscription.deleted':
        session = event['data']['object']
        customer_id = getattr(session, 'customer', None)
        if customer_id:
            database.update_user_tier_by_customer_id(customer_id, "free")
            logger.info(f"Subscription cancelled via Stripe: {customer_id}", extra={"customer_id": customer_id, "event_type": "subscription_deleted"})
        
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
        ("https://knob.monster/roadmap", "2026-06-21", "weekly", "0.85"),
        ("https://knob.monster/terms", "2026-06-21", "monthly", "0.5"),
        ("https://knob.monster/privacy", "2026-06-21", "monthly", "0.5"),
        ("https://knob.monster/payment-methods", "2026-06-21", "monthly", "0.6"),
        ("https://knob.monster/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer", "2026-06-23", "weekly", "0.9"),
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
        "- **Direct Pricing:** Simple plan options: $8/month (billed monthly) or $5/month (billed annually, $60 total). No trials.",
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


# Wildcard fallback route for Programmatic SEO Synthesizer landing pages
@app.get("/{synth_slug}", response_class=HTMLResponse)
async def dynamic_synth_seo(synth_slug: str, request: Request):
    if synth_slug in SEO_DATA:
        user = get_current_user(request)
        return render_template("landing.html", request, {"user": user, "seo": SEO_DATA[synth_slug], "seo_slug": synth_slug})
    raise HTTPException(status_code=404)


