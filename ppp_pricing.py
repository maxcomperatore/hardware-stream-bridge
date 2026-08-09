"""
ppp_pricing.py — Purchasing Power Parity Dynamic Pricing Engine
================================================================
Fetches real-time exchange rates + ARS MEP/Blue dollar (dolarapi.com),
calculates a complex GDP-per-capita PPP discount formula for every country,
and returns a Stripe-ready `price_data` dict with unit_amount in cents.
Geolocalized checkout descriptions included.

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
    # EU countries intentionally omitted — they use static EUR catalog pricing.
    "US": 85_373,  "CH": 105_669, "NO": 94_660,
    "SG": 88_447,  "IS": 78_837,
    "AU": 64_964,  "CA": 53_247,
    "GB": 49_100,  "JP": 33_950,  "NZ": 46_377,
    "AE": 49_000,  "QA": 76_000,

    # --- Tier 1: High Income (5–20% discount) ---
    "IL": 54_771,  "KR": 35_196,  "TR": 15_700,
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
    """
    alpha = 0.45           # Power curve shaping (< 0.5 = more generous to poor countries)
    max_discount = 0.80    # Maximum 80% discount
    steepness = 1.15       # Amplifier so mid-tier countries get meaningful savings

    if gdp_ratio >= 1.0:
        return 0.0         # Richer-than-US or equal → no discount

    raw = 1.0 - (gdp_ratio ** alpha)
    discounted = min(raw * steepness, max_discount)

    # Apply sigmoid smoothing to prevent abrupt jumps
    k = 8.0
    smoothed = 1.0 / (1.0 + math.exp(-k * (discounted - 0.5)))
    # Rescale from sigmoid output [~0.018, ~0.982] back to [0, max_discount]
    normalized = (smoothed - 0.5) * max_discount * 1.65
    return max(0.0, min(normalized, max_discount))


def _compute_ppp_price_usd(country_code: str) -> float:
    """
    Compute the final PPP-adjusted price in USD for a given country.
    """
    gdp = GDP_PER_CAPITA_USD.get(country_code.upper(), US_GDP_BASELINE)
    gdp_ratio = gdp / US_GDP_BASELINE
    discount = _sigmoid_ppp_discount(gdp_ratio)

    adjusted_usd = BASE_USD_PRICE * (1.0 - discount)

    # Argentina specific: halve the price further to reflect
    # the gap between official and blue dollar purchasing power.
    if country_code.upper() == "AR":
        adjusted_usd *= 0.55

    return max(MIN_USD_FLOOR, min(adjusted_usd, MAX_USD_CEIL))


def _snap_ending_9(whole: float) -> int:
    """Nearest whole amount ending in 9 (479, 489, 499…)."""
    n = max(9, int(round(whole)))
    base = (n // 10) * 10
    candidates = [base - 1, base + 9, base + 19]
    candidates = [c for c in candidates if c >= 9]
    return min(candidates, key=lambda c: abs(c - n))


def _snap_ending_99(whole: float) -> int:
    """Nearest whole amount ending in 99 (399, 499, 999…)."""
    n = max(99, int(round(whole)))
    base = (n // 100) * 100
    candidates = [base - 1, base + 99]
    candidates = [c for c in candidates if c >= 99]
    return min(candidates, key=lambda c: abs(c - n))


def _psychological_round(amount: float, currency: str) -> int:
    """Round to culture-local price endings."""
    zero_decimal = {"JPY", "KRW", "VND", "IDR", "CLP", "PYG", "HUF"}
    round_to_x999 = {"ARS", "COP", "UYU", "BOB", "DOP", "NGN", "EGP", "PKR", "BDT"}
    whole_ending_9 = {
        "MXN", "PEN", "TRY", "THB", "MYR", "PHP", "ZAR", "UAH",
        "GEL", "KZT", "UZS", "AZN", "INR",
    }
    ending_90 = {"BRL"}
    ending_99 = {"USD", "CAD", "AUD", "NZD", "SGD", "HKD", "GBP", "CHF", "EUR"}

    cur = currency.upper()

    if cur in zero_decimal:
        snapped = _snap_ending_9(amount) if amount < 1000 else _snap_ending_99(amount)
        if amount >= 1000:
            return int(round(amount / 100.0) * 100)
        return max(1, snapped)

    if cur in round_to_x999:
        rounded = round(amount / 100.0) * 100
        thousands = rounded / 1000
        snapped = (math.floor(thousands) + 0.999) * 1000
        return int(round(snapped * 100))

    if cur in ending_90:
        floor_major = math.floor(amount)
        candidates = [floor_major - 1 + 0.90, floor_major + 0.90, floor_major + 1 + 0.90]
        snapped = min((c for c in candidates if c >= 0.90), key=lambda c: abs(c - amount))
        return max(90, int(round(snapped * 100)))

    if cur in whole_ending_9:
        whole = _snap_ending_9(amount) if amount < 1000 else _snap_ending_99(amount)
        return max(900, whole * 100)

    if cur in ending_99:
        floored = math.floor(amount)
        snapped = (floored - 1 + 0.99) if amount - floored < 0.5 else (floored + 0.99)
        return max(99, int(round(snapped * 100)))

    whole = _snap_ending_9(amount)
    return max(900, whole * 100)


# ---------------------------------------------------------------------------
# 5.  MAIN PUBLIC API
# ---------------------------------------------------------------------------

def _get_localized_description(country_code: str) -> str:
    """Returns a culturally localized Stripe checkout description for every market."""
    code = country_code.upper()
    
    descriptions = {
        # --- Latin America & Spain ---
        "AR": "Pago único. Tuyo para siempre. Olvidate de pagar por mes.", # Argentinian voseo
        "MX": "Pago único. Tuyo para siempre. Cero rentas mensuales.",     # Mexico
        "ES": "Pago único. Tuyo para siempre. Cero cuotas mensuales.",     # Spain
        "CL": "Pago único. Tuyo para siempre. Cero mensualidades.",        # Chile
        "CO": "Pago único. Tuyo para siempre. Sin cobros mensuales.",      # Colombia
        "PE": "Pago único. Tuyo para siempre. Nada de pagos mensuales.",   # Peru
        "UY": "Pago único. Tuyo para siempre. Cero cuotas.",               # Uruguay
        "PY": "Pago único. Tuyo para siempre. Sin cuotas mensuales.",      # Paraguay
        "BO": "Pago único. Tuyo para siempre. Sin pagos mensuales.",       # Bolivia
        "VE": "Pago único. Tuyo para siempre. Sin mensualidades.",         # Venezuela
        "EC": "Pago único. Tuyo para siempre. Cero pagos mensuales.",      # Ecuador
        
        # --- Brazil & Portugal ---
        "BR": "Pagamento único. Seu para sempre. Sem mensalidades.",       # Brazil
        "PT": "Pagamento único. Teu para sempre. Sem mensalidades.",       # Portugal
        
        # --- Western & Northern Europe ---
        "FR": "Paiement unique. À vous pour toujours. Zéro abonnement mensuel.", # France
        "DE": "Einmalige Zahlung. Gehört für immer dir. Keine monatlichen Gebühren.", # Germany
        "AT": "Einmalige Zahlung. Gehört für immer dir. Keine monatlichen Gebühren.", # Austria
        "CH": "Einmalige Zahlung. Gehört für immer dir. Keine monatlichen Gebühren.", # Switzerland
        "IT": "Pagamento unico. Tuo per sempre. Nessun canone mensile.",   # Italy
        "NO": "Engangsbetaling. Din for alltid. Ingen månedlige avgifter.",# Norway
        "IS": "Eingreiðsla. Þitt að eilífu. Engin mánaðargjöld.",          # Iceland
        "SE": "Engångsbetalning. Din för alltid. Inga månadsavgifter.",    # Sweden
        "DK": "Engangsbetaling. Din for evigt. Ingen månedlige gebyrer.",  # Denmark
        "FI": "Kertamaksu. Sinun ikuisesti. Ei kuukausimaksuja.",          # Finland
        "NL": "Eenmalige betaling. Voor altijd van jou. Geen maandelijkse kosten.", # Netherlands
        
        # --- Eastern Europe & Balkans ---
        "UA": "Одноразовий платіж. Ваше назавжди. Жодних щомісячних платежів.", # Ukraine
        "RS": "Jednokratno plaćanje. Zauvek tvoje. Bez mesečnih pretplata.",  # Serbia
        "BA": "Jednokratno plaćanje. Zauvijek tvoje. Bez mjesečnih pretplata.",# Bosnia
        "ME": "Jednokratno plaćanje. Zauvijek tvoje. Bez mjesečnih pretplata.",# Montenegro
        "MK": "Еднократна уплата. Твое засекогаш. Без месечни претплати.",    # North Macedonia
        "AL": "Pagesë e vetme. E jotja përgjithmonë. Zero tarifa mujore.",    # Albania
        "PL": "Jednorazowa płatność. Twoje na zawsze. Brak miesięcznych opłat.",# Poland
        "CZ": "Jednorázová platba. Navždy vaše. Žádné měsíční poplatky.",     # Czechia
        "HU": "Egyszeri fizetés. Örökre a tied. Nincs havidíj.",              # Hungary
        "RO": "Plată unică. Al tău pentru totdeauna. Fără abonament lunar.",  # Romania
        
        # --- CIS & Caucasus ---
        "KZ": "Единоразовый платеж. Ваше навсегда. Никаких ежемесячных плат.", # Kazakhstan (Russian widely used in tech)
        "UZ": "Bir martalik to'lov. Umrbod sizniki. Oylik to'lovlarsiz.",      # Uzbekistan
        "GE": "ერთჯერადი გადახდა. შენი სამუდამოდ. ყოველთვიური გადასახადის გარეშე.", # Georgia
        "AM": "Միանվագ վճարում: Ձերն է ընդմիշտ: Առանց ամսական վճարի:",            # Armenia
        "AZ": "Birdəfəlik ödəniş. Həmişəlik sənin. Aylıq ödəniş yoxdur.",      # Azerbaijan
        "MD": "Plată unică. Al tău pentru totdeauna. Fără abonament lunar.",  # Moldova (Romanian)
        
        # --- Middle East & North Africa (Arabic & Hebrew & Turkish) ---
        "IL": "תשלום חד-פעמי. שלך לתמיד. ללא מנוי חודשי.",                 # Israel
        "TR": "Tek seferlik ödeme. Sonsuza kadar senin. Aylık ücret yok.", # Turkey
        "AE": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # UAE
        "QA": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Qatar
        "SA": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Saudi Arabia
        "EG": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Egypt
        "MA": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Morocco
        "TN": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Tunisia
        "SY": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Syria
        "YE": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Yemen
        "SD": "دفع لمرة واحدة. لك للأبد. بدون اشتراك شهري.",                 # Sudan
        
        # --- East Asia ---
        "JP": "買い切り。ずっとあなたのもの。月額料金ゼロ。",                 # Japan
        "KR": "일회성 결제. 평생 소장. 월 구독료 제로.",                      # South Korea
        "CN": "一次性付款。永久拥有。零月租。",                              # China (Simplified)
        "TW": "一次性付款。永久擁有。零月租。",                              # Taiwan (Traditional)
        "HK": "一次性付款。永久擁有。零月租。",                              # Hong Kong (Traditional)
        "MN": "Нэг удаагийн төлбөр. Үүрд таных. Сар бүрийн хураамжгүй.",   # Mongolia
        
        # --- South & Southeast Asia ---
        "IN": "एक बार का भुगतान। हमेशा के लिए आपका। कोई मासिक किराया नहीं।",    # India (Hindi)
        "BD": "এককালীন পেমেন্ট। চিরকালের জন্য আপনার। কোনো মাসিক ভাড়া নেই।",      # Bangladesh
        "PK": "ایک بار کی ادائیگی۔ ہمیشہ کے لیے آپ کا۔ کوئی ماہانہ کرایہ نہیں۔", # Pakistan (Urdu)
        "NP": "एकमुष्ट भुक्तानी। सधैंको लागि तपाईंको। कुनै मासिक भाडा छैन।",      # Nepal
        "ID": "Sekali bayar. Milikmu selamanya. Tanpa biaya bulanan.",     # Indonesia
        "MY": "Bayaran sekali. Milik anda selamanya. Tiada yuran bulanan.",# Malaysia
        "TH": "จ่ายครั้งเดียว. เป็นของคุณตลอดไป. ไม่มีรายเดือน.",                 # Thailand
        "VN": "Thanh toán một lần. Sở hữu trọn đời. Không phí hàng tháng.",# Vietnam
        "PH": "Isang bayad lang. Sayo na habang buhay. Walang monthly fee.", # Philippines (Taglish)
        "KH": "បង់ប្រាក់តែម្តង។ ជារបស់អ្នកជារៀងរហូត។ គ្មានការជួលប្រចាំខែ។",         # Cambodia
        "LA": "ຈ່າຍຄັ້ງດຽວ. ເປັນຂອງທ່ານຕະຫຼອດໄປ. ບໍ່ມີຄ່າເຊົ່າລາຍເດືອນ.",            # Laos
        "MM": "တစ်ကြိမ်တည်းပေးချေပါ။ သင့်အတွက်ထာဝရ။ လစဉ်ကြေးမရှိပါ။",               # Myanmar
        
        # --- Africa (Non-Arabic) ---
        "ZA": "One-time payment. Yours forever. Zero monthly rent.",       # South Africa (English default)
        "NG": "One-time payment. Yours forever. Zero monthly rent.",       # Nigeria (English)
        "KE": "Malipo ya mara moja. Yako milele. Hakuna ada za kila mwezi.",# Kenya (Swahili)
        "TZ": "Malipo ya mara moja. Yako milele. Hakuna ada za kila mwezi.",# Tanzania (Swahili)
        "UG": "One-time payment. Yours forever. Zero monthly rent.",       # Uganda (English)
        "GH": "One-time payment. Yours forever. Zero monthly rent.",       # Ghana (English)
        "RW": "Kwishyura inshuro imwe. Ni ibyawe iteka. Nta bukode bwa buri kwezi.", # Rwanda (Kinyarwanda)
        "ET": "አንድ ጊዜ ክፍያ። ለዘላለም የእርስዎ። ምንም ወርሃዊ ክፍያ የለም።",         # Ethiopia (Amharic)
    }
    
    # English default fallback for US, GB, AU, CA, NZ, SG, and unmapped countries
    return descriptions.get(code, "One-time payment. Yours forever. Zero monthly rent.")


async def compute_ppp_checkout(
    country_code: str,
    product_name: str = "bipluk+",
    product_description: str | None = None,
) -> dict[str, Any]:
    """
    Compute a fully dynamic Stripe `price_data` line item dict for a given country.
    """
    code = country_code.upper()
    
    # Localized text injection
    desc = product_description or _get_localized_description(code)

    # Step 1: Compute PPP-adjusted USD price
    ppp_usd = _compute_ppp_price_usd(code)

    # Step 2: Determine currency
    if code == "AR":
        currency = "ARS"
        fx_rate = await get_ars_blue_rate()
    else:
        currency_map = {
            "GB": "GBP", "AU": "AUD", "CA": "CAD", "JP": "JPY",
            "CH": "CHF", "LI": "CHF", "MX": "MXN", "BR": "BRL",
            "IN": "INR", "CL": "CLP", "CO": "COP", "PE": "PEN",
            "TR": "TRY", "KR": "KRW", "SG": "SGD", "HK": "HKD",
            "NZ": "NZD", "ZA": "ZAR", "NG": "NGN", "EG": "EGP",
            "ID": "IDR", "TH": "THB", "MY": "MYR", "PH": "PHP",
            "VN": "VND", "PK": "PKR", "BD": "BDT", "UA": "UAH",
            "GE": "GEL", "KZ": "KZT", "UZ": "UZS", "AZ": "AZN",
        }
        currency = currency_map.get(code, "USD")
        fx_rate = await get_fx_rate(currency) if currency != "USD" else 1.0

    # Step 3: Convert PPP USD price to local currency
    local_amount = ppp_usd * fx_rate

    # Step 4: Psychological rounding → Stripe cents
    unit_amount = _psychological_round(local_amount, currency)

    # Step 5: Compute effective USD discount %
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
                "description": desc[:500],
            },
        },
        "quantity": 1,
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
    """
    result = await compute_ppp_checkout(country_code)
    meta = result["_meta"]
    currency = meta["currency"]
    unit = meta["unit_amount_cents"]

    zero_decimal = {"JPY", "KRW", "VND", "IDR", "CLP", "PYG", "HUF"}
    whole_display = {
        "ARS", "COP", "UYU", "BOB", "DOP", "NGN", "EGP", "PKR", "BDT",
        "MXN", "PEN", "TRY", "THB", "MYR", "PHP", "ZAR", "UAH",
        "GEL", "KZT", "UZS", "AZN", "INR",
    }
    ending_90_display = {"BRL"}
    cur = currency.upper()

    if cur in zero_decimal:
        display_amount = f"{unit:,}"
    elif cur in whole_display:
        major = unit // 100
        display_amount = f"{major:,}"
    elif cur in ending_90_display:
        major = unit // 100
        cents = unit % 100
        display_amount = f"{major:,}".replace(",", ".") + f",{cents:02d}"
    else:
        display_amount = f"{unit / 100:,.2f}"

    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CHF": "Fr.",
        "ARS": "$", "BRL": "R$", "MXN": "MX$", "INR": "₹", "KRW": "₩",
        "AUD": "$", "CAD": "$", "NZD": "$", "SGD": "$", "HKD": "$",
        "CLP": "$", "COP": "$", "PEN": "S/.", "PLN": "zł", "CZK": "Kč",
        "HUF": "Ft", "RON": "lei", "TRY": "₺", "ZAR": "R", "NGN": "₦",
        "EGP": "E£", "IDR": "Rp", "THB": "฿", "MYR": "RM", "PHP": "₱",
        "VND": "₫", "PKR": "₨", "BDT": "৳", "UAH": "₴",
    }
    symbol = symbols.get(currency.upper(), currency + " ")

    return {
        "display": f"{symbol}{display_amount}",
        "symbol": symbol,
        "amount_display": display_amount,
        "currency": currency,
        "discount_pct": meta["discount_pct"],
        "ppp_usd": meta["ppp_usd_price"],
        "is_ppp": meta["discount_pct"] > 0,
        "unit_amount_cents": unit,
    }