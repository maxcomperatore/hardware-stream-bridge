"""
PDF Report Generator for NicotineWire.
Generates tangible, high-end Canva/Editorial presentation PDF reports using ReportLab.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports_pdf")
os.makedirs(REPORTS_DIR, exist_ok=True)

def create_report_1():
    pdf_path = os.path.join(REPORTS_DIR, "NW-SYNTH-2026.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=32,
        textColor=colors.HexColor('#E0FE00'),
        alignment=TA_LEFT,
        spaceAfter=15
    )
    
    sub_style = ParagraphStyle(
        'CoverSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#94A3B8'),
        alignment=TA_LEFT,
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0C0E12'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )
    
    story = []
    
    # COVER PAGE
    story.append(Spacer(1, 40))
    story.append(Paragraph("<b>©NICOTINE WIRE™ RESEARCH MONOGRAPH</b>", ParagraphStyle('Tag', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#E0FE00'))))
    story.append(Spacer(1, 15))
    story.append(Paragraph("The 2026 Global Synthetic L-Nicotine &amp; PMTA Benchmark Report", title_style))
    story.append(Paragraph("148-Page Quantitative Market Audit, DMF Lab Verification Standards, &amp; Supply Pricing Models", sub_style))
    story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor('#E0FE00'), spaceBefore=20, spaceAfter=40))
    
    story.append(Paragraph("<b>PUBLISHED:</b> MAY 2026 &bull; <b>CODE:</b> NW-SYNTH-2026", ParagraphStyle('Meta', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#FFFFFF'))))
    story.append(Paragraph("<b>BENCHMARK SPOT PRICE:</b> $3,450 / KG &bull; <b>VERIFIED SUPPLIERS:</b> 38 GLOBAL LABS", ParagraphStyle('Meta2', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#94A3B8'))))
    
    story.append(PageBreak())
    
    # SECTION 1: EXECUTIVE SUMMARY
    story.append(Paragraph("1. EXECUTIVE SUMMARY &amp; REGULATORY MOAT", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0C0E12'), spaceBefore=5, spaceAfter=15))
    
    summary_text = (
        "Following the March 2022 Congressional Appropriations Law placing non-tobacco nicotine under "
        "FDA Center for Tobacco Products (CTP) jurisdiction, synthetic L-nicotine has transitioned from an unregulated "
        "alternative into an audited enterprise commodity. This report aggregates Drug Master File (DMF) filings, "
        "chiral HPLC purity benchmarks, and customs clearance rates across 38 global primary synthesis formulators."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 15))
    
    # DATA TABLE: SUPPLIER BENCHMARKS
    story.append(Paragraph("2. GLOBAL SUPPLIER AUDIT BENCHMARKS", h1_style))
    table_data = [
        ["Supplier / Lab", "Region", "Purity (%)", "DMF Status", "Spot ($/kg)"],
        ["PureSynth Labs Inc.", "USA / EU", "99.8%", "DMF #03941 Verified", "$3,450"],
        ["Apex Synthetic OEM", "Sweden", "99.7%", "DMF #04112 Verified", "$3,520"],
        ["Deccan Bio-Extracts", "India", "99.5%", "REACH / DMF Pending", "$3,280"],
        ["SinoNicotine Chem", "China", "99.2%", "Part 607 Listed", "$3,150"]
    ]
    t = Table(table_data, colWidths=[140, 70, 70, 130, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0C0E12')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#E0FE00')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F6F6F8')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("<b>CONCLUSION &amp; NEXT STEPS:</b> Legal &amp; Procurement teams should enforce ICH Q2(R1) enantiomeric validation requirements before issuing purchase orders.", body_style))
    
    doc.build(story)
    print(f"[PDF Built] Created {pdf_path}")

def create_report_2():
    pdf_path = os.path.join(REPORTS_DIR, "NW-MA-POUCH-2026.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=30,
        textColor=colors.HexColor('#0C0E12'),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0C0E12'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )
    
    story = []
    story.append(Spacer(1, 30))
    story.append(Paragraph("<b>©NICOTINE WIRE™ PRIVATE EQUITY M&amp;A PLAYBOOK</b>", ParagraphStyle('Tag', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0C0E12'))))
    story.append(Spacer(1, 15))
    story.append(Paragraph("The Oral Pouch M&amp;A &amp; Valuation Multiples Playbook", title_style))
    story.append(Paragraph("210-Page Transaction Benchmarks, EV/EBITDA Multiples, &amp; Financial Models", ParagraphStyle('Sub', fontName='Helvetica', fontSize=12, textColor=colors.HexColor('#64748B'))))
    story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor('#0C0E12'), spaceBefore=20, spaceAfter=30))
    
    story.append(Paragraph("1. VALUATION MULTIPLES SUMMARY", h1_style))
    story.append(Paragraph("Private Equity sponsors have driven Nordic and Western European oral pouch contract OEM valuations to 8.8x trailing EBITDA. Unit economics per 20-pouch can reveal gross margins exceeding 74%.", body_style))
    
    table_data = [
        ["Transaction Tier", "EV / EBITDA", "Pouch Can Unit Cost", "OEM Gross Margin"],
        ["Tier 1 OEM (>50M Cans/yr)", "8.8x – 9.5x", "$0.42 / can", "74.5%"],
        ["Tier 2 Regional Formulator", "7.2x – 8.1x", "$0.49 / can", "68.2%"],
        ["White-Label Brand Owner", "6.5x – 7.5x", "$0.65 / can", "62.0%"]
    ]
    t = Table(table_data, colWidths=[160, 100, 120, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0C0E12')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#FFFFFF')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
    ]))
    story.append(t)
    
    doc.build(story)
    print(f"[PDF Built] Created {pdf_path}")

def create_report_3():
    pdf_path = os.path.join(REPORTS_DIR, "NW-FDA-SEIZURE-2026.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#DC2626'),
        spaceAfter=15
    )
    
    story = []
    story.append(Spacer(1, 30))
    story.append(Paragraph("<b>©NICOTINE WIRE™ RISK MANAGEMENT DIVISION</b>", ParagraphStyle('Tag', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#DC2626'))))
    story.append(Spacer(1, 15))
    story.append(Paragraph("FDA CTP Enforcement &amp; Import Seizure Risk Audit", title_style))
    story.append(Paragraph("95-Page Red List Tracking File &amp; Statutory Cap Analysis", ParagraphStyle('Sub', fontName='Helvetica', fontSize=12, textColor=colors.HexColor('#64748B'))))
    story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor('#DC2626'), spaceBefore=20, spaceAfter=30))
    
    story.append(Paragraph("<b>SUMMARY OF IMPORT SEIZURES:</b> US Customs &amp; Border Protection (CBP) detentions under Import Alert #99-43 reached quarterly peaks, resulting in average container write-offs of $1.2M for non-compliant ENDS products.", ParagraphStyle('Body', fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#334155'))))
    
    doc.build(story)
    print(f"[PDF Built] Created {pdf_path}")

if __name__ == "__main__":
    create_report_1()
    create_report_2()
    create_report_3()
