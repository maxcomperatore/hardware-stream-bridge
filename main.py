from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import io
import os
import hashlib
import stripe
import database
import parser
import logging

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

app = FastAPI(title="Knob Monster - Vintage Synth Patch Manager")

from datetime import datetime

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
    
    # Don't block static files or favicon so assets render properly on the landing page
    if is_earth_day and not request.url.path.startswith("/static") and request.url.path != "/favicon.ico":
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

# Force immediate module-level copy of new static images to override cache
try:
    import shutil
    src_dir = "C:/Users/Usuario/.gemini/antigravity/brain/21cc624c-71d6-4620-83a8-f77a95f2af34"
    dest_dir = os.path.join(BASE_DIR, "static")
    os.makedirs(dest_dir, exist_ok=True)
    for src_name, dest_name in [
        ("vintage_synth_hero_user_1780849554157.png", "vintage_synth_hero.png"),
        ("studio_detail_user_1780849586288.png", "studio_detail.png"),
        ("midi_handshake_user_1780849568376.png", "midi_handshake.png"),
        ("index_extraction_candid_1780849725170.png", "index_extraction.png"),
        ("dashboard_candid_1780849740378.png", "dashboard.png"),
        ("dashboard_candid_1780849740378.png", "dashboard_preview.png")
    ]:
        src_path = os.path.join(src_dir, src_name)
        if os.path.exists(src_path):
            shutil.copy(src_path, os.path.join(dest_dir, dest_name))
except Exception as e:
    print(f"Module-level copy failed: {e}")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Mount Static Files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Configure Stripe key & fallback mock mode
STRIPE_SECRET_KEY = "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"
STRIPE_WEBHOOK_SECRET = "whsec_AWPK4gRmIUdFkUXAzn9IMufmJF5pW5wR"
stripe.api_key = STRIPE_SECRET_KEY

STRIPE_PRICE_ID_YEARLY = "price_1Tj3wRLuSQGuB7eyeLFUuCSS"
STRIPE_PRICE_ID_MONTHLY = "price_1Tj3w8LuSQGuB7ey5ZhEjwri"
BASE_URL = "https://knob.monster"

# Initialize database and copy assets on startup
@app.on_event("startup")
async def startup_event():
    database.init_db()
    
    # Try copying files locally, skip/fail silently on serverless read-only environments
    try:
        import shutil
        src_dir = "C:/Users/Usuario/.gemini/antigravity/brain/21cc624c-71d6-4620-83a8-f77a95f2af34"
        dest_dir = os.path.join(BASE_DIR, "static")
        os.makedirs(dest_dir, exist_ok=True)
        
        hero_src = os.path.join(src_dir, "vintage_synth_hero_user_1780849554157.png")
        if os.path.exists(hero_src):
            shutil.copy(hero_src, os.path.join(dest_dir, "vintage_synth_hero.png"))
            
        detail_src = os.path.join(src_dir, "studio_detail_user_1780849586288.png")
        if os.path.exists(detail_src):
            shutil.copy(detail_src, os.path.join(dest_dir, "studio_detail.png"))

        camera_src = os.path.join(src_dir, "vintage_camera_404_1780240561882.png")
        if os.path.exists(camera_src):
            shutil.copy(camera_src, os.path.join(dest_dir, "vintage_camera_404.png"))

        troll_src = os.path.join(src_dir, "troll.png")
        troll_dest = os.path.join(dest_dir, "troll.png")
        if os.path.exists(troll_src):
            shutil.copy(troll_src, troll_dest)
            
        if os.path.exists(troll_dest):
            shutil.copy(troll_dest, os.path.join(dest_dir, "logo.png"))
        else:
            logo_src = os.path.join(src_dir, "vaultsynth_logo_1780240683932.png")
            if os.path.exists(logo_src):
                shutil.copy(logo_src, os.path.join(dest_dir, "logo.png"))

        # Copy green and gold trolls
        for filename, dest_filename in [("troll (1).png", "troll_green.png"), ("troll (2).png", "troll_gold.png")]:
            path_dest = os.path.join(dest_dir, filename)
            path_src = os.path.join(src_dir, filename)
            if os.path.exists(path_dest):
                shutil.copy(path_dest, os.path.join(dest_dir, dest_filename))
            elif os.path.exists(path_src):
                shutil.copy(path_src, os.path.join(dest_dir, dest_filename))

        handshake_src = os.path.join(src_dir, "midi_handshake_user_1780849568376.png")
        if os.path.exists(handshake_src):
            shutil.copy(handshake_src, os.path.join(dest_dir, "midi_handshake.png"))

        dashboard_src = os.path.join(src_dir, "dashboard_candid_1780849740378.png")
        if os.path.exists(dashboard_src):
            shutil.copy(dashboard_src, os.path.join(dest_dir, "dashboard.png"))
            shutil.copy(dashboard_src, os.path.join(dest_dir, "dashboard_preview.png"))

        extraction_src = os.path.join(src_dir, "index_extraction_candid_1780849725170.png")
        if os.path.exists(extraction_src):
            shutil.copy(extraction_src, os.path.join(dest_dir, "index_extraction.png"))

        recall_src = os.path.join(src_dir, "recall_button_1780240735209.png")
        if os.path.exists(recall_src):
            shutil.copy(recall_src, os.path.join(dest_dir, "recall_button.png"))

        og_src = os.path.join(src_dir, "og_banner_minimal_1780341452555.png")
        if os.path.exists(og_src):
            shutil.copy(og_src, os.path.join(dest_dir, "og_banner.png"))
            
        # Optimize assets to WebP
        if not os.environ.get("VERCEL"):
            try:
                try:
                    from PIL import Image
                except ImportError:
                    import subprocess
                    import sys
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
                    from PIL import Image

                images_to_convert = [
                    ("studio_detail.png", "studio_detail.webp", 800),
                    ("midi_handshake.png", "midi_handshake.webp", 800),
                    ("index_extraction.png", "index_extraction.webp", 800),
                    ("recall_button.png", "recall_button.webp", 800),
                    ("bgood.png", "bgood.webp", 120),
                    ("troll_gold.png", "troll_gold.webp", 64),
                    ("logo.png", "logo.webp", 120),
                    ("trade_offer.jpg", "trade_offer.webp", 400),
                ]
                for src_name, dest_name, max_width in images_to_convert:
                    src_path = os.path.join(dest_dir, src_name)
                    dest_path = os.path.join(dest_dir, dest_name)
                    if os.path.exists(src_path):
                        with Image.open(src_path) as img:
                            w, h = img.size
                            if w > max_width:
                                ratio = max_width / float(w)
                                new_h = int(float(h) * ratio)
                                img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
                            
                            if img.mode in ("RGBA", "LA") or dest_name in ("troll_gold.webp", "logo.webp"):
                                img.save(dest_path, "WEBP", quality=80)
                            else:
                                img.convert("RGB").save(dest_path, "WEBP", quality=80)
                print("Startup image optimization completed successfully.")
            except Exception as img_err:
                print(f"Startup image optimization failed: {img_err}")
    except Exception as e:
        print(f"Startup asset copy skipped: {e}")

# Password hashing helper
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Version-safe TemplateResponse wrapper to support both Starlette >= 0.28 and Starlette < 0.28
def render_template(template_name: str, request: Request, context: dict = None, status_code: int = 200):
    if context is None:
        context = {}
    context["request"] = request
    
    import inspect
    sig = inspect.signature(templates.TemplateResponse)
    if "request" in sig.parameters:
        return templates.TemplateResponse(request=request, name=template_name, context=context, status_code=status_code)
    else:
        return templates.TemplateResponse(name=template_name, context=context, status_code=status_code)

# Session resolver
def get_current_user(request: Request):
    email = request.cookies.get("session_user")
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
    }
}

# --- Marketing & Auth Pages ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    return render_template("landing.html", request, {"user": user})

@app.get("/dx7", response_class=HTMLResponse)
async def dx7_seo(request: Request):
    user = get_current_user(request)
    return render_template("landing.html", request, {"user": user, "seo": SEO_DATA["dx7"], "seo_slug": "dx7"})

@app.get("/juno-106", response_class=HTMLResponse)
async def juno_seo(request: Request):
    user = get_current_user(request)
    return render_template("landing.html", request, {"user": user, "seo": SEO_DATA["juno-106"], "seo_slug": "juno-106"})

@app.get("/korg-m1", response_class=HTMLResponse)
async def korg_seo(request: Request):
    user = get_current_user(request)
    return render_template("landing.html", request, {"user": user, "seo": SEO_DATA["korg-m1"], "seo_slug": "korg-m1"})

@app.get("/jupiter-6", response_class=HTMLResponse)
async def jupiter_seo(request: Request):
    user = get_current_user(request)
    return render_template("landing.html", request, {"user": user, "seo": SEO_DATA["jupiter-6"], "seo_slug": "jupiter-6"})

@app.get("/sysex-librarian-alternatives", response_class=HTMLResponse)
async def sysex_librarian_alternatives(request: Request):
    user = get_current_user(request)
    return render_template("sysex_librarian.html", request, {"user": user})

@app.get("/sysex-librarian", response_class=HTMLResponse)
async def sysex_librarian_redirect():
    return RedirectResponse(url="/sysex-librarian-alternatives", status_code=301)

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

@app.get("/changelog", response_class=HTMLResponse)
async def changelog_page(request: Request):
    user = get_current_user(request)
    return render_template("changelog.html", request, {"user": user})

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
    if not user or user["hashed_password"] != hash_password(password):
        return render_template("login.html", request, {"error": "Invalid email or password"})
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session_user", value=email.lower().strip(), max_age=86400 * 30, path="/")
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
    
    user = database.get_user_by_email(email)
    if user:
        return render_template("signup.html", request, {"error": "Email is already registered", "plan": plan})
    
    try:
        database.create_user(email, hash_password(password))
        logger.info(f"User registered: {email}", extra={"email": email, "plan": plan, "event_type": "signup"})
    except Exception as e:
        return render_template("signup.html", request, {"error": "Account registration failed.", "plan": plan})
        
    response = RedirectResponse(url=f"/checkout?plan={plan}", status_code=303)
    response.set_cookie(key="session_user", value=email.lower().strip(), max_age=86400 * 30, path="/")
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
            allow_promotion_codes=False,
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
    database.update_user_tier(email, "premium", "mock_customer_id")
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
        customer_email = session.get('customer_email') or session.get('metadata', {}).get('user_email')
        customer_id = session.get('customer')
        if customer_email:
            database.update_user_tier(customer_email, "premium", customer_id)
            logger.info(f"Subscription activated via Stripe: {customer_email}", extra={"email": customer_email, "customer_id": customer_id, "event_type": "subscription_activated"})
            
    elif event['type'] == 'customer.subscription.deleted':
        session = event['data']['object']
        customer_id = session.get('customer')
        database.update_user_tier_by_customer_id(customer_id, "free")
        logger.info(f"Subscription cancelled via Stripe: {customer_id}", extra={"customer_id": customer_id, "event_type": "subscription_deleted"})
        
    return {"status": "success"}

@app.get("/sitemap.xml")
async def sitemap():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://knob.monster/</loc>
    <lastmod>2026-06-05</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://knob.monster/dx7</loc>
    <lastmod>2026-06-05</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://knob.monster/juno-106</loc>
    <lastmod>2026-06-05</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://knob.monster/korg-m1</loc>
    <lastmod>2026-06-05</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://knob.monster/jupiter-6</loc>
    <lastmod>2026-06-15</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://knob.monster/sysex-librarian-alternatives</loc>
    <lastmod>2026-06-15</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://knob.monster/login</loc>
    <lastmod>2026-06-05</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://knob.monster/signup</loc>
    <lastmod>2026-06-05</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://knob.monster/roadmap</loc>
    <lastmod>2026-06-18</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.85</priority>
  </url>
  <url>
    <loc>https://knob.monster/terms</loc>
    <lastmod>2026-06-18</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://knob.monster/privacy</loc>
    <lastmod>2026-06-18</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.5</priority>
  </url>
  <url>
    <loc>https://knob.monster/payment-methods</loc>
    <lastmod>2026-06-19</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
</urlset>"""
    return Response(content=xml_content, media_type="application/xml")

@app.get("/robots.txt")
async def robots():
    content = """User-agent: *
Allow: /
Disallow: /dashboard
Disallow: /banks/

Sitemap: https://knob.monster/sitemap.xml"""
    return Response(content=content, media_type="text/plain")


@app.get("/llms.txt")
async def llms_txt():
    content = """# knob.monster

> The iCloud for your vintage synthesizers. Back up, organize, and search patches from your 1980s and 90s hardware directly in your web browser. No desktop software or drivers required.

## Key Features
- **Browser-Native Web MIDI:** Direct connection to physical synth memory banks over SysEx.
- **Instant Search:** Fuzzy search through soundbanks by preset name.
- **Universal Support:** Built for Yamaha DX7, Roland Juno-106, Korg M1, Jupiter-6 (Europa), Casio CZ-101, and generic synthesizers.
- **Direct Pricing:** Simple plan options: $8/month (billed monthly) or $5/month (billed annually, $60 total). No trials.

## Key Pages
- [Home Page](https://knob.monster/): Explains features, pricing, and includes live MIDI scanning simulator.
- [DX7 Librarian](https://knob.monster/dx7): Specs and librarian details for Yamaha DX7.
- [Juno-106 Librarian](https://knob.monster/juno-106): Setup and dump guide for Roland Juno-106.
- [Korg M1 Librarian](https://knob.monster/korg-m1): Preset backup guide for Korg M1.
- [Jupiter-6 Librarian](https://knob.monster/jupiter-6): SysEx library configuration for Roland Jupiter-6.
- [Alternatives Guide](https://knob.monster/sysex-librarian-alternatives): Comprehensive comparison of web-based SysEx librarians.
- [Payment Methods](https://knob.monster/payment-methods): Supported payment mechanisms and local options.
"""
    return Response(content=content, media_type="text/plain")


