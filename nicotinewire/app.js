// NicotineWire™ PDF Delivery & Stripe Integration

const PDF_FILES = {
    'NW-SYNTH-2026': 'reports_pdf/NW-SYNTH-2026.pdf',
    'NW-MA-POUCH-2026': 'reports_pdf/NW-MA-POUCH-2026.pdf',
    'NW-FDA-SEIZURE-2026': 'reports_pdf/NW-FDA-SEIZURE-2026.pdf'
};

const STRIPE_LINKS = {
    monthly: "https://buy.stripe.com/4gM14o9dj9NEa1tfoM0Ba00",
    quarterly: "https://buy.stripe.com/4gM14o9dj9NEa1tfoM0Ba00",
    annual: "https://buy.stripe.com/8x27sMdtz0d4gpR5Oc0Ba02",
    report_synth: "reports_pdf/NW-SYNTH-2026.pdf",
    report_pouch: "reports_pdf/NW-MA-POUCH-2026.pdf",
    report_fda: "reports_pdf/NW-FDA-SEIZURE-2026.pdf",
    vendor_directory: "https://buy.stripe.com/4gM14oblr7Fw8Xp6Sg0Ba07",
    job_listing: "https://buy.stripe.com/dRm00kahn9NEddF6Sg0Ba08"
};

function downloadPdfReport(code) {
    const pdfPath = PDF_FILES[code] || 'reports_pdf/NW-SYNTH-2026.pdf';
    const link = document.createElement('a');
    link.href = pdfPath;
    link.download = code + '.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function openPreCheckoutModal(planKey) {
    const targetUrl = STRIPE_LINKS[planKey] || 'reports_pdf/NW-SYNTH-2026.pdf';
    if (targetUrl.endsWith('.pdf')) {
        downloadPdfReport(planKey.replace('report_', 'NW-').toUpperCase());
    } else {
        window.location.href = targetUrl;
    }
}
