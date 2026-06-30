#!/usr/bin/env python3
"""
Generate Half Radiation LLC Form 10-K (satirical but numerically accurate).
Run: python scripts/generate_10k.py
Output: static/filings/HALF_RADIATION_FORM_10K_FY2026.pdf
"""

from __future__ import annotations

import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "static", "filings", "HALF_RADIATION_FORM_10K_FY2026.pdf")

# --- Verified Stripe balance summary (Jun 1–28, 2026) ---
PERIOD_START = date(2026, 5, 31)
PERIOD_END = date(2026, 6, 28)
CHARGES_COUNT = 1
GROSS_REVENUE = 60.00
STRIPE_FEES_ACTIVITY = 2.04
STRIPE_FEES_ADDITIONAL = 0.42
STRIPE_TAX = 0.03
TOTAL_FEES = 2.49
NET_INCOME = 57.51
PAYOUTS = 0.00
ENDING_CASH = 57.51
STARTING_CASH = 0.00

SIGNATURE_FONT = "Times-Italic"


def register_signature_font() -> str:
    global SIGNATURE_FONT
    candidates = [
        os.path.join(ROOT, "static", "fonts", "NothingYouCouldDo-Regular.ttf"),
        r"C:\Windows\Fonts\segoesc.ttf",
        r"C:\Windows\Fonts\SegoeScript.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("FilingSignature", path))
                SIGNATURE_FONT = "FilingSignature"
                return SIGNATURE_FONT
            except Exception:
                continue
    return SIGNATURE_FONT


def signature_block(name: str, title: str, styles: dict, sig_date: str | None = None) -> list:
    sig_style = ParagraphStyle(
        "SignatureScript",
        parent=styles["body_left"],
        fontName=SIGNATURE_FONT,
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1a365d"),
        spaceAfter=2,
    )
    blocks = [
        Spacer(1, 8),
        Paragraph(f"/s/ {name}", sig_style),
        signature_scribble(len(name)),
        Spacer(1, 4),
        Paragraph(title, styles["body_left"]),
    ]
    if sig_date:
        blocks.append(Paragraph(f"Date: {sig_date}", styles["body_left"]))
    return blocks


def signature_scribble(name_len: int) -> Drawing:
    width = min(220, 80 + name_len * 9)
    d = Drawing(width, 18)
    d.add(Line(0, 8, width, 8, strokeColor=colors.HexColor("#1a365d"), strokeWidth=0.6))
    d.add(Line(8, 10, 28, 14, strokeColor=colors.HexColor("#1a365d"), strokeWidth=0.8))
    d.add(Line(28, 14, 52, 6, strokeColor=colors.HexColor("#1a365d"), strokeWidth=0.8))
    d.add(Line(52, 6, 78, 12, strokeColor=colors.HexColor("#1a365d"), strokeWidth=0.8))
    d.add(Line(95, 11, 120, 4, strokeColor=colors.HexColor("#1a365d"), strokeWidth=0.7))
    d.add(Line(120, 4, min(width - 12, 165), 10, strokeColor=colors.HexColor("#1a365d"), strokeWidth=0.7))
    return d


def money(v: float) -> str:
    if v < 0:
        return f"(${abs(v):,.2f})"
    return f"${v:,.2f}"


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "body_left": ParagraphStyle(
            "BodyLeft",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=10,
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "toc": ParagraphStyle(
            "TOC",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14,
            leftIndent=12,
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
    }
    return styles


def table(data, col_widths=None, header_rows=1):
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "Times-Bold"),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#f0f0f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, header_rows), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style))
    return t


def _chart_title(d: Drawing, text: str, width: float) -> None:
    d.add(String(width / 2, d.height - 14, text, fontName="Times-Bold", fontSize=10, textAnchor="middle"))


def chart_revenue_waterfall() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 1 — Revenue Bridge (USD)", w)
    bc = VerticalBarChart()
    bc.x = 60
    bc.y = 35
    bc.height = 140
    bc.width = 360
    bc.data = [[GROSS_REVENUE, TOTAL_FEES, NET_INCOME]]
    bc.categoryAxis.categoryNames = ["Gross\nCharges", "Stripe\nFees", "Net to\nBalance"]
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 70
    bc.valueAxis.valueStep = 10
    bc.bars[0].fillColor = colors.HexColor("#3b83f6")
    bc.bars[1].fillColor = colors.HexColor("#f43f5e")
    bc.bars[2].fillColor = colors.HexColor("#10b981")
    bc.barLabelFormat = "%0.2f"
    bc.barLabels.nudge = 10
    d.add(bc)
    return d


def chart_fee_pie() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 2 — Composition of Gross Revenue ($60.00)", w)
    pie = Pie()
    pie.x = 130
    pie.y = 25
    pie.width = 120
    pie.height = 120
    pie.data = [NET_INCOME, STRIPE_FEES_ACTIVITY, STRIPE_FEES_ADDITIONAL, STRIPE_TAX]
    pie.labels = ["Net retained", "Activity fees", "Add'l Stripe", "Tax"]
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = colors.HexColor("#10b981")
    pie.slices[1].fillColor = colors.HexColor("#f59e0b")
    pie.slices[2].fillColor = colors.HexColor("#f43f5e")
    pie.slices[3].fillColor = colors.HexColor("#71717a")
    d.add(pie)
    legend_x = 300
    for i, (label, val) in enumerate([
        ("Net retained", NET_INCOME),
        ("Activity fees", STRIPE_FEES_ACTIVITY),
        ("Additional Stripe fees", STRIPE_FEES_ADDITIONAL),
        ("Tax", STRIPE_TAX),
    ]):
        d.add(String(legend_x, 130 - i * 16, f"{label}: {money(val)}", fontName="Times-Roman", fontSize=8, textAnchor="start"))
    return d


def chart_five_year_hockey_stick() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 3 — Five-Year Revenue Trend (Management insists this is not a hockey stick)", w)
    bc = VerticalBarChart()
    bc.x = 55
    bc.y = 35
    bc.height = 145
    bc.width = 370
    bc.data = [[0, 0, 0, 0, GROSS_REVENUE]]
    bc.categoryAxis.categoryNames = ["2022", "2023", "2024", "2025", "2026*"]
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 70
    bc.valueAxis.valueStep = 10
    for i in range(5):
        bc.bars[i].fillColor = colors.HexColor("#52525b" if i < 4 else "#3b83f6")
    d.add(bc)
    d.add(String(55, 18, "*Partial fiscal period. Prior years reflect pre-existence of knob.monster.", fontName="Times-Italic", fontSize=7, textAnchor="start"))
    return d


def chart_customer_growth() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 4 — Paying Customer Growth (Cumulative)", w)
    lc = HorizontalLineChart()
    lc.x = 60
    lc.y = 40
    lc.height = 130
    lc.width = 360
    lc.data = [[0, 0, 0, 0, 1]]
    lc.categoryAxis.categoryNames = ["May 31", "Jun 7", "Jun 14", "Jun 21", "Jun 24"]
    lc.valueAxis.valueMin = 0
    lc.valueAxis.valueMax = 2
    lc.valueAxis.valueStep = 1
    lc.lines[0].strokeColor = colors.HexColor("#10b981")
    lc.lines[0].strokeWidth = 2
    lc.lines[0].symbol = None
    d.add(lc)
    d.add(String(60, 18, "Jun 24, 2026: THE CHOSEN ONE ARRIVES (1 paying customer).", fontName="Times-Italic", fontSize=7, textAnchor="start"))
    return d


def chart_cash_allocation() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 5 — Cash & Equivalents by Location", w)
    pie = Pie()
    pie.x = 130
    pie.y = 25
    pie.width = 120
    pie.height = 120
    pie.data = [ENDING_CASH, max(PAYOUTS, 0.01) if PAYOUTS == 0 else PAYOUTS]
    if PAYOUTS == 0:
        pie.data = [ENDING_CASH, 0.01]
        pie.labels = ["Stripe balance", "Bank (payouts pending)"]
        pie.slices[1].fillColor = colors.HexColor("#27272a")
    else:
        pie.labels = ["Stripe balance", "Bank account"]
    pie.slices[0].fillColor = colors.HexColor("#3b83f6")
    pie.slices.strokeWidth = 0.5
    d.add(pie)
    d.add(String(290, 100, f"Stripe: {money(ENDING_CASH)}", fontName="Times-Roman", fontSize=9, textAnchor="start"))
    d.add(String(290, 84, f"Paid out: {money(PAYOUTS)}", fontName="Times-Roman", fontSize=9, textAnchor="start"))
    return d


def chart_meme_arr() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 6 — GAAP Revenue vs Non-GAAP Meme-Adjusted ARR", w)
    bc = HorizontalBarChart()
    bc.x = 140
    bc.y = 45
    bc.height = 100
    bc.width = 280
    actual_arr = GROSS_REVENUE
    meme_arr = GROSS_REVENUE * 12
    bc.data = [[actual_arr, meme_arr]]
    bc.categoryAxis.categoryNames = ["Actual YTD revenue", "Meme-adjusted ARR (×12)"]
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 750
    bc.valueAxis.valueStep = 150
    bc.bars[0].fillColor = colors.HexColor("#10b981")
    bc.bars[1].fillColor = colors.HexColor("#a855f7")
    d.add(bc)
    d.add(String(140, 22, "Non-GAAP measure. Not comparable to companies with customers.", fontName="Times-Italic", fontSize=7, textAnchor="start"))
    return d


def chart_stripe_fee_pct() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 7 — Stripe Take Rate vs Industry SaaS Benchmarks*", w)
    bc = VerticalBarChart()
    bc.x = 55
    bc.y = 35
    bc.height = 145
    bc.width = 370
    our_rate = (TOTAL_FEES / GROSS_REVENUE) * 100
    bc.data = [[our_rate, 2.9, 30, 70]]
    bc.categoryAxis.categoryNames = ["Half\nRadiation", "Typical\nproc. fee", "Typical\nSaaS COGS", "MIDI-OX\n(emotional)"]
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 80
    bc.valueAxis.valueStep = 10
    bc.bars[0].fillColor = colors.HexColor("#3b83f6")
    for i in range(1, 4):
        bc.bars[i].fillColor = colors.HexColor("#52525b")
    bc.barLabelFormat = "%0.1f"
    d.add(bc)
    d.add(String(55, 18, "*MIDI-OX benchmark estimated from therapy bills. Proc. fee = illustrative.", fontName="Times-Italic", fontSize=7, textAnchor="start"))
    return d


def chart_parser_ship_velocity() -> Drawing:
    w, h = 460, 220
    d = Drawing(w, h)
    _chart_title(d, "FIGURE 8 — SysEx Parsers in Production (Count)", w)
    bc = VerticalBarChart()
    bc.x = 55
    bc.y = 35
    bc.height = 145
    bc.width = 370
    bc.data = [[0, 0, 0, 0, 6]]
    bc.categoryAxis.categoryNames = ["2022", "2023", "2024", "2025", "Jun 2026"]
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 8
    bc.valueAxis.valueStep = 2
    for i in range(5):
        bc.bars[i].fillColor = colors.HexColor("#52525b" if i < 4 else "#10b981")
    d.add(bc)
    d.add(String(55, 18, "DX7, Juno-106, M1, Jupiter-6, CZ-101, Generic scan.", fontName="Times-Italic", fontSize=7, textAnchor="start"))
    return d


def charts_exhibit(story, s):
    story.append(Paragraph("EXHIBIT 99.5 — MANAGEMENT CHARTS &amp; GRAPHICAL SUPPLEMENTS", s["h1"]))
    story.append(Paragraph(
        "The following figures are unaudited, generated programmatically, and certified visually acceptable by Absolutely Nobody LLP. "
        "All dollar figures tie to the Stripe Balance Summary unless labeled Non-GAAP or Meme-adjusted.",
        s["body"],
    ))
    story.append(Spacer(1, 8))
    for chart_fn in (
        chart_revenue_waterfall,
        chart_fee_pie,
        chart_five_year_hockey_stick,
        chart_customer_growth,
        chart_cash_allocation,
        chart_meme_arr,
        chart_stripe_fee_pct,
        chart_parser_ship_velocity,
    ):
        story.append(chart_fn())
        story.append(Spacer(1, 14))
    story.append(PageBreak())


def cover(story, s):
    story.append(Spacer(1, 1.2 * inch))
    story.append(Paragraph("UNITED STATES", s["cover_sub"]))
    story.append(Paragraph("SECURITIES AND EXCHANGE COMMISSION", s["cover_sub"]))
    story.append(Paragraph("Washington, D.C. 20549", s["cover_sub"]))
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph("FORM 10-K", s["cover_title"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("(Mark One)", s["cover_sub"]))
    story.append(Paragraph("☒ ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934", s["cover_sub"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        f"For the fiscal period from {PERIOD_START.strftime('%B %d, %Y')} to {PERIOD_END.strftime('%B %d, %Y')}",
        s["cover_sub"],
    ))
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph("HALF RADIATION LLC", s["cover_title"]))
    story.append(Paragraph("(Exact name of registrant as specified in its charter)", s["small"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("New Mexico Limited Liability Company", s["cover_sub"]))
    story.append(Paragraph("(State or other jurisdiction of incorporation or organization)", s["small"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("7372 — Prepackaged Software / 5734 — Computer & Software Stores", s["cover_sub"]))
    story.append(Paragraph("(Primary Standard Industrial Classification Code Number)", s["small"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Not Applicable — Registrant is not a public company and has no ticker symbol", s["cover_sub"]))
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph(
        "Principal executive offices: c/o knob.monster, Internet, Earth<br/>"
        "vault@knob.monster | halfradiationllc@gmail.com | https://knob.monster",
        s["cover_sub"],
    ))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(
        "Indicate by check mark if the registrant is a well-known seasoned issuer, as defined in Rule 405 of the Securities Act. "
        "☐ Yes ☒ No (Registrant has $57.51 in cash.)",
        s["body"],
    ))
    story.append(Paragraph(
        "Indicate by check mark if the registrant is a large accelerated filer, an accelerated filer, a non-accelerated filer, "
        "a smaller reporting company, or an emerging growth company. See definitions in Exchange Act Rule 12b-2.",
        s["body"],
    ))
    story.append(Paragraph(
        "☐ Large accelerated filer ☐ Accelerated filer ☒ Non-accelerated filer ☒ Smaller reporting company ☒ Emerging growth company",
        s["body"],
    ))
    story.append(Paragraph(
        "If an emerging growth company, indicate by check mark if the registrant has elected not to use the extended transition "
        "period for complying with any new or revised financial accounting standards. ☒ The registrant elects to comply using "
        "a spreadsheet and vibes.",
        s["body"],
    ))
    story.append(PageBreak())


def toc(story, s):
    story.append(Paragraph("TABLE OF CONTENTS", s["h1"]))
    items = [
        ("PART I", ""),
        ("Item 1.", "Business", "4"),
        ("Item 1A.", "Risk Factors", "8"),
        ("Item 1B.", "Unresolved Staff Comments", "14"),
        ("Item 2.", "Properties", "14"),
        ("Item 3.", "Legal Proceedings", "15"),
        ("Item 4.", "Mine Safety Disclosures", "15"),
        ("PART II", ""),
        ("Item 5.", "Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities", "16"),
        ("Item 6.", "[Reserved]", "17"),
        ("Item 7.", "Management's Discussion and Analysis of Financial Condition and Results of Operations", "17"),
        ("Item 7A.", "Quantitative and Qualitative Disclosures About Market Risk", "22"),
        ("Item 8.", "Financial Statements and Supplementary Data", "23"),
        ("Item 9.", "Changes in and Disagreements With Accountants on Accounting and Financial Disclosure", "32"),
        ("Item 9A.", "Controls and Procedures", "32"),
        ("Item 9B.", "Other Information", "33"),
        ("Item 9C.", "Disclosure Regarding Foreign Jurisdictions that Prevent Inspections", "33"),
        ("PART III", ""),
        ("Item 10.", "Directors, Executive Officers and Corporate Governance", "34"),
        ("Item 11.", "Executive Compensation", "35"),
        ("Item 12.", "Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters", "36"),
        ("Item 13.", "Certain Relationships and Related Transactions, and Director Independence", "36"),
        ("Item 14.", "Principal Accountant Fees and Services", "37"),
        ("PART IV", ""),
        ("Item 15.", "Exhibit and Financial Statement Schedules", "38"),
        ("Signatures", "", "40"),
        ("Report of Independent Registered Public Accounting Firm", "", "41"),
    ]
    for row in items:
        if len(row) == 2:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>{row[0]}</b>", s["toc"]))
        else:
            label, title, page = row
            dots = "." * max(4, 60 - len(label) - len(title))
            story.append(Paragraph(f"{label} {title} {dots} {page}", s["toc"]))
    story.append(PageBreak())


def part1_business(story, s):
    story.append(Paragraph("PART I", s["h1"]))
    story.append(Paragraph("ITEM 1. BUSINESS", s["h1"]))
    story.append(Paragraph("<b>Overview</b>", s["h2"]))
    story.append(Paragraph(
        "Half Radiation LLC (the \"Company,\" \"we,\" \"us,\" or \"our\") is a New Mexico limited liability company formed to "
        "operate knob.monster, a browser-native cloud System Exclusive (SysEx) librarian and patch management platform for "
        "vintage synthesizers manufactured primarily in the 1980s and 1990s. The Company's mission is to eliminate legacy desktop "
        "MIDI utilities, obsolete USB drivers, and the existential dread associated with CR2032 battery failure.",
        s["body"],
    ))
    story.append(Paragraph(
        "We commenced commercial operations on May 31, 2026, upon acquisition of the knob.monster domain name for an amount "
        "management describes as \"way too much money\" and deployment of Web MIDI decoders for the Yamaha DX7, Roland Juno-106, "
        "Korg M1, Roland Jupiter-6, and Casio CZ-101.",
        s["body"],
    ))
    story.append(Paragraph("<b>Products and Services</b>", s["h2"]))
    story.append(Paragraph(
        "knob.monster enables users to connect class-compliant USB-to-MIDI interfaces directly to supported web browsers "
        "(Google Chrome, Microsoft Edge, Opera) without installing desktop software. Users may dump, store, search, and restore "
        "patch banks via the Web MIDI API. The Company offers two lifetime license tiers:",
        s["body"],
    ))
    story.append(table([
        ["Plan", "Price (USD)", "License scope", "Commercial use"],
        ["knob.monster+ Personal", "$39.00", "Lifetime", "Non-commercial only"],
        ["knob.monster+ Studio", "$399.00", "Lifetime", "One commercial location"],
    ], col_widths=[1.6 * inch, 1.0 * inch, 1.1 * inch, 1.6 * inch]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Regional pricing is available in EUR, GBP, CAD, and AUD through Stripe price localization. Business email domains "
        "are routed to the Studio tier at checkout pursuant to the Company's license compliance policy.",
        s["body"],
    ))
    story.append(Paragraph("<b>Competition</b>", s["h2"]))
    story.append(Paragraph(
        "Primary competitors include MIDI-OX (Windows, last meaningfully updated circa 2011), Snoize (macOS, discontinued), "
        "SoundQuest/MIDI Quest (hundreds of dollars), and the user's own denial that the internal battery has died. "
        "Management believes the Company's browser-native architecture, dark-mode aesthetic, and willingness to publish this "
        "document constitute differentiated competitive advantages.",
        s["body"],
    ))
    story.append(Paragraph("<b>Customers and Revenue Concentration</b>", s["h2"]))
    story.append(Paragraph(
        f"During the period ended {PERIOD_END.strftime('%B %d, %Y')}, the Company recorded {CHARGES_COUNT} successful charge(s) "
        f"totaling {money(GROSS_REVENUE)} in gross revenue. Customer concentration is extreme: one charge represents 100% of "
        "period revenue. Management celebrates this milestone as proof of concept and notes that ten paying customers would "
        "require discontinuation of the term \"goblinos\" in internal source code.",
        s["body"],
    ))
    story.append(Paragraph("<b>Technology Infrastructure</b>", s["h2"]))
    story.append(Paragraph(
        "The platform is built on FastAPI, PostgreSQL, Stripe, Resend SMTP, PostHog analytics, and Tailwind CSS delivered "
        "via CDN. SysEx parsers are maintained in Python. The Company has not experienced material downtime except during "
        "deployments performed while eating discount instant noodles.",
        s["body"],
    ))
    story.append(Paragraph("<b>Intellectual Property</b>", s["h2"]))
    story.append(Paragraph(
        "The Company owns the knob.monster trademark, logo, pixel-font aesthetic, and proprietary SysEx parsing logic. "
        "The Company does not own the Yamaha DX7, Roland Juno-106, or any deceased firmware engineer's soul.",
        s["body"],
    ))
    story.append(Paragraph("<b>Employees</b>", s["h2"]))
    story.append(Paragraph(
        "As of June 28, 2026, the Company employed one (1) human, zero (0) contractors, and approximately forty-seven (47) "
        "Large Language Models consulted in an advisory capacity without compensation.",
        s["body"],
    ))
    story.append(PageBreak())

    story.append(Paragraph("ITEM 1A. RISK FACTORS", s["h1"]))
    story.append(Paragraph(
        "An investment in Half Radiation LLC is impossible because we have not issued securities. If we had, the following "
        "risks would keep you awake during a tape recall:",
        s["body"],
    ))
    risks = [
        ("CR2032 Battery Risk", "Vintage synthesizer internal batteries die without warning, causing memory loss and emotional damage. Our product mitigates but cannot reverse dead batteries already deceased."),
        ("MIDI-OX Persistence Risk", "MIDI-OX remains installed on Windows XP machines worldwide. Users may continue using free abandonware instead of paying $39."),
        ("Web MIDI Browser Risk", "Apple Safari and Mozilla Firefox do not support Web MIDI. Users on these browsers may believe the product is broken when the browser is."),
        ("Stripe Fee Risk", f"Payment processing fees represented {(TOTAL_FEES/GROSS_REVENUE*100):.1f}% of gross revenue during the period. At current scale, each transaction is materially impacted."),
        ("Single-Customer Risk", "100% revenue concentration in one charge creates going-concern sensitivity to chargebacks, refunds, and the customer's continued ownership of a synthesizer."),
        ("Payout Delay Risk", f"As of period end, {money(PAYOUTS)} had been paid out to the Company's bank account. Cash remains in Stripe balance, subject to platform risk."),
        ("Synth Nerd Market Risk", "Total addressable market is bounded by the intersection of 'owns vintage synth' and 'trusts cloud backup.' Management estimates this is not Coupang."),
        ("Regulatory Risk", "SysEx data is not personally identifiable unless your patch names contain your Social Security number, which we discourage."),
        ("Carbon Neutrality Risk", "The Company claims 100% offset via vintage-analog carbon credits certified by absolutely nobody. This may not satisfy the SEC, the EPA, or your mom."),
        ("AI Hallucination Risk", "FAQ chat may occasionally answer questions using OpenRouter/Gemini. Answers are grounded in FAQ knowledge base but management cannot guarantee the model will not recommend hot-glueing a MIDI port."),
    ]
    for title, text in risks:
        story.append(Paragraph(f"<b>{title}.</b> {text}", s["body"]))
    story.append(PageBreak())

    story.append(Paragraph("ITEM 1B. UNRESOLVED STAFF COMMENTS", s["h1"]))
    story.append(Paragraph("None. The SEC has not returned our calls.", s["body"]))
    story.append(Paragraph("ITEM 2. PROPERTIES", s["h1"]))
    story.append(Paragraph(
        "The Company leases no physical properties. Principal assets consist of a laptop, one or more USB-to-MIDI cables "
        "(management recommends Roland UM-ONE or iConnectivity mio), and cloud hosting accounts. Fair value of physical "
        "property: immaterial, slightly sticky.",
        s["body"],
    ))
    story.append(Paragraph("ITEM 3. LEGAL PROCEEDINGS", s["h1"]))
    story.append(Paragraph(
        "The Company is not a party to any material legal proceedings. Informal proceedings continue with the user's "
        "synthesizer regarding Write Protect switches.",
        s["body"],
    ))
    story.append(Paragraph("ITEM 4. MINE SAFETY DISCLOSURES", s["h1"]))
    story.append(Paragraph("Not applicable. We mine patches, not coal.", s["body"]))
    story.append(PageBreak())


def part2(story, s):
    story.append(Paragraph("PART II", s["h1"]))
    story.append(Paragraph(
        "ITEM 5. MARKET FOR REGISTRANT'S COMMON EQUITY, RELATED STOCKHOLDER MATTERS AND ISSUER PURCHASES OF EQUITY SECURITIES",
        s["h1"],
    ))
    story.append(Paragraph(
        "There is no public market for membership interests in Half Radiation LLC. The Company has never declared or paid "
        "cash dividends. Management intends to retain all $57.51 of earnings for growth, ramen, and domain renewals.",
        s["body"],
    ))
    story.append(Paragraph("ITEM 6. [RESERVED]", s["h1"]))
    story.append(Paragraph("Reserved for future revenue large enough to require a bar chart.", s["body"]))

    story.append(Paragraph(
        "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS",
        s["h1"],
    ))
    story.append(Paragraph(
        "The following discussion should be read in conjunction with our financial statements and the related notes "
        "thereto included elsewhere in this Annual Report on Form 10-K. This discussion contains forward-looking statements "
        "involving risks, uncertainties, and the phrase \"we will definitely get ten customers.\"",
        s["body"],
    ))
    story.append(Paragraph("<b>Overview of Fiscal Period</b>", s["h2"]))
    story.append(Paragraph(
        f"The Company was founded on {PERIOD_START.strftime('%B %d, %Y')}. This report covers our first partial fiscal "
        f"period through {PERIOD_END.strftime('%B %d, %Y')}. On June 24, 2026, we acquired our first paying customer, "
        "an event internally codenamed \"THE CHOSEN ONE ARRIVES.\"",
        s["body"],
    ))
    story.append(Paragraph("<b>Results of Operations</b>", s["h2"]))
    story.append(Paragraph(
        f"Gross revenue for the period was {money(GROSS_REVENUE)} from {CHARGES_COUNT} charge(s). Total payment processing "
        f"and platform fees were {money(TOTAL_FEES)}, comprising activity fees of {money(STRIPE_FEES_ACTIVITY)}, additional "
        f"Stripe fees of {money(STRIPE_FEES_ADDITIONAL)}, and tax of {money(STRIPE_TAX)}. Net income was {money(NET_INCOME)}, "
        "representing a net margin of 95.9%, which management believes is acceptable for a software company that has not "
        "yet paid for accounting software.",
        s["body"],
    ))
    story.append(table([
        ["Metric", "Amount", "% of Gross"],
        ["Gross charges", money(GROSS_REVENUE), "100.0%"],
        ["Stripe activity fees", f"({money(STRIPE_FEES_ACTIVITY).strip('$')})", f"{STRIPE_FEES_ACTIVITY/GROSS_REVENUE*100:.1f}%"],
        ["Additional Stripe fees", f"({money(STRIPE_FEES_ADDITIONAL).strip('$')})", f"{STRIPE_FEES_ADDITIONAL/GROSS_REVENUE*100:.1f}%"],
        ["Tax", f"({money(STRIPE_TAX).strip('$')})", f"{STRIPE_TAX/GROSS_REVENUE*100:.1f}%"],
        ["Net balance change", money(NET_INCOME), f"{NET_INCOME/GROSS_REVENUE*100:.1f}%"],
    ], col_widths=[2.4 * inch, 1.3 * inch, 1.3 * inch]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Liquidity and Capital Resources</b>", s["h2"]))
    story.append(Paragraph(
        f"Cash held in Stripe balance at period end: {money(ENDING_CASH)}. Total payouts to bank accounts: {money(PAYOUTS)}. "
        "The Company believes current liquidity is sufficient to fund operations for approximately 1.4 Roland UM-ONE MIDI "
        "interfaces or two months of basic hosting, whichever comes first.",
        s["body"],
    ))
    story.append(Paragraph("<b>Critical Accounting Estimates</b>", s["h2"]))
    story.append(Paragraph(
        "Revenue is recognized upon successful Stripe checkout. Lifetime licenses are recognized in full at point of sale "
        "because management has not read ASC 606 and hopes lifetime means lifetime.",
        s["body"],
    ))
    story.append(Paragraph("<b>Non-GAAP Financial Measures</b>", s["h2"]))
    story.append(Paragraph(
        "Management tracks Adjusted EBITDA by adding back Stripe fees, domain regret, and emotional damage from reading "
        "Gearspace threads. Adjusted EBITDA for the period approximates gross revenue.",
        s["body"],
    ))
    story.append(PageBreak())

    story.append(Paragraph("ITEM 7A. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK", s["h1"]))
    story.append(Paragraph(
        "<b>Interest Rate Risk.</b> Immaterial. Cash earns zero interest in Stripe balance.",
        s["body"],
    ))
    story.append(Paragraph(
        "<b>Foreign Currency Risk.</b> The Company offers EUR, GBP, CAD, and AUD pricing. Exposure is limited because "
        "period revenue was 100% USD.",
        s["body"],
    ))
    story.append(Paragraph(
        "<b>SysEx Transmission Risk.</b> Buffer overflow on 8-bit synth CPUs may corrupt dumps. The Company throttles "
        "transmission with 60ms pauses. Qualitative assessment: better than MIDI-OX defaults.",
        s["body"],
    ))
    story.append(PageBreak())

    story.append(Paragraph("ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA", s["h1"]))
    story.append(Paragraph("INDEX TO FINANCIAL STATEMENTS", s["center"]))
    story.append(table([
        ["", "Page"],
        ["Report of Independent Registered Public Accounting Firm", "41"],
        ["Balance Sheets as of June 28, 2026", "42"],
        ["Statements of Operations for the Period May 31 – June 28, 2026", "43"],
        ["Statements of Cash Flows for the Period May 31 – June 28, 2026", "44"],
        ["Statements of Member's Equity for the Period May 31 – June 28, 2026", "45"],
        ["Notes to Financial Statements", "46"],
    ], col_widths=[4.8 * inch, 0.8 * inch], header_rows=0))
    story.append(PageBreak())

    # Balance Sheet
    story.append(Paragraph("HALF RADIATION LLC", s["center"]))
    story.append(Paragraph("BALANCE SHEETS", s["center"]))
    story.append(Paragraph("(Unaudited — but the Stripe numbers are real)", s["center"]))
    story.append(Paragraph(f"As of {PERIOD_END.strftime('%B %d, %Y')}", s["center"]))
    story.append(Spacer(1, 12))
    story.append(table([
        ["", "June 28, 2026"],
        ["ASSETS", ""],
        ["Current assets:", ""],
        ["  Cash — Stripe balance", money(ENDING_CASH)],
        ["  Accounts receivable", "$0.00"],
        ["  CR2032 batteries on hand", "$0.00"],
        ["Total current assets", money(ENDING_CASH)],
        ["Property and equipment, net", "$0.00"],
        ["Intangible assets (domain, parsers, vibes)", "Immaterial"],
        ["TOTAL ASSETS", money(ENDING_CASH)],
        ["", ""],
        ["LIABILITIES AND MEMBER'S EQUITY", ""],
        ["Current liabilities:", ""],
        ["  Accounts payable", "$0.00"],
        ["  Accrued Stripe fees payable", "$0.00"],
        ["  Deferred revenue (lifetime licenses, Note 3)", money(GROSS_REVENUE)],
        ["Total liabilities", money(GROSS_REVENUE)],
        ["", ""],
        ["Member's equity:", ""],
        ["  Accumulated deficit", money(NET_INCOME - GROSS_REVENUE)],
        ["Total member's equity", money(NET_INCOME - GROSS_REVENUE)],
        ["TOTAL LIABILITIES AND MEMBER'S EQUITY", money(ENDING_CASH)],
    ], col_widths=[4.2 * inch, 1.4 * inch], header_rows=0))
    story.append(Spacer(1, 8))
    story.append(Paragraph("See accompanying notes to financial statements.", s["small"]))
    story.append(PageBreak())

    # Income Statement
    story.append(Paragraph("HALF RADIATION LLC", s["center"]))
    story.append(Paragraph("STATEMENTS OF OPERATIONS", s["center"]))
    story.append(Paragraph(f"For the Period {PERIOD_START.strftime('%B %d, %Y')} to {PERIOD_END.strftime('%B %d, %Y')}", s["center"]))
    story.append(Spacer(1, 12))
    story.append(table([
        ["", "Amount"],
        ["REVENUE", ""],
        ["  Lifetime license revenue (Stripe charges)", money(GROSS_REVENUE)],
        ["Total revenue", money(GROSS_REVENUE)],
        ["", ""],
        ["COST OF REVENUE", ""],
        ["  Payment processing fees", money(TOTAL_FEES)],
        ["Total cost of revenue", money(TOTAL_FEES)],
        ["", ""],
        ["GROSS PROFIT", money(GROSS_REVENUE - TOTAL_FEES)],
        ["", ""],
        ["OPERATING EXPENSES", ""],
        ["  Research and development", "$0.00"],
        ["  Sales and marketing", "$0.00"],
        ["  General and administrative", "$0.00"],
        ["  Carbon neutrality offsets (certified by nobody)", "$0.00"],
        ["Total operating expenses", "$0.00"],
        ["", ""],
        ["OPERATING INCOME", money(NET_INCOME)],
        ["Interest income", "$0.00"],
        ["Interest expense", "$0.00"],
        ["NET INCOME", money(NET_INCOME)],
        ["", ""],
        ["Net income per membership unit (basic and diluted)", money(NET_INCOME)],
        ["Membership units outstanding", "1"],
    ], col_widths=[4.2 * inch, 1.4 * inch], header_rows=0))
    story.append(PageBreak())

    # Cash Flow
    story.append(Paragraph("HALF RADIATION LLC", s["center"]))
    story.append(Paragraph("STATEMENTS OF CASH FLOWS", s["center"]))
    story.append(Spacer(1, 12))
    story.append(table([
        ["", "Amount"],
        ["CASH FLOWS FROM OPERATING ACTIVITIES", ""],
        ["Net income", money(NET_INCOME)],
        ["Adjustments:", ""],
        ["  Deferred revenue", money(GROSS_REVENUE)],
        ["  Changes in working capital", "$0.00"],
        ["Net cash provided by operating activities", money(NET_INCOME)],
        ["", ""],
        ["CASH FLOWS FROM INVESTING ACTIVITIES", ""],
        ["Purchase of domain name", "Immaterial"],
        ["Net cash used in investing activities", "$0.00"],
        ["", ""],
        ["CASH FLOWS FROM FINANCING ACTIVITIES", ""],
        ["Member contributions", "$0.00"],
        ["Distributions / payouts to bank", money(PAYOUTS)],
        ["Net cash used in financing activities", money(PAYOUTS)],
        ["", ""],
        ["Net increase in cash", money(NET_INCOME)],
        ["Cash at beginning of period", money(STARTING_CASH)],
        ["Cash at end of period (Stripe balance)", money(ENDING_CASH)],
    ], col_widths=[4.2 * inch, 1.4 * inch], header_rows=0))
    story.append(PageBreak())

    # Member equity
    story.append(Paragraph("HALF RADIATION LLC", s["center"]))
    story.append(Paragraph("STATEMENTS OF MEMBER'S EQUITY", s["center"]))
    story.append(Spacer(1, 12))
    story.append(table([
        ["", "Member capital", "Retained earnings", "Total"],
        ["Balance, May 31, 2026", "$0.00", "$0.00", "$0.00"],
        ["Net income", "—", money(NET_INCOME), money(NET_INCOME)],
        ["Balance, June 28, 2026", "$0.00", money(NET_INCOME), money(NET_INCOME)],
    ], col_widths=[2.0 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch]))
    story.append(PageBreak())

    # Notes
    story.append(Paragraph("NOTES TO FINANCIAL STATEMENTS", s["h1"]))
    notes = [
        ("Note 1 — Organization and Basis of Presentation",
         "Half Radiation LLC was organized as a New Mexico LLC. These financial statements are prepared on an accrual basis "
         "using US GAAP as understood by a solo founder who watched one YouTube video about accounting."),
        ("Note 2 — Summary of Significant Accounting Policies",
         "Revenue recognition: upon Stripe payment success. Lifetime licenses: no expiration modeled. SysEx blobs: stored as hex in PostgreSQL."),
        ("Note 3 — Revenue Disaggregation",
         f"During the period, all {money(GROSS_REVENUE)} of revenue originated from Stripe charges in the reporting window June 1–28, 2026."),
        ("Note 4 — Stripe Balance Reconciliation",
         f"Per Stripe Balance Summary: starting balance {money(STARTING_CASH)}; account activity before fees {money(GROSS_REVENUE)}; "
         f"fees {money(-TOTAL_FEES)}; net balance change {money(NET_INCOME)}; payouts {money(PAYOUTS)}; ending balance {money(ENDING_CASH)}."),
        ("Note 5 — Income Taxes",
         "The Company has not computed provision for income taxes in these statements. Consult a cross-border CPA. We beg you."),
        ("Note 6 — Subsequent Events",
         "Management is aware of additional customer activity after period end, including transactions occurring on or about June 29, 2026, "
         "outside this reporting window. Such events are not adjusted herein."),
        ("Note 7 — Going Concern",
         "Management believes going concern is appropriate because $57.51 exceeds the cost of zero and the product works on a Juno-106 when cables are correct."),
        ("Note 8 — Concentration of Credit Risk",
         "Financial instruments that potentially subject the Company to credit risk consist principally of cash held at Stripe. "
         "The Company has no diversification strategy because diversification requires multiple customers."),
        ("Note 9 — Commitments and Contingencies",
         "The Company leases no facilities. Commitments include annual domain renewal, cloud hosting, Resend SMTP, PostHog, "
         "and OpenRouter API usage for FAQ chat. Total committed future spend: management has not calculated and prefers not to."),
        ("Note 10 — Fair Value Measurements",
         "Cash is carried at Stripe balance fair value (Level 1: observable in dashboard). SysEx hex strings are Level 3 "
         "unobservable inputs unless you can hear the difference."),
        ("Note 11 — Related Party Transactions",
         "The sole member may use the product without charge. No formal transfer pricing policy exists."),
        ("Note 12 — Segment Information",
         "The Company operates as one reportable segment: Browser-Native Vintage Synth Cloud Librarian. "
         "Geographic revenue: 100% USD in period. Synth geographic revenue: unknown until user selects synth model."),
        ("Note 13 — Stock-Based Compensation",
         "None. Compensation is existential."),
        ("Note 14 — Earnings Per Unit",
         f"Basic and diluted net income per membership unit: {money(NET_INCOME)}. Weighted average units: 1."),
        ("Note 15 — Recently Issued Accounting Pronouncements",
         "Management has not adopted any new FASB standards because management has not read any new FASB standards."),
    ]
    for title, text in notes:
        story.append(Paragraph(f"<b>{title}</b>", s["h2"]))
        story.append(Paragraph(text, s["body"]))
    story.append(PageBreak())

    story.append(Paragraph("ITEM 9. CHANGES IN AND DISAGREEMENTS WITH ACCOUNTANTS ON ACCOUNTING AND FINANCIAL DISCLOSURE", s["h1"]))
    story.append(Paragraph("None. Absolutely Nobody LLP has served since inception.", s["body"]))
    story.append(Paragraph("ITEM 9A. CONTROLS AND PROCEDURES", s["h1"]))
    story.append(Paragraph(
        "Disclosure controls: PostHog, Discord webhooks, and reading Stripe email alerts. Internal control over financial "
        "reporting: a Google Sheet that may or may not exist. Management concluded controls are effective because nobody "
        "has stolen $57.51 yet.",
        s["body"],
    ))
    story.append(Paragraph("ITEM 9B. OTHER INFORMATION", s["h1"]))
    story.append(Paragraph("None required under Rule 14a-12, unless you count this entire filing.", s["body"]))
    story.append(Paragraph("ITEM 9C. DISCLOSURE REGARDING FOREIGN JURISDICTIONS THAT PREVENT INSPECTIONS", s["h1"]))
    story.append(Paragraph("Not applicable. Our foreign jurisdiction is the cloud.", s["body"]))
    story.append(PageBreak())


def ceo_letter_and_supplements(story, s):
    story.append(Paragraph("LETTER TO STAKEHOLDERS", s["h1"]))
    story.append(Paragraph("(Not required by the SEC. Included because we have the PDF open.)", s["small"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Dear Person Who Owns a Juno-106,", s["body_left"]))
    paragraphs = [
        f"When we incorporated Half Radiation LLC on {PERIOD_START.strftime('%B %d, %Y')}, we did not anticipate filing a Form 10-K "
        f"twenty-nine days later. Yet here we are, reporting {money(NET_INCOME)} in net income and one (1) charge in Stripe.",
        "Our thesis remains unchanged: vintage synthesizers outlive their backup utilities. MIDI-OX runs on operating systems "
        "that should be in museums. Snoize is a memory. Your patches should live in the cloud, not on a floppy disk labeled "
        "FINAL_FINAL_v3.",
        "Operationally, we shipped Web MIDI ingestion, dual lifetime pricing, regional EUR/GBP/CAD/AUD checkout, FAQ chat, "
        "business-email Studio routing, and two demo videos that do not morph cables mid-loop. We removed fake live counters "
        "because honesty is a competitive advantage when your revenue fits in a tweet.",
        f"Financially, gross revenue was {money(GROSS_REVENUE)}. Stripe took {money(TOTAL_FEES)}. We retained {money(NET_INCOME)} "
        f"in platform balance and paid out {money(PAYOUTS)} to a bank account, because moving money is the second-hardest part "
        "of running a company after parsing Casio CZ nibbles.",
        "Looking ahead, we will not project hockey sticks. We will backup patches, answer Gearspace threads, and pursue ten "
        "paying customers so we can stop eating discount instant noodles. If you are reading this and you own a DX7, please "
        "consider knob.monster+. If you are the SEC, this is satire.",
        "Sincerely,",
    ]
    for p in paragraphs:
        story.append(Paragraph(p, s["body"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Chief Knob Officer", s["body_left"]))
    story.append(Paragraph("Half Radiation LLC", s["body_left"]))
    story.append(PageBreak())

    story.append(Paragraph("SELECTED FINANCIAL DATA (UNAUDITED)", s["h1"]))
    story.append(Paragraph("Five-Year Summary — Half Radiation LLC", s["h2"]))
    story.append(table([
        ["Fiscal Year", "2022", "2023", "2024", "2025", "2026 (partial)"],
        ["Gross revenue", "$0", "$0", "$0", "$0", money(GROSS_REVENUE)],
        ["Net income", "$0", "$0", "$0", "$0", money(NET_INCOME)],
        ["Cash at year-end", "$0", "$0", "$0", "$0", money(ENDING_CASH)],
        ["Paying customers (approx.)", "0", "0", "0", "0", "1+"],
        ["SysEx parsers shipped", "0", "0", "0", "0", "5+"],
        ["Form 10-K filings", "0", "0", "0", "0", "1"],
    ], col_widths=[1.35 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch, 1.0 * inch]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Quarterly Results (2026)", s["h2"]))
    story.append(table([
        ["Quarter", "Gross revenue", "Net income", "Charges"],
        ["Q2 2026 (May 31 – Jun 28)", money(GROSS_REVENUE), money(NET_INCOME), str(CHARGES_COUNT)],
        ["Q1 2026", "$0.00", "$0.00", "0"],
    ], col_widths=[2.0 * inch, 1.3 * inch, 1.3 * inch, 0.8 * inch]))
    charts_exhibit(story, s)
    story.append(PageBreak())

    story.append(Paragraph("SCHEDULE I — STRIPE BALANCE RECONCILIATION", s["h1"]))
    story.append(Paragraph(
        f"Source: Stripe Dashboard, Balance Summary, date range June 1, 2026 through "
        f"June 28, 2026. Daily data available through June 28 per Stripe UI.",
        s["body"],
    ))
    story.append(table([
        ["Line item", "Amount (USD)"],
        ["Starting balance, Jun 1", money(STARTING_CASH)],
        ["Account activity before fees", money(GROSS_REVENUE)],
        ["Fees (total per balance summary)", money(-TOTAL_FEES)],
        ["  — Activity fees component", money(-STRIPE_FEES_ACTIVITY)],
        ["  — Additional Stripe fees", money(-STRIPE_FEES_ADDITIONAL)],
        ["  — Tax component", money(-STRIPE_TAX)],
        ["Net balance change from activity", money(NET_INCOME)],
        ["Total payouts", money(PAYOUTS)],
        ["Ending balance, Jun 28", money(ENDING_CASH)],
    ], col_widths=[3.8 * inch, 1.8 * inch]))
    story.append(Spacer(1, 10))
    story.append(table([
        ["Balance change detail", "Amount (USD)"],
        ["Charges (count)", f"{money(GROSS_REVENUE)} ({CHARGES_COUNT})"],
        ["Fees", money(-STRIPE_FEES_ACTIVITY)],
        ["Refunds (count)", "$0.00 (0)"],
        ["Additional Stripe fees (count)", f"{money(-STRIPE_FEES_ADDITIONAL)} (1)"],
        ["Tax", money(-STRIPE_TAX)],
        ["Net balance change from activity", money(NET_INCOME)],
    ], col_widths=[3.8 * inch, 1.8 * inch]))
    story.append(PageBreak())

    story.append(Paragraph("SCHEDULE II — REVENUE BY PRODUCT LINE", s["h1"]))
    story.append(table([
        ["Product / SKU", "Gross", "Share of revenue"],
        ["knob.monster+ Personal ($39 list)", "See Note 3", "TBD"],
        ["knob.monster+ Studio ($399 list)", "See Note 3", "TBD"],
        ["Legacy subscription (deprecated)", "$0.00", "0%"],
        ["Monster Shop merchandise (pre-order)", "$0.00", "0%"],
        ["Total per Stripe charges", money(GROSS_REVENUE), "100%"],
    ], col_widths=[2.5 * inch, 1.2 * inch, 1.5 * inch]))
    story.append(Paragraph(
        "Note: Stripe reports aggregate charge amount for the period. SKU-level attribution requires checkout metadata "
        "review. Management believes the single charge relates to a lifetime license.",
        s["small"],
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph("SCHEDULE III — SUPPORTED SYNTH PLATFORMS (OPERATIONAL METRICS)", s["h1"]))
    story.append(table([
        ["Platform", "Parser status", "SEO landing page"],
        ["Yamaha DX7 / TX family", "Production", "Yes"],
        ["Roland Juno-106", "Production", "Yes"],
        ["Korg M1", "Production", "Yes"],
        ["Roland Jupiter-6", "Production", "Yes"],
        ["Casio CZ-101", "Production", "Yes"],
        ["Generic ASCII scan", "Production", "Yes"],
        ["Line 6 POD 2.0 (pedal.monster)", "Not started", "No"],
    ], col_widths=[1.8 * inch, 1.5 * inch, 1.3 * inch]))
    story.append(PageBreak())

    story.append(Paragraph("SUPPLEMENTAL DISCLOSURES — NON-GAAP RECONCILIATION", s["h1"]))
    story.append(table([
        ["Measure", "Amount"],
        ["Net income (GAAP)", money(NET_INCOME)],
        ["Add: Stripe fees", money(TOTAL_FEES)],
        ["Add: Domain regret (non-cash)", "Not quantified"],
        ["Add: Carbon offsets (certified by nobody)", "$0.00"],
        ["Adjusted EBITDA (Non-GAAP)", money(GROSS_REVENUE)],
        ["Meme-adjusted ARR", money(GROSS_REVENUE * 12)],
        ["Fully diluted goblinos outstanding", "0"],
    ], col_widths=[3.5 * inch, 2.1 * inch]))
    story.append(Paragraph(
        "Non-GAAP measures are not prepared under GAAP and should not be compared to companies that have revenue.",
        s["small"],
    ))
    story.append(PageBreak())


def part3(story, s):
    story.append(Paragraph("PART III", s["h1"]))
    story.append(Paragraph("ITEM 10. DIRECTORS, EXECUTIVE OFFICERS AND CORPORATE GOVERNANCE", s["h1"]))
    story.append(table([
        ["Name", "Age", "Position"],
        ["Sole Member / CEO / CTO / Support", "Redacted", "Chief Knob Officer"],
        ["Claude, GPT, Gemini, and associates", "N/A", "Unpaid advisory council"],
    ], col_widths=[2.2 * inch, 0.8 * inch, 2.6 * inch]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "There is no board of directors. Corporate governance consists of arguing with oneself in a Git commit message.",
        s["body"],
    ))
    story.append(Paragraph("ITEM 11. EXECUTIVE COMPENSATION", s["h1"]))
    story.append(Paragraph(
        f"The sole member received $0 in salary during the period. Total compensation: {money(NET_INCOME)} in retained "
        "earnings, one (1) lifetime knob.monster license, and unlimited SysEx dumps.",
        s["body"],
    ))
    story.append(Paragraph(
        "ITEM 12. SECURITY OWNERSHIP OF CERTAIN BENEFICIAL OWNERS AND MANAGEMENT AND RELATED STOCKHOLDER MATTERS",
        s["h1"],
    ))
    story.append(Paragraph("100% owned by the sole member. No equity compensation plans. No stock options. No cap table on Carta.", s["body"]))
    story.append(Paragraph("ITEM 13. CERTAIN RELATIONSHIPS AND RELATED TRANSACTIONS, AND DIRECTOR INDEPENDENCE", s["h1"]))
    story.append(Paragraph(
        "The CEO is not independent of management. Related party transactions include the CEO purchasing their own product "
        "potentially at employee discount (not yet implemented).",
        s["body"],
    ))
    story.append(Paragraph("ITEM 14. PRINCIPAL ACCOUNTANT FEES AND SERVICES", s["h1"]))
    story.append(table([
        ["Service", "Fee"],
        ["Audit fees — Absolutely Nobody LLP", "$0.00"],
        ["Tax fees", "$0.00"],
        ["All other fees (Stripe, domains, hosting)", "Not separately tracked"],
    ], col_widths=[3.5 * inch, 2.1 * inch]))
    story.append(PageBreak())


def part4_and_signatures(story, s):
    story.append(Paragraph("PART IV", s["h1"]))
    story.append(Paragraph("ITEM 15. EXHIBIT AND FINANCIAL STATEMENT SCHEDULES", s["h1"]))
    story.append(table([
        ["Exhibit", "Description"],
        ["31.1", "Certification of CEO pursuant to Rule 13a-14(a) (self-certified)"],
        ["32.1", "Certification pursuant to 18 U.S.C. Section 1350 (vibes-based)"],
        ["99.1", "Stripe Balance Summary export, June 1–28, 2026"],
        ["99.2", "knob.monster Terms of Service"],
        ["99.3", "Gearspace testimonial from bgood (real)"],
        ["99.4", "This PDF"],
        ["99.5", "Management Charts & Graphical Supplements (8 figures)"],
    ], col_widths=[0.9 * inch, 4.7 * inch]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("SIGNATURES", s["h1"]))
    story.append(Paragraph(
        "Pursuant to the requirements of Section 13 or 15(d) of the Securities Exchange Act of 1934, the registrant has "
        "duly caused this report to be signed on its behalf by the undersigned, thereunto duly authorized.",
        s["body"],
    ))
    story.append(Spacer(1, 24))
    story.append(Paragraph("HALF RADIATION LLC", s["body_left"]))
    story.append(Paragraph("By:", s["body_left"]))
    today = date.today().strftime("%B %d, %Y")
    for block in signature_block(
        "Knob Radiation",
        "Sole Member and Chief Knob Officer",
        s,
        sig_date=today,
    ):
        story.append(block)
    story.append(PageBreak())

    story.append(Paragraph("EXHIBIT 31.1 — CEO CERTIFICATION", s["h1"]))
    story.append(Paragraph(
        "I, Knob Radiation, Chief Knob Officer of Half Radiation LLC, certify that: (1) I have not read this report; "
        "(2) to my knowledge it contains real Stripe numbers; (3) I have no idea what Item 9C means; and (4) the Juno-106 "
        "backup feature works when MIDI Out goes to MIDI In.",
        s["body"],
    ))
    for block in signature_block("Knob Radiation", "Chief Knob Officer", s, sig_date=today):
        story.append(block)
    story.append(PageBreak())

    story.append(Paragraph("REPORT OF INDEPENDENT REGISTERED PUBLIC ACCOUNTING FIRM", s["h1"]))
    story.append(Paragraph("To the Sole Member of Half Radiation LLC:", s["body_left"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Opinion Disclaimer</b>", s["h2"]))
    story.append(Paragraph(
        "We are Absolutely Nobody LLP, an imaginary firm of independent registered public accountants. We have not audited "
        "anything. We reviewed the Stripe dashboard screenshot and concluded the numbers look Stripe-shaped.",
        s["body"],
    ))
    story.append(Paragraph(
        f"In our opinion, based on nothing resembling generally accepted auditing standards, the financial statements present "
        f"fairly, in all material respects, the financial position of Half Radiation LLC as of {PERIOD_END.strftime('%B %d, %Y')}, "
        f"and its results of operations and cash flows for the period then ended, assuming Stripe is telling the truth.",
        s["body"],
    ))
    story.append(Spacer(1, 24))
    for block in signature_block(
        "Absolutely Nobody",
        "Partner Emeritus, Absolutely Nobody LLP",
        s,
        sig_date=today,
    ):
        story.append(block)
    story.append(Paragraph("New Mexico, Earth", s["body_left"]))
    story.append(PageBreak())
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<i>This Form 10-K is a satirical transparency document published by Half Radiation LLC. "
        "It is not filed with the SEC. Financial figures sourced from Stripe Balance Summary unless noted. "
        "Do not use for investment decisions. Do use for backing up your Juno-106.</i>",
        s["small"],
    ))


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.drawCentredString(letter[0] / 2, 0.45 * inch, f"Half Radiation LLC — Form 10-K — Page {doc.page}")
    canvas.drawString(0.75 * inch, 0.45 * inch, "Fiscal period ended June 28, 2026")
    canvas.restoreState()


def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Half Radiation LLC Form 10-K FY2026",
        author="Half Radiation LLC",
    )
    styles = build_styles()
    register_signature_font()
    story = []
    cover(story, styles)
    toc(story, styles)
    part1_business(story, styles)
    part2(story, styles)
    ceo_letter_and_supplements(story, styles)
    part3(story, styles)
    part4_and_signatures(story, styles)
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"Generated: {OUTPUT}")
    print(f"Pages: {doc.page}")


if __name__ == "__main__":
    main()
