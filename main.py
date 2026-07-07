from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import settings
import io
import os
import zipfile
import hashlib
import hmac
import bcrypt
from itsdangerous import Signer, BadSignature, URLSafeTimedSerializer
import stripe
import database
import parser
import logging
import mimetypes
import traceback
import re
import faq_knowledge
import shop_packs
import research_survey_2026
import research_lessons_launch_2026
import pricing_geo_titles
from icon_paths import (
    brand_icon,
    dinkie_cover_icon,
    dinkie_cover_icon_names,
    dinkie_icon,
    flag_icon,
    stripe_cover_icon,
    stripe_cover_icon_names,
    _RECT_FLAGS_MAP,
)
from urllib.parse import quote, urlparse

def posthog_support_context(user: dict | None, *, enable_conversations: bool = False) -> dict:
    """PostHog init flags: support bubble only on dashboard; signed identity for logged-in users."""
    ctx = {
        "posthog_enable_conversations": False,
        "posthog_identity_distinct_id": None,
        "posthog_identity_hash": None,
    }
    if not enable_conversations or not user:
        return ctx
    distinct_id = user["email"]
    ctx["posthog_enable_conversations"] = True
    ctx["posthog_identity_distinct_id"] = distinct_id
    secret = settings.POSTHOG_CONVERSATIONS_IDENTITY_SECRET
    if secret:
        ctx["posthog_identity_hash"] = hmac.new(
            secret.encode("utf-8"),
            distinct_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    return ctx


def safe_next_url(next_url: str | None, default: str = "/dashboard") -> str:
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        return default
    return next_url

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

CONSUMER_EMAIL_DOMAINS = frozenset({
    "gmail.com", "googlemail.com",
    "yahoo.com", "yahoo.co.uk", "yahoo.co.jp", "ymail.com", "rocketmail.com",
    "hotmail.com", "hotmail.co.uk", "outlook.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com",
    "proton.me", "protonmail.com", "protonmail.ch", "pm.me",
    "aol.com",
    "gmx.com", "gmx.net", "gmx.de",
    "mail.com", "email.com",
    "yandex.com", "yandex.ru",
    "fastmail.com", "fastmail.fm",
    "tutanota.com", "tuta.io",
    "hey.com",
    "qq.com", "163.com", "126.com",
    "inbox.com", "zoho.com",
})


def get_email_domain(email: str) -> str:
    parts = email.lower().strip().rsplit("@", 1)
    return parts[1] if len(parts) == 2 else ""


def is_consumer_email(email: str) -> bool:
    return get_email_domain(email) in CONSUMER_EMAIL_DOMAINS


def resolve_plan_for_email(plan: str, email: str) -> str:
    """Custom / business email domains must purchase Studio, not Personal."""
    normalized = normalize_plan(plan)
    if normalized == "personal" and not is_consumer_email(email):
        return "studio"
    return normalized
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

    if settings.POSTHOG_API_KEY:
        resource = Resource(attributes={"service.name": "knob-monster"})
        logger_provider = LoggerProvider(resource=resource)
        set_logger_provider(logger_provider)

        exporter = OTLPLogExporter(
            endpoint="https://us.i.posthog.com/i/v1/logs",
            headers={"Authorization": f"Bearer {settings.POSTHOG_API_KEY}"},
        )
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

        handler = LoggingHandler(logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)
except Exception as e:
    logger.error(f"Failed to initialize PostHog OTLP Logging: {e}")

# PostHog Python SDK — Error Tracking & Exception Capture
try:
    from posthog import Posthog

    posthog_client = (
        Posthog(
            project_api_key=settings.POSTHOG_API_KEY,
            host=settings.POSTHOG_HOST,
        enable_exception_autocapture=True,
        )
        if settings.POSTHOG_API_KEY
        else None
    )
except Exception as e:
    posthog_client = None
    logger.error(f"Failed to initialize PostHog SDK: {e}")

DISCORD_WEBHOOK_URL = settings.DISCORD_WEBHOOK_URL
DISCORD_LOGO_URL = f"{settings.SITE_BASE}/static/logo.png"

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
    if not DISCORD_WEBHOOK_URL:
        return
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
                "icon_url": DISCORD_LOGO_URL,
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
            "avatar_url": DISCORD_LOGO_URL,
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
    <link rel="stylesheet" href="/static/fonts/knob-monster.css">
    <title>KNOB.MONSTER | Closed for Earth Day</title>
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

SITE_BASE = settings.SITE_BASE
_MARKETING_SECRET = settings.SESSION_SECRET_KEY
_marketing_serializer = (
    URLSafeTimedSerializer(_MARKETING_SECRET, salt="km-marketing-assets") if _MARKETING_SECRET else None
)

PROTECTED_MARKETING_ASSETS = frozenset({
    "studio_detail.avif",
    "midi_handshake.avif",
    "index_extraction.avif",
    "recall_button.avif",
    "trade_offer.avif",
    "bgood.avif",
    "vintage_camera_404.avif",
    "og_banner.png",
})

PREVIEW_BOT_MARKERS = (
    "facebookexternalhit",
    "twitterbot",
    "linkedinbot",
    "discordbot",
    "slackbot",
    "telegrambot",
    "whatsapp",
    "googlebot",
    "bingpreview",
    "applebot",
    "embedly",
    "redditbot",
)

OUR_HOSTS = frozenset({"knob.monster", "www.knob.monster", "localhost", "127.0.0.1"})

MARKETING_ASSETS_DIR = os.path.join(BASE_DIR, "private", "marketing")


def _marketing_media_type(filename: str) -> str:
    if filename.endswith(".avif"):
        return "image/avif"
    if filename.endswith(".png"):
        return "image/png"
    if filename.endswith(".webp"):
        return "image/webp"
    return "application/octet-stream"


def sign_marketing_asset(filename: str) -> str:
    if not _marketing_serializer:
        return quote(filename)
    return quote(_marketing_serializer.dumps(filename))


def marketing_asset_path(filename: str) -> str:
    if filename not in PROTECTED_MARKETING_ASSETS:
        return f"/static/{filename}"
    return f"/m/{filename}?t={sign_marketing_asset(filename)}"


def marketing_asset_abs_url(filename: str) -> str:
    return f"{SITE_BASE}{marketing_asset_path(filename)}"


def _is_preview_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(marker in ua for marker in PREVIEW_BOT_MARKERS)


def _is_our_referer(referer: str) -> bool:
    if not referer:
        return False
    host = urlparse(referer).netloc.lower().split(":", 1)[0]
    return host in OUR_HOSTS or host.endswith(".vercel.app")


def _allow_marketing_asset(request: Request, filename: str, token):
    if filename not in PROTECTED_MARKETING_ASSETS:
        return False
    if not token or not _marketing_serializer:
        return False
    try:
        if _marketing_serializer.loads(token, max_age=60 * 60 * 24 * 7) != filename:
            return False
    except Exception:
        return False
    if _is_preview_bot(request.headers.get("user-agent", "")):
        return True
    sec_fetch_site = (request.headers.get("sec-fetch-site") or "").lower()
    if sec_fetch_site in {"same-origin", "same-site"}:
        return True
    if _is_our_referer(request.headers.get("referer", "")):
        return True
    return False


def dinkie_icon_path(name: str) -> str:
    return dinkie_icon(name)


templates.env.globals["asset_url"] = marketing_asset_path
templates.env.globals["asset_abs_url"] = marketing_asset_abs_url
templates.env.globals["dinkie_icon"] = dinkie_icon_path
templates.env.globals["dinkie_cover_icon"] = dinkie_cover_icon
templates.env.globals["dinkie_cover_icon_names"] = dinkie_cover_icon_names
templates.env.globals["stripe_cover_icon"] = stripe_cover_icon
templates.env.globals["stripe_cover_icon_names"] = stripe_cover_icon_names
templates.env.globals["flag_icon"] = flag_icon
templates.env.globals["brand_icon"] = brand_icon
templates.env.globals["rect_flags_map"] = _RECT_FLAGS_MAP
templates.env.globals["posthog_api_key"] = settings.POSTHOG_API_KEY or ""
templates.env.globals["posthog_api_host"] = settings.POSTHOG_HOST


@app.get("/m/{filename}")
async def serve_marketing_asset(filename: str, request: Request, t=None):
    if filename not in PROTECTED_MARKETING_ASSETS:
        raise HTTPException(status_code=404)
    if not _allow_marketing_asset(request, filename, t):
        raise HTTPException(status_code=403, detail="Forbidden")
    asset_path = os.path.join(MARKETING_ASSETS_DIR, filename)
    if not os.path.isfile(asset_path):
        raise HTTPException(status_code=404)
    return FileResponse(
        asset_path,
        media_type=_marketing_media_type(filename),
        headers={"Cache-Control": "private, no-store"},
    )


@app.middleware("http")
async def block_public_marketing_static(request: Request, call_next):
    path = request.url.path
    if path.startswith("/static/"):
        name = path.rsplit("/", 1)[-1]
        if name in PROTECTED_MARKETING_ASSETS:
            return Response("Forbidden", status_code=403, media_type="text/plain")
    return await call_next(request)

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
    logo_path = os.path.join(BASE_DIR, "static", "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404)

# Mount Static Files
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/gif", ".gif")
mimetypes.add_type("image/svg+xml", ".svg")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Configure Stripe key & fallback mock mode
STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET or ""
stripe.api_key = STRIPE_SECRET_KEY

STRIPE_PRICE_ID_YEARLY = settings.STRIPE_PRICE_ID_YEARLY
STRIPE_PRICE_ID_MONTHLY = settings.STRIPE_PRICE_ID_MONTHLY
STRIPE_PRICE_ID_LIFETIME = settings.STRIPE_PRICE_ID_LIFETIME
STRIPE_PRICE_ID_PERSONAL = settings.STRIPE_PRICE_ID_PERSONAL
STRIPE_PRICE_ID_STUDIO = settings.STRIPE_PRICE_ID_STUDIO
STRIPE_PRICE_ID_PERSONAL_EUR = settings.STRIPE_PRICE_ID_PERSONAL_EUR
STRIPE_PRICE_ID_STUDIO_EUR = settings.STRIPE_PRICE_ID_STUDIO_EUR
STRIPE_PRICE_ID_PERSONAL_GBP = settings.STRIPE_PRICE_ID_PERSONAL_GBP
STRIPE_PRICE_ID_STUDIO_GBP = settings.STRIPE_PRICE_ID_STUDIO_GBP
STRIPE_PRICE_ID_PERSONAL_CAD = settings.STRIPE_PRICE_ID_PERSONAL_CAD
STRIPE_PRICE_ID_STUDIO_CAD = settings.STRIPE_PRICE_ID_STUDIO_CAD
STRIPE_PRICE_ID_PERSONAL_AUD = settings.STRIPE_PRICE_ID_PERSONAL_AUD
STRIPE_PRICE_ID_STUDIO_AUD = settings.STRIPE_PRICE_ID_STUDIO_AUD
STRIPE_PRICE_ID_PERSONAL_CHF = settings.STRIPE_PRICE_ID_PERSONAL_CHF
STRIPE_PRICE_ID_STUDIO_CHF = settings.STRIPE_PRICE_ID_STUDIO_CHF
STRIPE_PRICE_ID_SOUND_PACK = settings.STRIPE_PRICE_ID_SOUND_PACK
PACK_STRIPE_PRICE_ENV_KEYS = {
    "m1_matrix": "STRIPE_PRICE_ID_PACK_M1_MATRIX",
    "dx7_retro": "STRIPE_PRICE_ID_PACK_DX7",
    "juno_nostalgia": "STRIPE_PRICE_ID_PACK_JUNO",
}
BASE_URL = settings.SITE_BASE

EU_EUR_COUNTRY_CODES = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})

GB_GBP_COUNTRY_CODES = frozenset({"GB"})
CA_CAD_COUNTRY_CODES = frozenset({"CA"})
AU_AUD_COUNTRY_CODES = frozenset({"AU"})
CH_CHF_COUNTRY_CODES = frozenset({"CH", "LI"})

COUNTRY_NAME_TO_ISO = {
    "GERMANY": "DE",
    "FRANCE": "FR",
    "ITALY": "IT",
    "SPAIN": "ES",
    "NETHERLANDS": "NL",
    "BELGIUM": "BE",
    "AUSTRIA": "AT",
    "POLAND": "PL",
    "SWEDEN": "SE",
    "DENMARK": "DK",
    "FINLAND": "FI",
    "IRELAND": "IE",
    "PORTUGAL": "PT",
    "GREECE": "GR",
    "CZECHIA": "CZ",
    "CZECH REPUBLIC": "CZ",
    "ROMANIA": "RO",
    "HUNGARY": "HU",
    "CROATIA": "HR",
    "SLOVAKIA": "SK",
    "SLOVENIA": "SI",
    "BULGARIA": "BG",
    "LITHUANIA": "LT",
    "LATVIA": "LV",
    "ESTONIA": "EE",
    "CYPRUS": "CY",
    "LUXEMBOURG": "LU",
    "MALTA": "MT",
    "UNITED KINGDOM": "GB",
    "GREAT BRITAIN": "GB",
    "ENGLAND": "GB",
    "UK": "GB",
    "CANADA": "CA",
    "AUSTRALIA": "AU",
    "SWITZERLAND": "CH",
    "LIECHTENSTEIN": "LI",
}

REGIONAL_PRICING_CATALOG = {
    "usd": {
        "region": "usd",
        "currency": "USD",
        "symbol": "$",
        "personal_amount": "39",
        "studio_amount": "399",
        "billing_label": "USD / ONE-TIME",
    },
    "eur": {
        "region": "eur",
        "currency": "EUR",
        "symbol": "€",
        "personal_amount": "39",
        "studio_amount": "399",
        "billing_label": "EUR / ONE-TIME",
    },
    "gbp": {
        "region": "gbp",
        "currency": "GBP",
        "symbol": "£",
        "personal_amount": "39",
        "studio_amount": "399",
        "billing_label": "GBP / ONE-TIME",
    },
    "cad": {
        "region": "cad",
        "currency": "CAD",
        "symbol": "$",
        "personal_amount": "59",
        "studio_amount": "599",
        "billing_label": "CAD / ONE-TIME",
    },
    "aud": {
        "region": "aud",
        "currency": "AUD",
        "symbol": "$",
        "personal_amount": "59",
        "studio_amount": "599",
        "billing_label": "AUD / ONE-TIME",
    },
    "chf": {
        "region": "chf",
        "currency": "CHF",
        "symbol": "Fr.",
        "personal_amount": "39",
        "studio_amount": "399",
        "billing_label": "CHF / ONE-TIME",
    },
}

def normalize_country_code(raw: str | None) -> str:
    if not raw:
        return "US"
    value = raw.strip().upper()
    if len(value) == 2 and value.isalpha():
        return value
    return COUNTRY_NAME_TO_ISO.get(value, "US")

def eur_pricing_enabled() -> bool:
    return bool(STRIPE_PRICE_ID_PERSONAL_EUR and STRIPE_PRICE_ID_STUDIO_EUR)

def gbp_pricing_enabled() -> bool:
    return bool(STRIPE_PRICE_ID_PERSONAL_GBP and STRIPE_PRICE_ID_STUDIO_GBP)

def cad_pricing_enabled() -> bool:
    return bool(STRIPE_PRICE_ID_PERSONAL_CAD and STRIPE_PRICE_ID_STUDIO_CAD)

def aud_pricing_enabled() -> bool:
    return bool(STRIPE_PRICE_ID_PERSONAL_AUD and STRIPE_PRICE_ID_STUDIO_AUD)

def chf_pricing_enabled() -> bool:
    return bool(STRIPE_PRICE_ID_PERSONAL_CHF and STRIPE_PRICE_ID_STUDIO_CHF)

REGIONAL_PRICE_IDS = {
    "gbp": (STRIPE_PRICE_ID_PERSONAL_GBP, STRIPE_PRICE_ID_STUDIO_GBP),
    "eur": (STRIPE_PRICE_ID_PERSONAL_EUR, STRIPE_PRICE_ID_STUDIO_EUR),
    "cad": (STRIPE_PRICE_ID_PERSONAL_CAD, STRIPE_PRICE_ID_STUDIO_CAD),
    "aud": (STRIPE_PRICE_ID_PERSONAL_AUD, STRIPE_PRICE_ID_STUDIO_AUD),
    "chf": (STRIPE_PRICE_ID_PERSONAL_CHF, STRIPE_PRICE_ID_STUDIO_CHF),
}

def get_pricing_region(country_code: str | None) -> str:
    code = normalize_country_code(country_code)
    if gbp_pricing_enabled() and code in GB_GBP_COUNTRY_CODES:
        return "gbp"
    if chf_pricing_enabled() and code in CH_CHF_COUNTRY_CODES:
        return "chf"
    if cad_pricing_enabled() and code in CA_CAD_COUNTRY_CODES:
        return "cad"
    if aud_pricing_enabled() and code in AU_AUD_COUNTRY_CODES:
        return "aud"
    if eur_pricing_enabled() and code in EU_EUR_COUNTRY_CODES:
        return "eur"
    return "usd"

def get_regional_pricing(country_code: str | None) -> dict:
    return dict(REGIONAL_PRICING_CATALOG[get_pricing_region(country_code)])


def format_free_price_display(regional: dict) -> str:
    region = regional["region"]
    if region == "gbp":
        return "£0"
    if region == "eur":
        return "€0"
    if region == "chf":
        return "Fr. 0"
    if region == "usd":
        return "$0"
    return f"{regional['symbol']}0 {regional['currency']}"


def enrich_regional_pricing(country_code: str | None = None) -> dict:
    regional = get_regional_pricing(country_code)
    return {**regional, "free_price_display": format_free_price_display(regional)}

def resolve_client_ip(request: Request) -> tuple[str, bool]:
    client_ip = request.client.host if request.client else "127.0.0.1"
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(",")[0].strip()
    else:
        cf_connecting_ip = request.headers.get("cf-connecting-ip")
        if cf_connecting_ip:
            client_ip = cf_connecting_ip.strip()
        else:
            x_real_ip = request.headers.get("x-real-ip")
            if x_real_ip:
                client_ip = x_real_ip.strip()

    if client_ip != "localhost":
        import ipaddress
        try:
            ipaddress.ip_address(client_ip)
        except ValueError:
            client_ip = "127.0.0.1"

    is_private = client_ip in ["127.0.0.1", "localhost", "::1"]
    if not is_private and (
        client_ip.startswith("192.168.")
        or client_ip.startswith("10.")
        or any(client_ip.startswith(f"172.{i}.") for i in range(16, 32))
    ):
        is_private = True
    return client_ip, is_private

def lookup_geo_country(client_ip: str, is_private: bool) -> dict:
    import urllib.request
    import json

    try:
        url = "https://ipwho.is/" if is_private else f"https://ipwho.is/{client_ip}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            if data.get("success"):
                return {
                    "country_name": data.get("country"),
                    "country": normalize_country_code(data.get("country_code") or data.get("country")),
                    "ip": data.get("ip") if not is_private else "127.0.0.1",
                }
    except Exception as e:
        logger.error(f"Server-side ipwho.is geoip lookup failed: {e}")

    return {
        "country_name": "everywhere",
        "country": "US",
        "ip": "127.0.0.1",
    }

def get_request_country_code(request: Request) -> str:
    for header in ("cf-ipcountry", "x-vercel-ip-country"):
        code = request.headers.get(header)
        if code and len(code) == 2 and code.upper() != "XX":
            return normalize_country_code(code)
    client_ip, is_private = resolve_client_ip(request)
    geo = lookup_geo_country(client_ip, is_private)
    return normalize_country_code(geo.get("country"))

PLAN_CATALOG = {
    "personal": {
        "label": "Personal",
        "price_display": "$39",
        "amount_cents": 3900,
        "stripe_price_id": STRIPE_PRICE_ID_PERSONAL,
        "commercial": False,
    },
    "studio": {
        "label": "knob.monster+ Studio",
        "price_display": "$399",
        "amount_cents": 39900,
        "stripe_price_id": STRIPE_PRICE_ID_STUDIO,
        "commercial": True,
    },
}

def normalize_plan(plan: str) -> str:
    if not plan:
        return "free"
    if plan == "free":
        return "free"
    if plan in ("lifetime", "personal"):
        return "personal"
    if plan == "studio":
        return "studio"
    return "personal"

def user_has_premium(user: dict) -> bool:
    return bool(user) and user.get("tier") == "premium"

def get_valid_stripe_customer_id(user: dict) -> str | None:
    customer_id = user.get("stripe_customer_id")
    if not customer_id or customer_id == "mock_customer_id":
        return None
    if not str(customer_id).startswith("cus_"):
        return None
    if not STRIPE_SECRET_KEY:
        return customer_id
    try:
        stripe.Customer.retrieve(customer_id)
        return customer_id
    except stripe.error.StripeError:
        logger.warning("Ignoring stale Stripe customer id for %s", user.get("email"))
        return None

def checkout_adaptive_pricing_for_currency(currency: str) -> dict:
    """Stripe adaptive pricing only when checkout currency is USD (default)."""
    return {"adaptive_pricing": {"enabled": currency.lower() == "usd"}}


def build_pack_checkout_kwargs(user: dict, pack_id: str, pack: dict) -> dict:
    """Match Personal one-time checkout — no customer, no payment_intent_data extras."""
    line_items = build_pack_checkout_line_items(pack_id, pack)
    pack_currency = "usd"
    if line_items and line_items[0].get("price_data"):
        pack_currency = line_items[0]["price_data"].get("currency", "usd")
    return {
        "line_items": line_items,
        "mode": "payment",
        "allow_promotion_codes": False,
        "success_url": BASE_URL + f"/dashboard?payment=pack_success&pack_id={pack_id}",
        "cancel_url": BASE_URL + "/shop?payment=pack_cancel",
        "metadata": {
            "purchase_type": "sound_pack",
            "pack_id": pack_id,
            "user_email": user["email"],
            "pack_name": pack["name"],
        },
        "customer_email": user["email"],
        **checkout_adaptive_pricing_for_currency(pack_currency),
    }

def get_pack_stripe_price_id(pack_id: str) -> str | None:
    env_key = PACK_STRIPE_PRICE_ENV_KEYS.get(pack_id)
    if env_key:
        specific = os.environ.get(env_key, "").strip()
        if specific.startswith("price_"):
            return specific
    shared = STRIPE_PRICE_ID_SOUND_PACK.strip()
    if shared.startswith("price_"):
        return shared
    return None

def build_pack_checkout_line_items(pack_id: str, pack: dict) -> list[dict]:
    """Inline price_data avoids catalog price adaptive-pricing issues on hosted Checkout."""
    use_catalog = os.environ.get("STRIPE_PACK_USE_CATALOG_PRICE", "").strip().lower() in ("1", "true", "yes")
    price_id = get_pack_stripe_price_id(pack_id) if use_catalog else None
    if price_id:
        return [{"price": price_id, "quantity": 1}]
    return [
        {
            "price_data": {
                "currency": "usd",
                "unit_amount": pack["price_cents"],
                "product_data": {
                    "name": pack["name"][:250],
                    "description": (pack.get("description") or pack["name"])[:500],
                },
            },
            "quantity": 1,
        }
    ]

def create_pack_checkout_session(user: dict, pack_id: str, pack: dict):
    return stripe.checkout.Session.create(**build_pack_checkout_kwargs(user, pack_id, pack))

def get_plan_price_id(plan: str, country_code: str | None = None) -> str:
    normalized = normalize_plan(plan)
    region = get_pricing_region(country_code)
    if region in REGIONAL_PRICE_IDS:
        personal_id, studio_id = REGIONAL_PRICE_IDS[region]
        return studio_id if normalized == "studio" else personal_id
    if normalized == "studio":
        return STRIPE_PRICE_ID_STUDIO or ""
    return PLAN_CATALOG[normalized]["stripe_price_id"]


def format_plan_price_display(regional: dict, plan: str) -> str:
    amount = regional["personal_amount"] if plan == "personal" else regional["studio_amount"]
    symbol = regional["symbol"]
    if regional["region"] == "usd":
        return f"{symbol}{amount}"
    if regional["region"] == "chf":
        return f"Fr. {amount}"
    return f"{symbol}{amount} {regional['currency']}"


def get_plan_catalog(country_code: str | None = None) -> dict:
    regional = get_regional_pricing(country_code)
    return {
        "personal": {
            "label": "Personal",
            "price_display": format_plan_price_display(regional, "personal"),
            "amount_cents": int(regional["personal_amount"]) * 100,
            "stripe_price_id": get_plan_price_id("personal", country_code),
            "commercial": False,
        },
        "studio": {
            "label": "knob.monster+ Studio",
            "price_display": format_plan_price_display(regional, "studio"),
            "amount_cents": int(regional["studio_amount"]) * 100,
            "stripe_price_id": get_plan_price_id("studio", country_code),
            "commercial": True,
        },
    }


def signup_template_context(request: Request, **kwargs) -> dict:
    country_code = get_request_country_code(request)
    return {
        "consumer_email_domains": sorted(CONSUMER_EMAIL_DOMAINS),
        "plan_catalog": get_plan_catalog(country_code),
        "pricing": enrich_regional_pricing(country_code),
        **kwargs,
    }


def render_signup(request: Request, **kwargs):
    return render_template("signup.html", request, signup_template_context(request, **kwargs))


def build_plan_checkout_line_items(plan: str, country_code: str | None) -> list[dict]:
    """Inline price_data avoids catalog/adaptive-pricing hosted Checkout failures."""
    normalized = normalize_plan(plan)
    use_catalog = os.environ.get("STRIPE_PLAN_USE_CATALOG_PRICE", "").strip().lower() in ("1", "true", "yes")
    if use_catalog:
        return [{"price": get_plan_price_id(normalized, country_code), "quantity": 1}]

    regional = get_regional_pricing(country_code)
    currency = regional["currency"].lower()
    if normalized == "studio":
        unit_amount = int(regional["studio_amount"]) * 100
        name = "knob.monster+ Studio (lifetime)"
        description = "Commercial use, one location. Lifetime license."
    else:
        unit_amount = int(regional["personal_amount"]) * 100
        name = "knob.monster+ Personal (lifetime)"
        description = "Non-commercial lifetime license."

    return [
        {
            "price_data": {
                "currency": currency,
                "unit_amount": unit_amount,
                "product_data": {
                    "name": name[:250],
                    "description": description[:500],
                },
            },
            "quantity": 1,
        }
    ]

# Email (Resend) — HTTP API for drips; SMTP for newsletter bulk
RESEND_API_KEY = settings.RESEND_API_KEY
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASSWORD = settings.SMTP_PASSWORD
SMTP_FROM = settings.SMTP_FROM
CRON_SECRET = settings.CRON_SECRET or ""


def get_resend_api_key() -> str:
    return RESEND_API_KEY or ""


def send_email_via_resend(
    to: str,
    subject: str,
    body: str,
    *,
    html: str | None = None,
    reply_to: str | None = None,
    list_unsubscribe: str | None = None,
) -> tuple[bool, str | None]:
    """Send one email via Resend HTTP API. Returns (ok, error_detail)."""
    import json
    import urllib.error
    import urllib.request

    api_key = get_resend_api_key()
    if not api_key:
        return False, "missing api key"

    payload: dict = {
        "from": SMTP_FROM,
        "to": [to],
        "subject": subject,
    }
    if html:
        payload["html"] = html
        if body:
            payload["text"] = body
    else:
        payload["text"] = body

    if reply_to:
        payload["reply_to"] = [reply_to]
    if list_unsubscribe:
        payload["headers"] = {"List-Unsubscribe": f"<{list_unsubscribe}>"}

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "knob.monster/1.0 (resend-api)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True, None
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        error = f"HTTP {err.code}: {detail}"
        logger.error(f"resend api failed for {to}: {error}")
        return False, error
    except Exception as err:
        error = str(err)
        logger.error(f"resend api failed for {to}: {error}")
        return False, error


def assert_cron_authorized(request: Request) -> None:
    """GitHub Actions cron — bearer CRON_SECRET only."""
    auth = request.headers.get("authorization", "")
    if CRON_SECRET and auth == f"Bearer {CRON_SECRET}":
        return
    if os.environ.get("VERCEL") == "1":
        raise HTTPException(status_code=401, detail="Unauthorized cron trigger")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    database.init_db()

# Secure Cookie Session signing key
SESSION_SECRET_KEY = settings.SESSION_SECRET_KEY
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
        "title": "Yamaha DX7 Backup & SysEx Librarian | Cloud Patch Manager",
        "description": "Browser-native Yamaha DX7 backup and SysEx librarian. Back up DX7 patches without installing software — Web MIDI cloud backup in Chrome, Edge, and Opera.",
        "keywords": "yamaha dx7 backup, dx7 backup, backup dx7 patches without software, sysex librarian, yamaha dx7 sysex, dx7 patch manager, cloud backup for synthesizers",
        "synth_name": "Yamaha DX7",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha DX7.</span>",
        "hero_subtitle": "The ultimate Yamaha DX7 online librarian. Back up, search, and recall Yamaha DX7 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
,
        "docs": {"title": "How to Turn Off Memory Protect on the Yamaha DX7", "content": "<p class=\"text-zinc-400 mb-4 text-sm md:text-base\">The Yamaha DX7 requires you to explicitly disable internal memory protection and enable SysEx data reception before you can back up or restore patches.</p>\n<ol class=\"list-decimal list-inside space-y-3 text-zinc-300 text-sm md:text-base font-medium\">\n    <li>Press the <strong class=\"text-white\">FUNCTION</strong> button on the front panel.</li>\n    <li>Press button <strong class=\"text-white\">8</strong> (labeled MEMORY PROTECT INTERNAL).</li>\n    <li>The LCD screen will display <code>MEMORY PROTECT INTERNAL: ON</code>.</li>\n    <li>Press the <strong class=\"text-white\">-1/NO</strong> button to change it to <code>OFF</code>.</li>\n    <li>Press button <strong class=\"text-white\">8</strong> again to access the SYS INFO screen.</li>\n    <li>Ensure the screen says <code>SYS INFO: AVAIL</code>. If it says <code>UNAVAIL</code>, press <strong class=\"text-white\">+1/YES</strong> to toggle it.</li>\n</ol>\n<p class=\"text-zinc-400 mt-5 text-sm md:text-base\">Your DX7 is now ready to send and receive SysEx dumps.</p>"}    },
    "juno-106": {
        "title": "Roland Juno-106 Patches & SysEx Backup | Cloud Librarian",
        "description": "Save and back up Roland Juno-106 patches and presets in the cloud. Browser SysEx librarian for Juno-106 — no drivers, vintage synth backup via Web MIDI.",
        "keywords": "juno-106 patches, roland juno 106 backup, how to save juno-106 presets, juno 106 sysex librarian, vintage synth backup, cloud backup for synthesizers",
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
    country_code = get_request_country_code(request)
    client_ip, is_private = resolve_client_ip(request)
    geo = lookup_geo_country(client_ip, is_private)
    pricing_title = pricing_geo_titles.build_pricing_title(country_code, geo.get("country_name"))
    return render_template(
        "landing.html",
        request,
        {
            "user": user,
            "remaining_slots": remaining_slots,
            "total_patches": total_patches,
            "pricing": enrich_regional_pricing(country_code),
            "pricing_title_html": pricing_title["html"],
            "pricing_title_fallback": pricing_geo_titles.DEFAULT_PRICING_TITLE,
            "eur_pricing_enabled": eur_pricing_enabled(),
            "gbp_pricing_enabled": gbp_pricing_enabled(),
            "cad_pricing_enabled": cad_pricing_enabled(),
            "aud_pricing_enabled": aud_pricing_enabled(),
            "chf_pricing_enabled": chf_pricing_enabled(),
            "eu_country_codes": sorted(EU_EUR_COUNTRY_CODES),
            "gb_country_codes": sorted(GB_GBP_COUNTRY_CODES),
            "ca_country_codes": sorted(CA_CAD_COUNTRY_CODES),
            "au_country_codes": sorted(AU_AUD_COUNTRY_CODES),
            "ch_country_codes": sorted(CH_CHF_COUNTRY_CODES),
            "faq_suggestions": faq_knowledge.FAQ_SUGGESTIONS,
        },
    )


@app.post("/api/faq/ask")
async def faq_ask(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Question must be 500 characters or fewer.")

    result = answer_faq_question(question)
    return result

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

@app.get("/audit/midiox", response_class=HTMLResponse)
async def midiox_ssl_audit(request: Request):
    user = get_current_user(request)
    return render_template("midiox_ssl_audit.html", request, {"user": user})

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
    packs = shop_packs.packs_for_template()
    owned_pack_ids = set()
    if user:
        owned_pack_ids = {
            pack["id"]
            for pack in shop_packs.list_shop_packs()
            if shop_packs.user_owns_pack(user["id"], pack["id"])
        }
    return render_template("shop.html", request, {
        "user": user,
        "packs": packs,
        "owned_pack_ids": owned_pack_ids,
        "checkout_error": request.query_params.get("checkout_error"),
        "payment_status": request.query_params.get("payment"),
    })

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

@app.get("/vintage-synth-cloud-backup", response_class=HTMLResponse)
async def guide_cloud_backup_page(request: Request):
    user = get_current_user(request)
    return render_template("guide_cloud_backup.html", request, {"user": user})

@app.get("/research/2026-vintage-synth-owner-survey", response_class=HTMLResponse)
async def research_survey_2026_page(request: Request):
    user = get_current_user(request)
    return render_template(
        "research_survey_2026.html",
        request,
        {"user": user, "survey": research_survey_2026.SURVEY_2026},
    )

@app.get("/research/2026-vintage-synth-owner-survey/data.json")
async def research_survey_2026_json():
    return JSONResponse(
        content=research_survey_2026.public_json(),
        headers={"Cache-Control": "public, max-age=3600"},
    )

@app.get("/research/2026-browser-sysex-vault-launch-lessons", response_class=HTMLResponse)
async def research_lessons_launch_2026_page(request: Request):
    user = get_current_user(request)
    return render_template(
        "research_lessons_launch_2026.html",
        request,
        {"user": user, "lessons": research_lessons_launch_2026.LESSONS_LAUNCH_2026},
    )

@app.get("/research/2026-browser-sysex-vault-launch-lessons/data.json")
async def research_lessons_launch_2026_json():
    return JSONResponse(
        content=research_lessons_launch_2026.public_json(),
        headers={"Cache-Control": "public, max-age=3600"},
    )

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
    client_ip, is_private = resolve_client_ip(request)
    geo = lookup_geo_country(client_ip, is_private)
    country_code = get_request_country_code(request)
    pricing = get_regional_pricing(country_code)
    pricing_title = pricing_geo_titles.build_pricing_title(country_code, geo.get("country_name"))
    return {
        **geo,
        "country": country_code,
        "pricing_region": pricing["region"],
        "pricing_title": pricing_title["text"],
        "pricing_title_html": pricing_title["html"],
        "eur_pricing_enabled": eur_pricing_enabled(),
        "gbp_pricing_enabled": gbp_pricing_enabled(),
        "cad_pricing_enabled": cad_pricing_enabled(),
        "aud_pricing_enabled": aud_pricing_enabled(),
        "chf_pricing_enabled": chf_pricing_enabled(),
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
    next_url = request.query_params.get("next")
    if get_current_user(request):
        return RedirectResponse(url=safe_next_url(next_url))
    return render_template("login.html", request, {"error": error, "next": next_url})

@app.post("/login")
async def do_login(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form(None)):
    user = database.get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        trigger_alert(
            "login_failed",
            f"Failed login attempt for user `{email}`.",
            {"email": email, "reason": "invalid_credentials"},
            distinct_id=email or "anonymous"
        )
        return render_template("login.html", request, {"error": "Invalid email or password", "next": next})
    
    response = RedirectResponse(url=safe_next_url(next), status_code=303)
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
async def signup_page(request: Request, error: str = None, plan: str = None):
    if get_current_user(request):
        return RedirectResponse(url="/dashboard")
    plan = normalize_plan(plan)
    return render_signup(request, error=error, plan=plan)

@app.post("/signup")
async def do_signup(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    plan: str = Form("free"),
    license_ack: str = Form(None),
):
    email_clean = email.lower().strip()
    requested_plan = normalize_plan(plan)
    plan = resolve_plan_for_email(requested_plan, email_clean)
    plan_upgraded_for_email = plan != requested_plan

    if not EMAIL_REGEX.match(email_clean):
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: invalid email format",
            {"email": email, "reason": "invalid_email_format"},
            distinct_id="anonymous"
        )
        return render_signup(
            request,
            error="Invalid email address format",
            plan=plan,
        )

    if password != confirm_password:
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: passwords do not match",
            {"email": email, "reason": "password_mismatch"},
            distinct_id="anonymous"
        )
        return render_signup(request, error="Passwords do not match", plan=plan)
    
    if len(password) < 8:
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: weak password",
            {"email": email, "reason": "weak_password"},
            distinct_id="anonymous"
        )
        return render_signup(request, error="Password must be at least 8 characters long", plan=plan)
    
    if plan == "personal" and not license_ack:
        return render_signup(
            request,
            error="Please confirm personal, non-commercial use for the Personal plan.",
            plan=plan,
        )
    
    user = database.get_user_by_email(email)
    if user:
        trigger_alert(
            "user_signup_failed",
            f"Sign up failed for `{email}`: email already registered",
            {"email": email, "reason": "email_registered"},
            distinct_id=email
        )
        return render_signup(request, error="Email is already registered", plan=plan)
    
    try:
        database.create_user(email_clean, hash_password(password))
        logger.info(f"User registered: {email_clean}", extra={"email": email_clean, "plan": plan, "event_type": "signup"})
        trigger_alert(
            "user_signup",
            f"New user registered: `{email_clean}` with plan `{plan}`."
            + (" (auto-upgraded from Personal — business email domain)" if plan_upgraded_for_email else ""),
            {"email": email_clean, "plan": plan, "plan_upgraded_for_email": plan_upgraded_for_email},
            distinct_id=email_clean
        )
        background_tasks.add_task(send_welcome_email_task, email_clean)
    except Exception as e:
        trigger_alert(
            "user_signup_failed",
            f"Account registration failed for `{email}`: {str(e)}",
            {"email": email, "plan": plan, "error": str(e)},
            distinct_id=email or "anonymous"
        )
        return render_signup(request, error="Account registration failed.", plan=plan)

    # Check if this email paid before registering — auto-upgrade instantly
    pending = database.consume_pending_premium(email)
    if pending:
        pending_plan = normalize_plan(pending.get("plan") or "personal")
        database.update_user_tier(email, "premium", pending.get("stripe_customer_id"), plan=pending_plan)
        logger.info(f"Pending premium applied on registration: {email}", extra={"email": email, "event_type": "pending_premium_applied"})
        trigger_alert(
            "pending_premium_applied",
            f"Pending premium applied for `{email}` upon registration.",
            {"email": email, "customer_id": pending.get("stripe_customer_id")},
            distinct_id=email
        )
        response = RedirectResponse(url="/dashboard?payment=success", status_code=303)
    else:
        welcome_url = "/dashboard?welcome=1"
        if plan_upgraded_for_email:
            welcome_url += "&upgraded=business_email"
        response = RedirectResponse(url=welcome_url, status_code=303)

    response.set_cookie(
        key="session_user",
        value=sign_session_cookie(email_clean),
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
    context = {"banks": banks, "user": user, "pricing": enrich_regional_pricing(get_request_country_code(request))}
    context.update(posthog_support_context(user, enable_conversations=True))
    return render_template("index.html", request, context)

@app.get("/banks", response_class=HTMLResponse)
async def get_banks(request: Request):
    user = get_current_user(request)
    if not user:
        if "hx-request" in request.headers:
            return HTMLResponse(headers={"HX-Redirect": "/login"})
        return RedirectResponse(url="/login")
        
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.get("/banks/export-all")
async def export_all_banks(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    if user["tier"] != "premium":
        return RedirectResponse(url="/checkout")

    banks = database.get_all_banks(user["id"])
    if not banks:
        raise HTTPException(status_code=404, detail="No banks to export")

    corrupt: list[str] = []
    entries: list[tuple[dict, bytes]] = []
    for bank in banks:
        try:
            sysex_bytes = bytes.fromhex(bank["sysex_hex"])
        except ValueError:
            corrupt.append(bank["name"])
            continue
        entries.append((bank, sysex_bytes))

    if corrupt:
        raise HTTPException(
            status_code=500,
            detail=f"Vault export aborted: corrupted data in {', '.join(corrupt)}"
        )
    if not entries:
        raise HTTPException(status_code=404, detail="No banks to export")

    buf = io.BytesIO()
    used_names: dict[str, int] = {}
    manifest_lines = ["# knob.monster vault export", f"# {len(entries)} soundbank(s)", ""]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for bank, sysex_bytes in entries:
            base = re.sub(r"[^\w\-]+", "_", bank["name"].lower()).strip("_") or "bank"
            count = used_names.get(base, 0)
            used_names[base] = count + 1
            filename = f"{base}.syx" if count == 0 else f"{base}_{count}.syx"
            archive.writestr(filename, sysex_bytes)
            manifest_lines.append(f"{filename}\t{bank['name']}\t{bank['synth_model']}\t{len(sysex_bytes)} bytes")

        archive.writestr("manifest.txt", "\n".join(manifest_lines) + "\n")

    buf.seek(0)

    trigger_alert(
        "vault_exported",
        f"Full vault export ({len(entries)} banks) by user `{user['email']}`.",
        {"email": user["email"], "bank_count": len(entries)},
        distinct_id=user["email"]
    )

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="knob_monster_vault.zip"'}
    )

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

    if user.get("tier") != "premium":
        if bank.get("patches"):
            for i, patch in enumerate(bank["patches"]):
                patch["name"] = f"LOCKED {i+1} (PRO)"
        else:
            bank["patches"] = [{"name": "LOCKED (PRO)", "index": 0}]

    template = "patch_list_mobile.html" if request.query_params.get("mobile") == "1" else "patch_list.html"
    return render_template(template, request, {"bank": bank, "user": user})

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
        elif synth_model == "Sequential Prophet":
            patch_names = parser.parse_prophet_sysex(sysex_bytes)
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
        elif synth_model == "Sequential Prophet":
            patch_names = parser.parse_prophet_sysex(sysex_bytes)
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

@app.get("/checkout-pack/{pack_id}")
async def checkout_pack(request: Request, pack_id: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url=f"/login?next=/checkout-pack/{pack_id}")

    pack = shop_packs.get_shop_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
        
    if shop_packs.user_owns_pack(user["id"], pack_id):
        return RedirectResponse(url="/dashboard?payment=pack_owned", status_code=303)

    if not STRIPE_SECRET_KEY:
        bank_id = shop_packs.fulfill_sound_pack(user["email"], pack_id)
        if bank_id:
            trigger_alert(
                "marketplace_pack_purchased",
                f"Sound pack `{pack['name']}` fulfilled (mock) for `{user['email']}`.",
                {"email": user["email"], "pack_id": pack_id, "pack_name": pack["name"], "bank_id": bank_id},
                distinct_id=user["email"],
            )
        return RedirectResponse(url="/dashboard?payment=pack_success", status_code=303)

    try:
        checkout_session = create_pack_checkout_session(user, pack_id, pack)
        if not checkout_session.url:
            raise RuntimeError("Stripe returned a checkout session without a redirect URL")
        adaptive = getattr(checkout_session, "adaptive_pricing", None) or {}
        trigger_alert(
            "stripe_pack_checkout_initiated",
            f"Sound pack checkout started for `{user['email']}` — `{pack['name']}`.",
            {
                "email": user["email"],
                "pack_id": pack_id,
                "pack_name": pack["name"],
                "checkout_session_id": checkout_session.id,
                "stripe_price_id": get_pack_stripe_price_id(pack_id),
                "inline_price": os.environ.get("STRIPE_PACK_USE_CATALOG_PRICE", "").strip().lower() not in ("1", "true", "yes"),
                "adaptive_pricing": adaptive.get("enabled") if isinstance(adaptive, dict) else getattr(adaptive, "enabled", None),
            },
            distinct_id=user["email"],
        )
        return RedirectResponse(url=checkout_session.url, status_code=303)
    except Exception as e:
        logger.error(f"Stripe pack checkout failed: {e}", extra={"pack_id": pack_id, "email": user["email"]})
        trigger_alert(
            "stripe_pack_checkout_failed",
            f"Sound pack checkout failed for `{user['email']}` / `{pack_id}`: {e}",
            {"email": user["email"], "pack_id": pack_id, "error": str(e)},
            distinct_id=user["email"],
        )
        return RedirectResponse(
            url="/shop?checkout_error=stripe",
            status_code=303,
        )

# --- Stripe Monetization Endpoints ---
@app.get("/checkout")
async def create_checkout_session(request: Request, plan: str = "personal"):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
    # If Stripe keys are missing, run in sandbox developer mock-mode
    if not STRIPE_SECRET_KEY:
        return RedirectResponse(url=f"/mock-checkout-success?email={user['email']}&plan={normalize_plan(plan)}")
    
    normalized_plan = normalize_plan(plan)
    if not user_has_premium(user):
        checkout_plan = resolve_plan_for_email(normalized_plan, user["email"])
        if checkout_plan != normalized_plan:
            return RedirectResponse(
                url=f"/checkout?plan=studio&upgraded=business_email",
                status_code=303,
            )
        normalized_plan = checkout_plan
    country_code = get_request_country_code(request)
    if user_has_premium(user):
        current_plan = normalize_plan(user.get("plan") or "personal")
        if normalized_plan == current_plan:
            return RedirectResponse(url="/dashboard?payment=already_active")
        if normalized_plan == "personal" and current_plan == "studio":
            return RedirectResponse(url="/dashboard?payment=already_active")

    if normalized_plan in ("personal", "studio"):
        checkout_mode = "payment"
    elif plan == "yearly":
        price_id = STRIPE_PRICE_ID_YEARLY
        checkout_mode = "subscription"
        normalized_plan = "yearly"
    else:
        price_id = STRIPE_PRICE_ID_MONTHLY
        checkout_mode = "subscription"
        normalized_plan = "monthly"
    
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
        if checkout_mode == "payment":
            line_items = build_plan_checkout_line_items(normalized_plan, country_code)
        else:
            line_items = [{"price": price_id, "quantity": 1}]

        pricing_region = get_regional_pricing(country_code)
        checkout_currency = pricing_region["currency"] if checkout_mode == "payment" else "usd"

        checkout_kwargs = {
            "line_items": line_items,
            "mode": checkout_mode,
            "allow_promotion_codes": allow_promo,
            **checkout_adaptive_pricing_for_currency(checkout_currency),
            "success_url": BASE_URL + "/dashboard?payment=success",
            "cancel_url": BASE_URL + "/dashboard?payment=cancel",
            "metadata": {
                "user_email": user["email"],
                "plan": normalized_plan,
                "pricing_region": pricing_region["region"],
            },
        }

        if normalized_plan == "studio" and checkout_mode == "payment":
            studio_checkout_extras = {
                "invoice_creation": {
                    "enabled": True,
                    "invoice_data": {
                        "description": "knob.monster+ Studio lifetime license (commercial use, one location).",
                        "metadata": {"plan": "studio"},
                    },
                },
                "tax_id_collection": {"enabled": True},
                "billing_address_collection": "required",
            }
            stripe_customer_id = get_valid_stripe_customer_id(user)
            if stripe_customer_id:
                studio_checkout_extras["customer"] = stripe_customer_id
                studio_checkout_extras["customer_update"] = {"name": "auto", "address": "auto"}
            else:
                studio_checkout_extras["customer_email"] = user["email"]
                studio_checkout_extras["customer_creation"] = "always"
            checkout_kwargs.update(studio_checkout_extras)
        else:
            checkout_kwargs["customer_email"] = user["email"]

        checkout_session = stripe.checkout.Session.create(**checkout_kwargs)
        trigger_alert(
            "stripe_checkout_initiated",
            f"Stripe checkout initiated by `{user['email']}` for plan `{normalized_plan}`.",
            {
                "email": user["email"],
                "plan": normalized_plan,
                "checkout_session_id": checkout_session.id,
                "pricing_region": get_regional_pricing(country_code)["region"],
                "inline_price": checkout_mode == "payment",
            },
            distinct_id=user["email"]
        )
        return RedirectResponse(url=checkout_session.url, status_code=303)
    except Exception as e:
        logger.error(f"Stripe checkout failed for {user['email']}: {e}")
        trigger_alert(
            "stripe_checkout_failed",
            f"Stripe checkout session creation failed for `{user['email']}`: {str(e)}",
            {"email": user["email"], "plan": plan, "error": str(e)},
            distinct_id=user["email"]
        )
        return RedirectResponse(
            url="/dashboard?checkout_error=stripe",
            status_code=303,
        )

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
        
    stripe_customer_id = get_valid_stripe_customer_id(user)
    if not stripe_customer_id:
        return RedirectResponse(url="/checkout")
        
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
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
async def mock_checkout_success(email: str, plan: str = "personal"):
    # Protect against production payment bypass
    if os.environ.get("VERCEL") or (STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith("sk_test_")):
        raise HTTPException(status_code=403, detail="Mock checkout is disabled in production")
    normalized_plan = normalize_plan(plan)
    database.update_user_tier(email, "premium", "mock_customer_id", plan=normalized_plan)
    return RedirectResponse(url="/dashboard?payment=success")

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
        metadata = getattr(session, 'metadata', None) or {}
        if not isinstance(metadata, dict):
            metadata = dict(metadata) if metadata else {}
        if metadata.get("purchase_type") == "sound_pack":
            pack_id = metadata.get("pack_id")
            if customer_email and pack_id:
                pack = shop_packs.get_shop_pack(pack_id)
                bank_id = shop_packs.fulfill_sound_pack(customer_email, pack_id)
                if bank_id and pack:
                    logger.info(
                        f"Sound pack delivered via Stripe: {customer_email} / {pack_id}",
                        extra={"email": customer_email, "pack_id": pack_id, "bank_id": bank_id, "event_type": "pack_purchased"},
                    )
                    trigger_alert(
                        "marketplace_pack_purchased",
                        f"Sound pack `{pack['name']}` purchased via Stripe for `{customer_email}`.",
                        {"email": customer_email, "pack_id": pack_id, "pack_name": pack["name"], "bank_id": bank_id},
                        distinct_id=customer_email,
                    )
        elif metadata.get("plan"):
            purchased_plan = normalize_plan(metadata.get("plan"))
            if customer_email:
                existing_user = database.get_user_by_email(customer_email)
                if existing_user:
                    database.update_user_tier(customer_email, "premium", customer_id, plan=purchased_plan)
                    logger.info(f"Subscription activated via Stripe: {customer_email}", extra={"email": customer_email, "customer_id": customer_id, "plan": purchased_plan, "event_type": "subscription_activated"})
                    trigger_alert(
                        "subscription_activated",
                        f"Subscription activated via Stripe for `{customer_email}` on plan `{purchased_plan}`.",
                        {"email": customer_email, "customer_id": customer_id, "plan": purchased_plan},
                        distinct_id=customer_email
                    )
                else:
                    # User paid before registering — park it, apply on registration
                    database.upsert_pending_premium(customer_email, customer_id, plan=purchased_plan)
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

def build_sitemap_xml() -> str:
    from datetime import date

    today = date.today().isoformat()
    entries: list[tuple[str, str, str]] = [
        (f"{SITE_BASE}/", "weekly", "1.0"),
        (f"{SITE_BASE}/shop", "weekly", "0.9"),
        (f"{SITE_BASE}/vintage-synth-cloud-backup", "weekly", "1.0"),
        (f"{SITE_BASE}/sysex-librarian-alternatives", "weekly", "0.95"),
        (f"{SITE_BASE}/knob-monster-vs-snoize-sysex-librarian", "weekly", "0.9"),
        (f"{SITE_BASE}/knob-monster-vs-midi-ox", "weekly", "0.9"),
        (f"{SITE_BASE}/audit/midiox", "monthly", "0.85"),
        (f"{SITE_BASE}/resources", "weekly", "0.85"),
        (f"{SITE_BASE}/payment-methods", "monthly", "0.6"),
        (f"{SITE_BASE}/terms", "monthly", "0.5"),
        (f"{SITE_BASE}/privacy", "monthly", "0.5"),
        (f"{SITE_BASE}/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer", "weekly", "0.9"),
        (f"{SITE_BASE}/how-to-backup-yamaha-dx7-presets-sysex-transfer-guide", "weekly", "0.9"),
        (f"{SITE_BASE}/how-to-backup-roland-juno-106-presets-sysex-transfer-guide", "weekly", "0.9"),
        (f"{SITE_BASE}/how-to-backup-korg-m1-presets-sysex-transfer-guide", "weekly", "0.9"),
        (f"{SITE_BASE}/why-your-vintage-synth-battery-is-killing-your-sounds", "weekly", "0.9"),
        (f"{SITE_BASE}/how-to-fix-juno-106-memory-loss-troubleshooting-guide", "weekly", "0.9"),
        (f"{SITE_BASE}/research/2026-vintage-synth-owner-survey", "monthly", "0.85"),
        (f"{SITE_BASE}/research/2026-vintage-synth-owner-survey/data.json", "monthly", "0.8"),
        (f"{SITE_BASE}/research/2026-browser-sysex-vault-launch-lessons", "monthly", "0.85"),
        (f"{SITE_BASE}/research/2026-browser-sysex-vault-launch-lessons/data.json", "monthly", "0.8"),
    ]
    for slug in SEO_DATA.keys():
        entries.append((f"{SITE_BASE}/{slug}", "weekly", "0.9"))
        
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, changefreq, priority in entries:
        xml_lines.extend([
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{today}</lastmod>",
            f"    <changefreq>{changefreq}</changefreq>",
            f"    <priority>{priority}</priority>",
            "  </url>",
        ])
    xml_lines.append("</urlset>")
    return "\n".join(xml_lines)
    
@app.get("/sitemap.xml")
@app.get("/sitemap.xml/")
async def sitemap():
    return Response(content=build_sitemap_xml(), media_type="application/xml")

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
        "- **Lifetime Pricing:** knob.monster+ Personal $39 (non-commercial) or knob.monster+ Studio $399 (commercial, one location). Sound packs from $9 in the Monster Shop.",
        "",
        "## Key Pages",
        "- [Home Page](https://knob.monster/): SysEx librarian, vintage synth cloud backup, pricing, live MIDI demo.",
        "- [Vintage Synth Cloud Backup](https://knob.monster/vintage-synth-cloud-backup): Pillar guide for DX7 backup, Juno-106 patches, cloud backup for synthesizers, MIDI-OX alternative Mac.",
        "- [Monster Shop](https://knob.monster/shop): Curated SysEx sound banks for DX7, Juno-106, and Korg M1.",
        "- [Alternatives Guide](https://knob.monster/sysex-librarian-alternatives): Comparison of web-based SysEx librarians.",
        "- [Snoize Comparison](https://knob.monster/knob-monster-vs-snoize-sysex-librarian): knob.monster vs Snoize SysEx Librarian.",
        "- [MIDI-OX Comparison](https://knob.monster/knob-monster-vs-midi-ox): knob.monster vs Windows MIDI-OX.",
        "- [MIDI-OX TLS Audit](https://knob.monster/audit/midiox): Independent transport-security review of midiox.com.",
        "- [Payment Methods](https://knob.monster/payment-methods): Supported payment options.",
        "",
        "## How-To Guides",
        "- [Yamaha DX7 SysEx Backup](https://knob.monster/how-to-backup-yamaha-dx7-presets-sysex-transfer-guide)",
        "- [Roland Juno-106 SysEx Backup](https://knob.monster/how-to-backup-roland-juno-106-presets-sysex-transfer-guide)",
        "- [Korg M1 SysEx Backup](https://knob.monster/how-to-backup-korg-m1-presets-sysex-transfer-guide)",
        "- [Vintage Synth Battery Guide](https://knob.monster/why-your-vintage-synth-battery-is-killing-your-sounds)",
        "- [Juno-106 Memory Loss Troubleshooting](https://knob.monster/how-to-fix-juno-106-memory-loss-troubleshooting-guide)",
        "- [Web MIDI Engineering Notes](https://knob.monster/how-do-you-keep-web-midi-from-crashing-a-1983-synthesizer)",
        "",
        "## Original Research (2026)",
        "First-party data from knob.monster visitors. Cite: Half Radiation LLC, 2026 Vintage Synth Owner Survey, knob.monster, June 25–July 1, 2026.",
        "",
        "- **Survey page:** https://knob.monster/research/2026-vintage-synth-owner-survey",
        "- **Machine-readable JSON:** https://knob.monster/research/2026-vintage-synth-owner-survey/data.json",
        "- **Sample:** n=61 completed responses (2,417 impressions, 2.57% conversion)",
        "- **Segmentation:** 47.5% gear room (5+ boards), 41.0% bedroom (1–2 synths), 11.5% commercial",
        "- **Top brands** (valid gear lists, n=18): Roland 44%, Korg 39%, Moog 28%",
        "- **Frequently named models:** Juno-60/106, Korg MS-20, Yamaha DX7, Roland D-50",
        "",
        "## Launch Lessons (2026)",
        "First-party founder field log from month one. Cite: Half Radiation LLC, Lessons from Launching a Browser SysEx Vault, knob.monster, June 2026.",
        "",
        "- **Lessons page:** https://knob.monster/research/2026-browser-sysex-vault-launch-lessons",
        "- **Machine-readable JSON:** https://knob.monster/research/2026-browser-sysex-vault-launch-lessons/data.json",
        "- **Survey popup:** 2.57% conversion (61/2,417), 58.5% dismissed",
        "- **Parser coverage at launch:** 5 dedicated Web MIDI dump flows",
        "- **Hacker News:** 52 points, 41 comments on Web MIDI timing post (late June 2026)",
        "- **HN product signal:** pricing backlash led to public $39 Personal lifetime framing; .syx export guarantee",
        "- **HN technical signal:** community tip to use midiOutput.send(data, performance.now() + offset)",
        "- **Key lesson:** distribution and trust outran parser breadth at launch",
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
- **Personal**: $39 one-time lifetime. 1 user, non-commercial use.
- **knob.monster+ Studio**: $399 one-time lifetime. Commercial use at one location. Same features as Personal.
- **Commercial / B2B**: Contact halfradiationllc@gmail.com for bespoke site licenses, white-labeling, and multi-site rollouts.

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

Premium access: knob.monster+ ($39) or knob.monster+ Studio ($399) lifetime plans. Checkout at `/checkout?plan=personal` or `/checkout?plan=studio`. Commercial/B2B via email.

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
        "services": ["checkout"],
        "capabilities": ["stripe_checkout", "one_time_payment"],
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
            "currencies": ["USD", "EUR", "GBP", "CAD", "AUD", "CHF", "BRL", "KRW"],
            "billing_periods": ["lifetime"]
        },
        "endpoints": {
            "checkout": f"{SITE_BASE}/checkout",
            "portal": f"{SITE_BASE}/portal",
            "status": f"{SITE_BASE}/status"
        },
        "pricing": {
            "personal": {"amount": 3900, "currency": "USD", "interval": "one-time"},
            "studio": {"amount": 39900, "currency": "USD", "interval": "one-time", "commercial": True},
            "commercial": {"contact": "halfradiationllc@gmail.com"}
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


@app.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_page(request: Request, token: str = ""):
    email = ""
    error = ""
    if token:
        try:
            email = cookie_signer.unsign(token).decode()
            database.add_to_unsubscribed(email)
            trigger_alert(
                "newsletter_unsubscribed",
                f"User `{email}` has unsubscribed from the newsletter.",
                {"email": email},
                distinct_id=email
            )
        except BadSignature:
            error = "Invalid or expired unsubscribe link."
            logger.warning(f"Invalid unsubscribe token attempt: {token}")
    return render_template("unsubscribe.html", request, {"email": email, "error": error})

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
DRIP_SUBJECT = "your studio vault is locked"
DRIP_BODY_TEMPLATE = """hey there,

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
                    

def send_welcome_email_task(email: str):
    try:
        # Generate the personalized first name
        name_part = email.split('@')[0]
        first_name = re.split(r'[\._-]', name_part)[0]
        first_name_cap = first_name.capitalize() if first_name else "synth head"

        # Generate avatar URL
        hash_val = 5381
        for ch in str(email):
            hash_val = ((hash_val << 5) + hash_val) + ord(ch)
        idx = (abs(hash_val) % 48) + 1
        avatar_url = f"{SITE_BASE}/static/avatars/Simple%20colors/Icon{idx}.png"

        # Render HTML using templates
        template = templates.get_template("email_welcome.html")
        html_content = template.render({
            "first_name": first_name_cap,
            "avatar_url": avatar_url,
        })

        # Plain text fallback body
        plain_body = (
            f"Hi {first_name_cap},\n\n"
            "We believe a good SysEx librarian shouldn’t need a bunch of dusty plugins, local drivers, "
            "or desktop installers to do its job well. knob.monster already comes with the features you "
            "often have to install as add-ons, running securely right inside your web browser.\n\n"
            "Open your vault: https://knob.monster/dashboard\n\n"
            "Keep the analog alive,\n"
            "knob.monster support"
        )

        ok, err = send_email_via_resend(
            to=email,
            subject="welcome to knob.monster",
            body=plain_body,
            html=html_content,
            reply_to="halfradiationllc@gmail.com",
        )
        if ok:
            logger.info(f"Welcome email successfully sent to {email}")
        else:
            logger.error(f"Failed to send welcome email to {email}: {err}")
    except Exception as e:
        logger.error(f"Error in send_welcome_email_task for {email}: {str(e)}")


async def get_drip_eligible_users() -> tuple[list[dict], int, int]:
    """Return (eligible users, skipped_young, pending_total)."""
    if not hasattr(database, "get_pending_drip_users"):
        try:
            import importlib
            importlib.reload(database)
        except Exception as reload_err:
            logger.error(f"failed to reload database module: {reload_err}")

    users = database.get_pending_drip_users()
    eligible: list[dict] = []
    skipped_young = 0
    for u in users:
        created_at = datetime.fromisoformat(u["created_at"])
        elapsed = datetime.now() - created_at
        if elapsed.total_seconds() < 3600:
            skipped_young += 1
            continue
        eligible.append(
            {
                "id": u["id"],
                "email": u["email"],
                "elapsed_seconds": int(elapsed.total_seconds()),
            }
        )
    return eligible, skipped_young, len(users)


@app.get("/api/cron/drip-pending")
async def drip_pending(request: Request):
    """Queue eligible drip recipients — actual send runs on GitHub Actions (Vercel IPs blocked by Cloudflare)."""
    assert_cron_authorized(request)
    eligible, skipped_young, pending_total = await get_drip_eligible_users()
    return {
        "subject": DRIP_SUBJECT,
        "body": DRIP_BODY_TEMPLATE,
        "from": SMTP_FROM,
        "reply_to": "halfradiationllc@gmail.com",
        "users": eligible,
        "skipped_young": skipped_young,
        "pending_total": pending_total,
    }


@app.post("/api/cron/drip-ack")
async def drip_ack(request: Request):
    """Mark drips sent / log failures after GitHub Actions delivers via Resend."""
    assert_cron_authorized(request)
    body = await request.json()
    sent_items = body.get("sent") or []
    failed_items = body.get("failed") or []
    skipped_young = int(body.get("skipped_young") or 0)
    pending_total = int(body.get("pending_total") or 0)

    for item in sent_items:
        database.mark_drip_sent(int(item["id"]))
        trigger_alert(
            "drip_email_sent",
            f"paywall drip sent to `{item['email']}`.",
            {
                "email": item["email"],
                "elapsed_seconds": item.get("elapsed_seconds"),
                "via": "resend-github",
            },
            distinct_id=item["email"],
        )

    last_error = None
    for item in failed_items:
        err = item.get("error") or "unknown"
        last_error = err
        trigger_alert(
            "drip_email_failed",
            f"paywall drip failed for `{item['email']}`: {err}",
            {"email": item["email"], "resend_error": err},
            distinct_id=item["email"],
        )

    summary = {
        "pending": pending_total,
        "sent": len(sent_items),
        "skipped_young": skipped_young,
        "failed": len(failed_items),
        "last_resend_error": last_error,
    }
    trigger_alert(
        "drip_cron_finished",
        (
            f"drip cron: {summary['sent']} sent, {summary['failed']} failed, "
            f"{skipped_young} too new, {pending_total} pending total."
        ),
        summary,
        distinct_id="drip_cron",
    )
    return {"status": "success", **summary}


@app.get("/api/cron/send-drips")
async def trigger_drip_cron(request: Request):
    """Legacy alias — drips send from GitHub Actions (scripts/send_drips.py)."""
    assert_cron_authorized(request)
    eligible, skipped_young, pending_total = await get_drip_eligible_users()
    return {
        "status": "use_github_actions",
        "message": "Run scripts/send_drips.py from the Drip Email Cron workflow.",
        "eligible": len(eligible),
        "skipped_young": skipped_young,
        "pending_total": pending_total,
    }

NEWSLETTER_TOPICS = [
    "why the DX7 is FM hell to program — and the one operator trick that finally clicks",
    "NiCad and lithium backup batteries: leak patterns, smell, and why waiting is the worst plan",
    "roland juno-106 bucket-brigade chorus — why it hisses and why we still love it",
    "sysex bulk dumps failing mid-transfer: buffer size, cable direction, and the 60ms pause trick",
    "the TX81Z Lately Bass preset — how one ROM patch owned 90s dance floors",
    "korg M1 universe preset and the moment PCM samples killed pure analog worship",
    "saving patches to cassette in 1984 — baud rate, alignment, and the screech nobody misses",
    "web MIDI in chrome vs safari: why your synth 'doesn't work' in the wrong browser",
    "jupiter-6 europa firmware vs stock — memory maps and why generic librarians choke",
    "casio CZ nibble-packed tones — why names don't exist and how librarians fake them",
    "MIDI-OX SSL warnings in 2026 — why desktop abandonware is a security footgun",
    "internal battery swap checklist before your next sysex dump (write protect, backup first)",
]

NEWSLETTER_PRODUCT_FACTS = """
PRODUCT FACTS (use only these — do not invent features or pricing):
- knob.monster is a browser SysEx librarian at https://knob.monster (Chrome/Edge, Web MIDI + SysEx).
- Dedicated parsers: Yamaha DX7, Roland Juno-106, Korg M1, Roland Jupiter-6, Casio CZ-101; generic scan for others.
- Lifetime pricing: Personal $39 (non-commercial), Studio $399 (commercial). NOT a monthly subscription.
- Shop sound packs from $9 at https://knob.monster/shop
- Users back up, search, download .syx, and flash banks via Web MIDI.
- Built by Half Radiation LLC. Support: halfradiationllc@gmail.com
"""

NEWSLETTER_FOOTER = """
---
back up your banks (lifetime — no subscription):
https://knob.monster/dashboard

to stop receiving these, unsubscribe instantly:
https://knob.monster/unsubscribe?token={{unsubscribe_token}}
"""

def get_openrouter_config():
    return settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL


def call_openrouter_chat(messages, json_object=False, timeout=30):
    import urllib.request
    import json

    api_key, model = get_openrouter_config()
    if not api_key:
        return None

    payload = {"model": model, "messages": messages}
    if json_object:
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://knob.monster",
            "X-Title": "knob.monster",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            response_data = json.loads(res.read().decode("utf-8"))
            return response_data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {e}")
        return None


def _parse_openrouter_json(text_response):
    import json

    cleaned = (text_response or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) > 2 and lines[-1].startswith("```"):
            cleaned = "\n".join(lines[1:-1]).strip()
        else:
            cleaned = cleaned.strip("`").strip()
    return json.loads(cleaned)


def answer_faq_question(question: str) -> dict:
    matched = faq_knowledge.find_faq_match(question)
    if matched:
        return {
            "answer": matched["answer"],
            "source": "faq",
            "matched_question": matched["question"],
        }

    corpus = faq_knowledge.build_faq_corpus()
    prompt = f"""You are the knob.monster support assistant on the landing page.
Answer the user's question using ONLY the official FAQ knowledge below.
When a FAQ clearly covers the question, reuse that FAQ answer text as closely as possible (light edits for flow are OK).
Do not invent features, pricing, synth support, or policies that are not in the FAQ.
If the FAQ does not cover the question, say you are not sure and suggest emailing halfradiationllc@gmail.com.
Keep answers concise (1-4 sentences). Plain text only, no markdown or HTML.

OFFICIAL FAQ:
{corpus}

User question: {question}

Return JSON: {{"answer": "your response"}}"""

    text_response = call_openrouter_chat([{"role": "user", "content": prompt}], json_object=True)
    if not text_response:
        return {
            "answer": (
                "I could not generate an answer right now. Please try one of the suggested questions, "
                "or email halfradiationllc@gmail.com and we will help."
            ),
            "source": "fallback",
        }

    try:
        parsed = _parse_openrouter_json(text_response)
        answer = (parsed.get("answer") or "").strip()
        if answer:
            return {"answer": answer, "source": "llm"}
    except Exception as json_err:
        logger.error(f"FAQ JSON parsing failed: {json_err}. Raw response:\n{text_response}")

    return {
        "answer": (
            "I could not parse an answer right now. Please try rephrasing your question, "
            "or email halfradiationllc@gmail.com."
        ),
        "source": "fallback",
    }


def _strip_ai_newsletter_footer(body: str) -> str:
    import re
    text = (body or "").strip()
    text = re.sub(r"\n---+\s*\n.*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"\n(to stop receiving|unsubscribe).*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def _validate_newsletter_draft(subject: str, body: str) -> list[str]:
    import re
    issues = []
    subj = (subject or "").strip()
    text = _strip_ai_newsletter_footer(body)
    if len(subj) < 8:
        issues.append("subject too short")
    if len(subj) > 90:
        issues.append("subject too long")
    if len(text) < 180:
        issues.append("body too short")
    if len(text) > 2200:
        issues.append("body too long")
    if re.search(r"<[^>]+>", text):
        issues.append("html not allowed")
    banned = [
        r"\$\d+/month",
        r"monthly subscription",
        r"prophet-5 parser",
        r"matrix-1000 parser",
        r"free tier forever",
        r"chatgpt",
    ]
    combined = f"{subj} {text}".lower()
    for pattern in banned:
        if re.search(pattern, combined):
            issues.append(f"banned phrase: {pattern}")
    return issues


def _finalize_newsletter_draft(subject: str, body: str) -> dict:
    clean_body = _strip_ai_newsletter_footer(body)
    return {
        "subject": (subject or "vintage synth field notes").strip().lower(),
        "body": clean_body + NEWSLETTER_FOOTER,
    }


def generate_newsletter_content_via_gemini() -> dict:
    import random

    fallback_newsletter = _finalize_newsletter_draft(
        "the ticking timebomb inside your 80s synthesizers",
        """hey,

if you own a roland juno-106, korg m1, or yamaha dx7, there is a silent killer on the mainboard: the backup battery.

NiCad packs leak. lithium cells die quietly. either way, when that cell goes flat, your custom patches vanish. sometimes the leak eats copper traces and the board is done.

before you swap the battery or buy another rompler, dump what you have. one sysex bulk save while the machine still boots is the difference between a library and a ghost.

tip: write protect off, known-good midi cable (out → in), chrome open, then request the bulk dump. if bytes stop mid-stream, slow the sender — vintage rom is not a race.""",
    )

    api_key, _model = get_openrouter_config()
    if not api_key:
        logger.warning("OpenRouter API key is not set. Using fallback newsletter.")
        return fallback_newsletter

    selected_topic = random.choice(NEWSLETTER_TOPICS)
    faq_corpus = faq_knowledge.build_faq_corpus()
    logger.info(f"Selected newsletter topic: {selected_topic}")

    prompt = f"""You write the knob.monster email — a field note for vintage synth owners (1983–1995 hardware).

VOICE: lowercase throughout. sound like a repair bench tech who has seen too many leaked batteries and flipped write-protect switches the wrong way. specific > poetic. no corporate hype, no "we're excited to announce", no sign-offs, no team name.

THIS WEEK'S TOPIC (go deep on ONE angle):
{selected_topic}

{NEWSLETTER_PRODUCT_FACTS}

OFFICIAL FAQ (ground truth — do not contradict):
{faq_corpus}

STRUCTURE for "body" (plain text only, no HTML, no markdown):
1) hook — 1–2 sentences, visceral or blunt
2) meat — 3–5 sentences with at least one concrete hardware detail (part name, symptom, workflow, or failure mode)
3) tip — 1–2 sentences the reader can act on this week (backup, cable check, battery, sysex, browser)

RULES:
- do NOT include any URLs, links, CTAs, or unsubscribe text — we append those
- do NOT mention features or synths not listed in PRODUCT FACTS
- do NOT claim monthly pricing or subscription billing
- max ~170 words for the body
- start with "hey," or jump straight into the hook

Return JSON only: {{"subject": "...", "body": "..."}}"""

    for attempt in range(3):
        try:
            text_response = call_openrouter_chat(
                [{"role": "user", "content": prompt}],
                json_object=True,
                timeout=45,
            )
            if not text_response:
                raise RuntimeError("Empty OpenRouter response")
            parsed = _parse_openrouter_json(text_response)
            subject = (parsed.get("subject") or "").strip().lower()
            body = (parsed.get("body") or "").strip()
            issues = _validate_newsletter_draft(subject, body)
            if issues:
                logger.warning(f"Newsletter draft rejected (attempt {attempt + 1}): {issues}")
                prompt += f"\n\nPREVIOUS DRAFT REJECTED: {', '.join(issues)}. Fix and try again."
                continue
            return _finalize_newsletter_draft(subject, body)
        except Exception as e:
            logger.error(f"Newsletter generation attempt {attempt + 1} failed: {e}")

    logger.error("All newsletter generation attempts failed; using fallback.")
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
            finalized = _finalize_newsletter_draft(override_subject, override_body)
            subject = finalized["subject"]
            body = finalized["body"]
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
            unsubscribe_token = cookie_signer.sign(email.encode()).decode()
            personal_body = body.replace("{{unsubscribe_token}}", unsubscribe_token)
            
            sent_via_smtp = False
            if server:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = smtp_from
                    msg['To'] = email
                    msg['Subject'] = subject
                    msg['Reply-To'] = "halfradiationllc@gmail.com"
                    msg['List-Unsubscribe'] = f"<https://knob.monster/unsubscribe?token={unsubscribe_token}>"
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

@app.get("/api/cron/newsletter-pending")
async def newsletter_pending(request: Request):
    """Queue newsletter recipients + content — send runs on GitHub Actions."""
    assert_cron_authorized(request)

    from datetime import date
    if date.today().isocalendar().week % 2 == 1:
        return {"status": "skipped", "reason": "biweekly off-week"}

    recipients = database.get_all_newsletter_recipients()
    if not recipients:
        return {"status": "empty", "recipient_count": 0}

    content = generate_newsletter_content_via_gemini()
    subject = content["subject"]
    body_template = content["body"]

    trigger_alert(
        "newsletter_broadcast_started",
        f"starting newsletter broadcast to {len(recipients)} recipients.\nsubject: `{subject}`",
        {"recipient_count": len(recipients), "subject": subject},
        distinct_id="newsletter_cron",
    )

    prepared = []
    for email in recipients:
        unsubscribe_token = cookie_signer.sign(email.encode()).decode()
        prepared.append(
            {
                "email": email,
                "body": body_template.replace("{{unsubscribe_token}}", unsubscribe_token),
                "list_unsubscribe": f"https://knob.monster/unsubscribe?token={unsubscribe_token}",
            }
        )

    return {
        "status": "ready",
        "subject": subject,
        "from": SMTP_FROM,
        "reply_to": "halfradiationllc@gmail.com",
        "recipients": prepared,
        "recipient_count": len(prepared),
    }


@app.post("/api/cron/newsletter-ack")
async def newsletter_ack(request: Request):
    assert_cron_authorized(request)
    body = await request.json()
    sent_count = int(body.get("sent_count") or 0)
    failed_count = int(body.get("failed_count") or 0)
    subject = body.get("subject") or ""
    failed_samples = body.get("failed") or []

    trigger_alert(
        "newsletter_broadcast_finished",
        f"finished newsletter broadcast. sent: {sent_count}, failed: {failed_count}.",
        {"sent_count": sent_count, "failed_count": failed_count, "subject": subject},
        distinct_id="newsletter_cron",
    )
    for item in failed_samples[:3]:
        trigger_alert(
            "newsletter_send_failed",
            f"newsletter failed for `{item.get('email')}`: {item.get('error')}",
            item,
            distinct_id=item.get("email", "newsletter_cron"),
        )

    return {
        "status": "success",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "subject": subject,
    }


@app.get("/api/cron/newsletter")
async def trigger_newsletter_cron(request: Request):
    """Legacy alias — newsletter sends from GitHub Actions (scripts/send_newsletter.py)."""
    assert_cron_authorized(request)

    from datetime import date
    if date.today().isocalendar().week % 2 == 1:
        return {"status": "skipped", "reason": "biweekly off-week"}

    recipients = database.get_all_newsletter_recipients()
    return {
        "status": "use_github_actions",
        "message": "Run scripts/send_newsletter.py from the Newsletter Cron workflow.",
        "recipient_count": len(recipients),
    }

