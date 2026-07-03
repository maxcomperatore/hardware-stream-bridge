"""Load configuration from environment (.env locally, Vercel env in production)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")

IS_PRODUCTION = os.environ.get("VERCEL") == "1"


def getenv(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is not None and str(value).strip():
        return str(value).strip()
    return default


def require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# Core
DATABASE_URL = require_env("DATABASE_URL") if IS_PRODUCTION else getenv("DATABASE_URL")
SESSION_SECRET_KEY = require_env("SESSION_SECRET_KEY") if IS_PRODUCTION else getenv(
    "SESSION_SECRET_KEY", "dev-only-session-secret-change-me"
)
SITE_BASE = (getenv("SITE_BASE", "https://knob.monster") or "https://knob.monster").rstrip("/")

# Stripe
STRIPE_SECRET_KEY = getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID_YEARLY = getenv("STRIPE_PRICE_ID_YEARLY")
STRIPE_PRICE_ID_MONTHLY = getenv("STRIPE_PRICE_ID_MONTHLY")
STRIPE_PRICE_ID_LIFETIME = getenv("STRIPE_PRICE_ID_LIFETIME")
STRIPE_PRICE_ID_PERSONAL = getenv("STRIPE_PRICE_ID_PERSONAL") or STRIPE_PRICE_ID_LIFETIME
STRIPE_PRICE_ID_STUDIO = getenv("STRIPE_PRICE_ID_STUDIO")
STRIPE_PRICE_ID_PERSONAL_EUR = getenv("STRIPE_PRICE_ID_PERSONAL_EUR")
STRIPE_PRICE_ID_STUDIO_EUR = getenv("STRIPE_PRICE_ID_STUDIO_EUR")
STRIPE_PRICE_ID_PERSONAL_GBP = getenv("STRIPE_PRICE_ID_PERSONAL_GBP")
STRIPE_PRICE_ID_STUDIO_GBP = getenv("STRIPE_PRICE_ID_STUDIO_GBP")
STRIPE_PRICE_ID_PERSONAL_CAD = getenv("STRIPE_PRICE_ID_PERSONAL_CAD")
STRIPE_PRICE_ID_STUDIO_CAD = getenv("STRIPE_PRICE_ID_STUDIO_CAD")
STRIPE_PRICE_ID_PERSONAL_AUD = getenv("STRIPE_PRICE_ID_PERSONAL_AUD")
STRIPE_PRICE_ID_STUDIO_AUD = getenv("STRIPE_PRICE_ID_STUDIO_AUD")
STRIPE_PRICE_ID_PERSONAL_CHF = getenv("STRIPE_PRICE_ID_PERSONAL_CHF")
STRIPE_PRICE_ID_STUDIO_CHF = getenv("STRIPE_PRICE_ID_STUDIO_CHF")
STRIPE_PRICE_ID_SOUND_PACK = getenv("STRIPE_PRICE_ID_SOUND_PACK")

# Email (Resend)
RESEND_API_KEY = getenv("RESEND_API_KEY")
SMTP_HOST = getenv("SMTP_HOST", "smtp.resend.com")
SMTP_PORT = getenv("SMTP_PORT", "587")
SMTP_USER = getenv("SMTP_USER", "resend")
SMTP_PASSWORD = getenv("SMTP_PASSWORD") or RESEND_API_KEY
SMTP_FROM = getenv("SMTP_FROM", "Knob Monster <vault@knob.monster>")

# Cron / internal auth
CRON_SECRET = getenv("CRON_SECRET")

# Analytics & alerts
POSTHOG_API_KEY = getenv("POSTHOG_API_KEY")
POSTHOG_HOST = getenv("POSTHOG_HOST", "https://e.knob.monster")
DISCORD_WEBHOOK_URL = getenv("DISCORD_WEBHOOK_URL")

# LLM (FAQ / optional features)
OPENROUTER_API_KEY = getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = getenv("OPENROUTER_MODEL", "google/gemini-3.1-flash-lite")
