"""
ppp_pricing.py — Purchasing Power Parity Dynamic Pricing Engine
================================================================
Fetches real-time exchange rates + ARS MEP/Blue dollar (dolarapi.com),
calculates a complex GDP-per-capita PPP discount formula for every country,
and returns a Stripe-ready `price_data` dict with unit_amount in cents.

No hardcoded Stripe Price IDs needed. Everything is computed on the fly.
"""

import asyncio
import logging
import math
import time
from functools import lru_cache
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1.  BASE PRICE (USD)
# ---------------------------------------------------------------------------
BASE_USD_PRICE = 49.00          # Your product's US price
MIN_USD_FLOOR  = 9.00           # Never go below $9 equivalent (abuse floor)
MAX_USD_CEIL   = 49.00          # Never exceed base price

# ---------------------------------------------------------------------------
# 2.  GDP PER CAPITA (USD, 2024 IMF estimates) — used for PPP formula
#     Source: IMF World Economic Outlook Database April 2024
# ---------------------------------------------------------------------------
GDP_PER_CAPITA_USD: dict[str, float] = {
    # --- Tier 0: Ultra-High Income (No discount) ---
    "US": 85_373,  "CH": 105_669, "NO": 94_660, "LU": 131_384,
    "SG": 88_447,  "IE": 106_059, "IS": 78_837,  "DK": 68_827,
    "AU": 64_964,  "SE": 59_267,  "NL": 63_754,  "FI": 55_715,
    "AT": 58_013,  "CA": 53_247,  "DE": 54_291,  "BE": 54_080,
    "GB": 49_100,  "FR": 45_592,  "JP": 33_950,  "NZ": 46_377,
    "AE": 49_000,  "QA": 76_000,

    # --- Tier 1: High Income (5–20% discount) ---
    "IL": 54_771,  "KR": 35_196,  "IT": 38_000,  "ES": 33_090,
    "PT": 27_100,  "CZ": 30_500,  "SI": 33_900,  "MT": 33_000,
    "EE": 31_700,  "SK": 24_200,  "LV": 24_500,  "LT": 29_300,
    "CY": 35_700,  "HR": 22_800,  "PL": 22_300,  "HU": 22_700,
    "GR": 22_000,  "RO": 19_500,  "BG": 15_600,  "TR": 15_700,
    "SA": 28_000,  "TW": 35_000,  "HK": 53_000,

    # --- Tier 2: Upper-Middle Income (20–40% discount) ---
    "MX": 11_000,  "BR": 10_100,  "ZA": 7_500,   "TH": 7_700,
    "CL": 16_000,  "CO": 7_200,   "PE": 7_400,   "EC": 6_200,
    "CN": 12_720,  "MY": 13_000,  "UA": 5_000,   "RS": 11_000,
    "MK": 8_100,   "BA": 7_800,   "AL": 7_100,   "ME": 10_500,

    # --- Tier 3: Lower-Middle Income (40–65% discount) ---
    "AR": 14_000,  # Argentina special — PPP adjusted for blue dollar reality
    "IN": 2_411,   "PH": 3_500,   "ID": 4_900,   "VN": 4_300,
    "EG": 4_200,   "NG": 2_200,   "PK": 1_700,   "BD": 2_600,
    "MA": 3_800,   "TN": 4_000,   "KE": 2_100,   "GH": 2_400,
    "UZ": 2_900,   "KZ": 13_000,  "AZ": 7_000,   "GE": 7_200,
    "AM": 5_400,   "MD": 5_200,

    # --- Tier 4: Low Income (65–80% discount) ---
    "BO": 3_800,   "PY": 6_000,   "UY": 17_000,  "VE": 4_600,
    "ET": 1_100,   "TZ": 1_200,   "UG": 1_000,   "RW": 950,
    "SD": 750,     "YE": 600,     "SY": 700,     "MM": 1_300,
    "KH": 1_800,   "LA": 2_100,   "NP": 1_400,   "MN": 5_000,
}

# US GDP per capita is the normalization baseline
US_GDP_BASELINE = GDP_PER_CAPITA_USD["US"]

# ---------------------------------------------------------------------------
# 3.  EXCHANGE RATE CACHE  (TTL = 3 hours)
# ---------------------------------------------------------------------------
_fx_cache: dict[str, tuple[float, float]] = {}   # currency -> (rate, timestamp)
_ars_cache: tuple[float, float] | None = None     # (blue_venta, timestamp)
FX_CACHE_TTL  = 10_800   # 3 hours
ARS_CACHE_TTL =  1_800   # 30 minutes (blue dollar moves fast)


async def _fetch_fx_rates() -> dict[str, float]:
    """Fetch real-time FX rates from open.er-api.com (free, no key needed)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://open.er-api.com/v6/latest/USD")
            resp.raise_for_status()
            return resp.json().get("rates", {})
    except Exception as exc:
        logger.warning("FX rate fetch failed: %s", exc)
        return {}


async def get_fx_rate(currency: str) -> float:
    """Return the USD→currency rate, with 3-hour cache."""
    currency = currency.upper()
    now = time.monotonic()
    if currency in _fx_cache:
        rate, ts = _fx_cache[currency]
        if now - ts < FX_CACHE_TTL:
            return rate
    rates = await _fetch_fx_rates()
    for cur, rate in rates.items():
        _fx_cache[cur.upper()] = (float(rate), now)
    return float(_fx_cache.get(currency, (1.0, now))[0])


async def get_ars_blue_rate() -> float:
    """
    Fetch the ARS blue/MEP dollar venta rate from dolarapi.com.
    Returns ARS per 1 USD (blue market rate).

    Endpoint: GET https://dolarapi.com/v1/dolares/blue
    Response: { "compra": N, "venta": N, "casa": "blue", ... }
    """
    global _ars_cache
    now = time.monotonic()
    if _ars_cache is not None:
        rate, ts = _ars_cache
        if now - ts < ARS_CACHE_TTL:
            return rate
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://dolarapi.com/v1/dolares/blue")
            resp.raise_for_status()
            data = resp.json()
            venta = float(data.get("venta", 0))
            if venta > 0:
                _ars_cache = (venta, now)
                logger.info("ARS blue venta fetched: ARS %.2f per USD", venta)
                return venta
    except Exception as exc:
        logger.warning("ARS blue rate fetch failed: %s", exc)
    # Fallback: official ARS rate from open.er-api
    official = await get_fx_rate("ARS")
    logger.warning("Falling back to official ARS rate: %.2f", official)
    _ars_cache = (official, now)
    return official


# ---------------------------------------------------------------------------
# 4.  THE PPP FORMULA — Complex sigmoid-based purchasing power discount
# ---------------------------------------------------------------------------

def _sigmoid_ppp_discount(gdp_ratio: float) -> float:
    """
    Sigmoid-based PPP discount curve.

    gdp_ratio = target_country_gdp / US_gdp  (0.0 → 1.0+)

    Returns a discount factor between 0.0 (no discount) and 0.80 (80% off).

    Formula:
        raw_discount = 1 - gdp_ratio^alpha
        discount = clamp(raw_discount * steepness_multiplier, 0, max_discount)

    The sigmoid ensures smooth transitions and avoids cliff-edges.
    """
    alpha = 0.45           # Power curve shaping (< 0.5 = more generous to poor countries)
    max_discount = 0.80    # Maximum 80% discount
    steepness = 1.15       # Amplifier so mid-tier countries get meaningful savings

    if gdp_ratio >= 1.0:
        return 0.0         # Richer-than-US or equal → no discount

    raw = 1.0 - (gdp_ratio ** alpha)
    discounted = min(raw * steepness, max_discount)

    # Apply sigmoid smoothing to prevent abrupt jumps
    # sigmoid(x) = 1 / (1 + e^(-k*(x-0.5)))
    k = 8.0
    smoothed = 1.0 / (1.0 + math.exp(-k * (discounted - 0.5)))
    # Rescale from sigmoid output [~0.018, ~0.982] back to [0, max_discount]
    normalized = (smoothed - 0.5) * max_discount * 1.65
    return max(0.0, min(normalized, max_discount))


def _compute_ppp_price_usd(country_code: str) -> float:
    """
    Compute the final PPP-adjusted price in USD for a given country.

    Uses GDP per capita ratio with sigmoid discount curve.
    Argentina gets an extra adjustment for the blue dollar reality gap.
    """
    gdp = GDP_PER_CAPITA_USD.get(country_code.upper(), US_GDP_BASELINE)
    gdp_ratio = gdp / US_GDP_BASELINE
    discount = _sigmoid_ppp_discount(gdp_ratio)

    adjusted_usd = BASE_USD_PRICE * (1.0 - discount)

    # Argentina specific: halve the price further to reflect
    # the gap between official and blue dollar purchasing power.
    # Real Argentine purchasing power is ~40-50% lower than GDP implies.
    if country_code.upper() == "AR":
        adjusted_usd *= 0.55

    return max(MIN_USD_FLOOR, min(adjusted_usd, MAX_USD_CEIL))


def _psychological_round(amount: float, currency: str) -> int:
    """
    Round to psychologically appealing price points.
    Returns integer unit in the smallest currency unit (cents for most, 1 for JPY).

    Examples:
        USD 14.73 → 1499 (=$14.99)
        ARS 27350 → 2749900 (=ARS 27,499 → stored as cents)
        JPY 1923  → 1900
    """
    # True zero-decimal currencies (Stripe stores whole units, no cents)
    zero_decimal = {"JPY", "KRW", "VND", "IDR", "CLP", "PYG", "HUF"}

    # High-inflation / large-number currencies: Stripe stores cents but
    # nobody prices in centavos/fils/etc — round to nearest 100 pesos
    round_to_hundreds = {"ARS", "COP", "UYU", "BOB", "DOP", "PYG", "NGN", "EGP", "PKR", "BDT"}

    cur = currency.upper()

    if cur in zero_decimal:
        return int(round(amount / 100.0) * 100)

    if cur in round_to_hundreds:
        # Round to nearest 100 pesos, then convert to cents for Stripe
        rounded_pesos = round(amount / 100.0) * 100
        # Snap to a clean psychological number (x99 or x000)
        thousands = rounded_pesos / 1000
        snapped = (math.floor(thousands) + 0.999) * 1000
        return int(round(snapped * 100))   # → Stripe cents

    # Standard 2-decimal currencies: snap to .99
    dollars = amount
    floored = math.floor(dollars)
    snapped = (floored - 1 + 0.99) if dollars - floored < 0.5 else (floored + 0.99)
    result = int(round(snapped * 100))
    return max(99, result)


# ---------------------------------------------------------------------------
# 5.  MAIN PUBLIC API
# ---------------------------------------------------------------------------

async def compute_ppp_checkout(
    country_code: str,
    product_name: str = "bipluk+ Lifetime Access",
    product_description: str = "One-time payment. Yours forever. Zero monthly rent.",
) -> dict[str, Any]:
    """
    Compute a fully dynamic Stripe `price_data` line item dict for a given country.

    For ARS, fetches live blue dollar rate from dolarapi.com.
    For all others, fetches live FX from open.er-api.com.

    Returns a dict ready to pass directly to stripe.checkout.Session.create().
    """
    code = country_code.upper()

    # Step 1: Compute PPP-adjusted USD price
    ppp_usd = _compute_ppp_price_usd(code)

    # Step 2: Determine currency
    if code == "AR":
        currency = "ARS"
        fx_rate = await get_ars_blue_rate()
    else:
        # Map country → currency (simplified for major markets)
        currency_map = {
            "GB": "GBP", "AU": "AUD", "CA": "CAD", "JP": "JPY",
            "CH": "CHF", "LI": "CHF", "MX": "MXN", "BR": "BRL",
            "IN": "INR", "CL": "CLP", "CO": "COP", "PE": "PEN",
            "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON",
            "TR": "TRY", "KR": "KRW", "SG": "SGD", "HK": "HKD",
            "NZ": "NZD", "ZA": "ZAR", "NG": "NGN", "EG": "EGP",
            "ID": "IDR", "TH": "THB", "MY": "MYR", "PH": "PHP",
            "VN": "VND", "PK": "PKR", "BD": "BDT", "UA": "UAH",
            "GE": "GEL", "KZ": "KZT", "UZ": "UZS", "AZ": "AZN",
        }
        # EU block → EUR
        eu_countries = {
            "DE", "FR", "IT", "ES", "PT", "NL", "BE", "AT", "FI", "IE",
            "GR", "SK", "SI", "EE", "LV", "LT", "LU", "MT", "CY", "HR",
        }
        if code in eu_countries:
            currency = "EUR"
        else:
            currency = currency_map.get(code, "USD")

        fx_rate = await get_fx_rate(currency) if currency != "USD" else 1.0

    # Step 3: Convert PPP USD price to local currency
    local_amount = ppp_usd * fx_rate

    # Step 4: Psychological rounding → Stripe cents
    unit_amount = _psychological_round(local_amount, currency)

    # Step 5: Compute effective USD discount % for logging/display
    effective_usd = ppp_usd
    discount_pct = round((1 - effective_usd / BASE_USD_PRICE) * 100, 1)

    logger.info(
        "PPP checkout | country=%s currency=%s ppp_usd=%.2f fx=%.4f "
        "local=%.2f unit_amount=%d discount=%.1f%%",
        code, currency, ppp_usd, fx_rate, local_amount, unit_amount, discount_pct,
    )

    return {
        "price_data": {
            "currency": currency.lower(),
            "unit_amount": unit_amount,
            "product_data": {
                "name": product_name[:250],
                "description": product_description[:500],
            },
        },
        "quantity": 1,
        # Extra metadata (not sent to Stripe, for logging / display)
        "_meta": {
            "country_code": code,
            "currency": currency,
            "ppp_usd_price": round(ppp_usd, 2),
            "fx_rate": round(fx_rate, 4),
            "local_amount_raw": round(local_amount, 2),
            "unit_amount_cents": unit_amount,
            "discount_pct": discount_pct,
        },
    }


async def get_ppp_display_price(country_code: str) -> dict[str, Any]:
    """
    Lightweight version for template display (landing page, pricing section).
    Returns human-readable price string + metadata without building full line item.
    """
    result = await compute_ppp_checkout(country_code)
    meta = result["_meta"]
    currency = meta["currency"]
    unit = meta["unit_amount_cents"]

    zero_decimal = {"JPY", "KRW", "VND", "IDR", "CLP", "PYG", "HUF"}
    round_to_hundreds = {"ARS", "COP", "UYU", "BOB", "DOP", "NGN", "EGP", "PKR", "BDT"}
    cur = currency.upper()
    if cur in zero_decimal:
        display_amount = f"{unit:,}"
    elif cur in round_to_hundreds:
        # Show whole pesos, no centavos  e.g. "27.499"
        pesos = unit // 100
        display_amount = f"{pesos:,}"
    else:
        display_amount = f"{unit / 100:,.2f}"

    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "Fr.",
        "ARS": "$", "BRL": "R$", "MXN": "$", "INR": "₹", "KRW": "₩",
        "AUD": "$", "CAD": "$", "NZD": "$", "SGD": "$", "HKD": "$",
        "CLP": "$", "COP": "$", "PEN": "S/.", "PLN": "zł", "CZK": "Kč",
        "HUF": "Ft", "RON": "lei", "TRY": "₺", "ZAR": "R", "NGN": "₦",
        "EGP": "E£", "IDR": "Rp", "THB": "฿", "MYR": "RM", "PHP": "₱",
        "VND": "₫", "PKR": "₨", "BDT": "৳", "UAH": "₴",
    }
    symbol = symbols.get(currency.upper(), currency + " ")

    return {
        "display": f"{symbol}{display_amount}",
        "currency": currency,
        "discount_pct": meta["discount_pct"],
        "ppp_usd": meta["ppp_usd_price"],
        "is_ppp": meta["discount_pct"] > 0,
        "unit_amount_cents": unit,
    }
