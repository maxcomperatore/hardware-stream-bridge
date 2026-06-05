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
    logger.info("PostHog OTLP Logging initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize PostHog OTLP Logging: {e}")

app = FastAPI(title="Knob Monster - Vintage Synth Patch Manager")

# Absolute path of the directory containing main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Mount Static Files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Configure Stripe key & fallback mock mode
STRIPE_SECRET_KEY = "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"
STRIPE_WEBHOOK_SECRET = "whsec_AWPK4gRmIUdFkUXAzn9IMufmJF5pW5wR"
stripe.api_key = STRIPE_SECRET_KEY

STRIPE_PRICE_ID_YEARLY = "price_1TdWxPLuSQGuB7eyZvIeKp7r"
STRIPE_PRICE_ID_MONTHLY = "price_1TdWwjLuSQGuB7ey4hIhr44e"
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
        
        hero_src = os.path.join(src_dir, "vintage_synth_hero_1780240317485.png")
        if os.path.exists(hero_src):
            shutil.copy(hero_src, os.path.join(dest_dir, "vintage_synth_hero.png"))
            
        detail_src = os.path.join(src_dir, "studio_detail_1780240351621.png")
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

        handshake_src = os.path.join(src_dir, "midi_handshake_1780240701609.png")
        if os.path.exists(handshake_src):
            shutil.copy(handshake_src, os.path.join(dest_dir, "midi_handshake.png"))

        dashboard_src = os.path.join(src_dir, "dashboard_preview_1780269292608.png")
        if not os.path.exists(dashboard_src):
            dashboard_src = os.path.join(src_dir, "media__1780266951702.png")
        if not os.path.exists(dashboard_src):
            dashboard_src = os.path.join(src_dir, "index_extraction_1780240720083.png")
        if os.path.exists(dashboard_src):
            shutil.copy(dashboard_src, os.path.join(dest_dir, "dashboard_preview.png"))

        extraction_src = os.path.join(src_dir, "index_extraction_artwork_1780272299586.png")
        if not os.path.exists(extraction_src):
            extraction_src = os.path.join(src_dir, "index_extraction_1780240720083.png")
        if os.path.exists(extraction_src):
            shutil.copy(extraction_src, os.path.join(dest_dir, "index_extraction.png"))

        recall_src = os.path.join(src_dir, "recall_button_1780240735209.png")
        if os.path.exists(recall_src):
            shutil.copy(recall_src, os.path.join(dest_dir, "recall_button.png"))

        og_src = os.path.join(src_dir, "og_banner_minimal_1780341452555.png")
        if os.path.exists(og_src):
            shutil.copy(og_src, os.path.join(dest_dir, "og_banner.png"))
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
        "title": "Yamaha DX7 SysEx Librarian & Patch Backup | knob.monster",
        "description": "The ultimate browser-native Yamaha DX7 SysEx librarian. Back up, search, and recall DX7 soundbanks in 1-click via Web MIDI. No drivers required.",
        "keywords": "yamaha dx7 sysex librarian, dx7 patch manager, dx7 editor online, dx7 web midi, dx7 patches",
        "synth_name": "Yamaha DX7",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Yamaha DX7.</span>",
        "hero_subtitle": "Back up, search, and recall Yamaha DX7 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
    },
    "juno-106": {
        "title": "Roland Juno-106 Patch Librarian & Editor | knob.monster",
        "description": "The ultimate browser-native Roland Juno-106 SysEx librarian. Back up, search, and recall Juno-106 soundbanks in 1-click via Web MIDI. No drivers required.",
        "keywords": "roland juno-106 librarian, juno 106 patch manager, juno 106 sysex online, juno 106 editor",
        "synth_name": "Roland Juno-106",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Roland Juno-106.</span>",
        "hero_subtitle": "Back up, search, and recall Roland Juno-106 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
    },
    "korg-m1": {
        "title": "Korg M1 SysEx Librarian & Preset Manager | knob.monster",
        "description": "The ultimate browser-native Korg M1 SysEx librarian. Back up, search, and recall Korg M1 soundbanks in 1-click via Web MIDI. No drivers required.",
        "keywords": "korg m1 sysex librarian, korg m1 patch manager, korg m1 editor online, korg m1 patches",
        "synth_name": "Korg M1",
        "hero_title": "The iCloud for your <br class=\"hidden sm:inline\"><span class=\"text-zinc-550\">Korg M1.</span>",
        "hero_subtitle": "Back up, search, and recall Korg M1 patches directly from your browser. Zero setup, zero drivers, instant 1-click MIDI transfers."
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

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return render_template("terms.html", request)

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return render_template("privacy.html", request)

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

    # Paywall verification: free users are capped at 3 soundbanks
    if user["tier"] == "free":
        current_banks = database.get_all_banks(user["id"])
        if len(current_banks) >= 3:
            return Response(status_code=402, headers={"HX-Trigger": "triggerUpgradeModal"})

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

    # Paywall verification: free users are capped at 3 soundbanks
    if user["tier"] == "free":
        current_banks = database.get_all_banks(user["id"])
        if len(current_banks) >= 3:
            return Response(status_code=402, headers={"HX-Trigger": "triggerUpgradeModal"})

    sysex_bytes = await file.read()
    sysex_hex = sysex_bytes.hex()
    
    # Parse voices
    if synth_model == "Yamaha DX7":
        patch_names = parser.parse_dx7_sysex(sysex_bytes)
    elif synth_model == "Roland Juno-106":
        patch_names = parser.parse_juno106_sysex(sysex_bytes)
    elif synth_model == "Korg M1":
        patch_names = parser.parse_korg_m1_sysex(sysex_bytes)
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
        
    database.delete_bank(bank_id, user["id"])
    banks = database.get_all_banks(user["id"])
    return render_template("bank_list.html", request, {"banks": banks})

@app.get("/banks/{bank_id}/download")
async def download_bank(request: Request, bank_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
        
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
            subscription_data={
                'trial_period_days': 7,
            },
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


