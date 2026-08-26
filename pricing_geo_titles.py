"""Geo-localized pricing section titles with flag."""

from __future__ import annotations

from icon_paths import flag_icon

DEFAULT_PRICING_TITLE = "A pricing system built for fellow synth heads."
ENGLISH_TITLE_TEMPLATE = "A pricing system built for fellow synth heads in {country}"

# Casual local slang — short, self-deprecating, synth-head inside jokes (no trailing period).
PRICING_TITLE_BY_LOCALE: dict[str, str] = {
    "de": "Preise für Leute mit zu vielen Synths",
    "pt": "Preços pra quem já perdeu a conta dos synths",
    "sv": "Priser för synth-nördar som köpte en till",
    "fr": "Des tarifs pour les accros au synthé",
    "es": "Precios para gente con GAS de synth",
    "it": "Prezzi per chi ha troppi synth in casa",
    "nl": "Prijzen voor synth-maniakken zoals jij",
    "pl": "Ceny dla synthomaniaków z pełną piwnicą",
    "da": "Priser til synth-nørder der ikke kan stoppe",
    "fi": "Hinnat synth-nörteille, joilla on liikaa laitteita",
    "no": "Priser for synth-nerder som trenger enda en",
    "cs": "Ceny pro lidi s příliš mnoha synthy doma",
    "ro": "Prețuri pentru dependenți de synth",
    "hu": "Árak akiknek túl sok szinti van otthon",
    "el": "Τιμές για synth addicts σαν εμάς",
    "hr": "Cijene za synth ovisnike s punim studiom",
    "sk": "Ceny pre ľudí čo už nemajú kam dať ďalší synth",
    "sl": "Cene za synth odvisnike z polno sobno",
    "bg": "Цени за synth маниаци с прекалено много кутии",
    "lt": "Kainos synth fanams su per daug dėžių",
    "lv": "Cenas synth ēstiem ar pilnu pagrabu",
    "et": "Hinnad synth-hulludele kellel on liiga palju kaste",
    "ja": "シンセ愛好家向け価格",
}

# Listed countries → locale slang (English-speaking entries use the in-{country} template).
COUNTRY_PRICING_LOCALE: dict[str, str] = {
    "JP": "ja",
    "DE": "de",
    "AT": "de",
    "CH": "de",
    "LI": "de",
    "SE": "sv",
    "DK": "da",
    "FI": "fi",
    "NO": "no",
    "IS": "no",
    "PT": "pt",
    "ES": "es",
    "FR": "fr",
    "BE": "fr",
    "LU": "fr",
    "MC": "fr",
    "NL": "nl",
    "IT": "it",
    "IE": "en",
    "GB": "en",
    "PL": "pl",
    "CZ": "cs",
    "SK": "sk",
    "HU": "hu",
    "RO": "ro",
    "BG": "bg",
    "HR": "hr",
    "SI": "sl",
    "LT": "lt",
    "LV": "lv",
    "EE": "et",
    "GR": "el",
    "CY": "el",
    "MT": "en",
}

COUNTRY_DISPLAY_NAMES: dict[str, str] = {
    "JP": "Japan",
    "US": "the USA",
    "GB": "the UK",
    "CA": "Canada",
    "AU": "Australia",
    "DE": "Germany",
    "CH": "Switzerland",
    "NL": "the Netherlands",
    "AE": "the UAE",
    "PH": "the Philippines",
}


def display_country_name(country_code: str, country_name: str | None = None) -> str:
    code = country_code.strip().upper()
    if code in COUNTRY_DISPLAY_NAMES:
        return COUNTRY_DISPLAY_NAMES[code]
    if country_name and country_name.lower() not in ("everywhere", "unknown"):
        return country_name
    return code


def flag_markup(country_code: str) -> str:
    code = country_code.strip().lower()
    return (
        f'<img src="{flag_icon(code)}" '
        f'width="32" height="24" class="h-6 w-auto inline-block align-middle ml-1.5" alt="" />'
    )


def build_pricing_title(country_code: str | None, country_name: str | None = None, accept_language: str | None = None) -> dict:
    """Return pricing headline text + HTML (always with flag when country is known)."""
    if not country_code:
        return {
            "text": DEFAULT_PRICING_TITLE,
            "html": DEFAULT_PRICING_TITLE,
            "country_code": None,
            "localized": False,
        }

    code = country_code.strip().upper()
    display = display_country_name(code, country_name)
    flag = flag_markup(code)

    # Respect Accept-Language header if browser explicitly prefers English
    prefers_english = False
    if accept_language:
        lang_first = accept_language.split(',')[0].split(';')[0].strip().lower()
        if lang_first.startswith("en"):
            prefers_english = True

    locale = COUNTRY_PRICING_LOCALE.get(code)
    if locale and locale != "en" and not prefers_english:
        text = PRICING_TITLE_BY_LOCALE.get(locale, ENGLISH_TITLE_TEMPLATE.format(country=display))
        text = text.rstrip(".")
    else:
        text = ENGLISH_TITLE_TEMPLATE.format(country=display)

    return {
        "text": text,
        "html": f"{text} {flag}",
        "country_code": code.lower(),
        "localized": bool(locale and locale != "en" and not prefers_english),
    }


def pricing_title_for_country(country_code: str | None, country_name: str | None = None) -> str:
    return build_pricing_title(country_code, country_name)["html"]
