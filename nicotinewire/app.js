// NicotineWire™ Stripe Checkout Link Manager

const STRIPE_LINKS = {
    monthly: "https://buy.stripe.com/4gM14o9dj9NEa1tfoM0Ba00",
    quarterly: "https://buy.stripe.com/4gM14o9dj9NEa1tfoM0Ba00", // Default to monthly checkout or custom
    annual: "https://buy.stripe.com/8x27sMdtz0d4gpR5Oc0Ba02",
    report_synth: "https://buy.stripe.com/cNi4gA0GN6Bs1uX1xW0Ba03",
    report_pouch: "https://buy.stripe.com/7sY14o2OV5xo2z1b8w0Ba04",
    report_fda: "https://buy.stripe.com/cNi14ofBH2lc6Ph2C00Ba05",
    vendor_directory: "https://buy.stripe.com/4gM14oblr7Fw8Xp6Sg0Ba07",
    job_listing: "https://buy.stripe.com/dRm00kahn9NEddF6Sg0Ba08"
};

function openPreCheckoutModal(planKey) {
    const targetUrl = STRIPE_LINKS[planKey] || STRIPE_LINKS.annual;
    window.location.href = targetUrl;
}
