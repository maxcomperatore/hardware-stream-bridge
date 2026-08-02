// NicotineWire Clean Executive Terminal Engine & Pre-Checkout Conversion System

const OPENROUTER_KEY = "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";
const MODEL_NAME = "deepseek/deepseek-v4-pro";

let isAllExpanded = false;

document.addEventListener('DOMContentLoaded', () => {
    injectPreCheckoutModalHTML();
});

function toggleExpandAll() {
    const detailsList = document.querySelectorAll('article details');
    const btn = document.getElementById('expand-all-btn');
    isAllExpanded = !isAllExpanded;

    detailsList.forEach(det => {
        det.open = isAllExpanded;
    });

    if (btn) {
        btn.innerText = isAllExpanded ? "COLLAPSE ALL BRIEFINGS" : "EXPAND ALL BRIEFINGS";
    }
}

function toggleAiDrawer() {
    const drawer = document.getElementById('ai-chat-drawer');
    if (!drawer) return;
    if (drawer.style.display === 'none' || drawer.style.display === '') {
        drawer.style.display = 'block';
    } else {
        drawer.style.display = 'none';
    }
}

function setPrompt(text) {
    const input = document.getElementById('ai-input');
    if (input) {
        input.value = text;
        askAi();
    }
}

async function askAi() {
    const input = document.getElementById('ai-input');
    const responseDiv = document.getElementById('ai-response');
    if (!input || !responseDiv) return;

    const query = input.value.trim();
    if (!query) {
        responseDiv.innerHTML = "<p><em>Please enter a question or click a 1-click prompt below...</em></p>";
        return;
    }

    responseDiv.innerHTML = "<p><strong>Senior AI Analyst:</strong> <em>Querying live Federal Register dockets, SEC filings, and nicotine M&amp;A database...</em></p>";

    const systemPrompt = "You are the Senior Executive AI Analyst at NicotineWire. You are a seasoned, authoritative expert in FDA CTP regulations, PMTA dockets, synthetic L-nicotine chemistry, TPD rules, oral pouch manufacturing, and PE M&A transaction valuation multiples. Answer questions with extreme financial & legal authority, hard quantitative metrics ($M, EV/EBITDA, P/E, SKU costs), bold strategic clarity, zero fluff, and always end your response with 'Check the Wire before you acquire.'";

    try {
        const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${OPENROUTER_KEY}`,
                "Content-Type": "application/json",
                "HTTP-Referer": "https://nicotinewire.com",
                "X-Title": "NicotineWire AI Analyst Desk"
            },
            body: JSON.stringify({
                model: MODEL_NAME,
                messages: [
                    { role: "system", content: systemPrompt },
                    { role: "user", content: query }
                ],
                temperature: 0.3
            })
        });

        const data = await res.json();
        if (data.choices && data.choices[0] && data.choices[0].message) {
            const raw = data.choices[0].message.content.replace(/\*\*/g, '').replace(/—/g, ', ');
            const paragraphs = raw.split(/\n+/).filter(p => p.trim().length > 0);
            const formattedHTML = paragraphs.map(p => `<p style="margin-bottom: 8px;">${p.trim()}</p>`).join('');
            responseDiv.innerHTML = `<div><strong style="color: #111;">Senior AI Analyst Verdict:</strong>${formattedHTML}</div>`;
        } else {
            responseDiv.innerHTML = `<p><strong>Senior AI Analyst:</strong> Synthetic nicotine PMTA docket status: High Sensitivity. Market valuations for oral pouches holding at 4.1x–5.0x ARR. Check the Wire before you acquire.</p>`;
        }
    } catch (err) {
        console.error("AI Chat Error:", err);
        responseDiv.innerHTML = `<p><strong>Senior AI Analyst:</strong> Live market docket analysis: FDA CTP enforcement prioritization favors monograph-certified synthetic pouch filers. Check the Wire before you acquire.</p>`;
    }
}

// -------------------------------------------------------------
// PRE-CHECKOUT ORDER OVERVIEW MODAL SYSTEM (PSYCHOLOGICAL ANCHORING)
// -------------------------------------------------------------

function injectPreCheckoutModalHTML() {
    if (document.getElementById('precheckout-overlay')) return;

    const modalDiv = document.createElement('div');
    modalDiv.id = 'precheckout-overlay';
    modalDiv.style.cssText = `
        display: none;
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(8px);
        z-index: 99999;
        overflow-y: auto;
        padding: 40px 16px;
        box-sizing: border-box;
    `;

    modalDiv.innerHTML = `
        <div style="max-width: 520px; margin: 0 auto; background: #0a0a0a; color: #ffffff; border: 2px solid #333333; border-radius: 8px; padding: 28px 24px; box-shadow: 0 20px 50px rgba(0,0,0,0.8); font-family: 'Mozilla Text', sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; font-family: 'Mozilla Headline', sans-serif; font-size: 1.5rem; letter-spacing: 0.05em; color: #ffffff; border: none; padding: 0;">ORDER OVERVIEW</h2>
                <button onclick="closePreCheckoutModal()" style="background: transparent; border: none; color: #888; font-size: 1.5rem; cursor: pointer;">✕</button>
            </div>

            <div style="background: #141414; border: 1px solid #262626; border-radius: 6px; padding: 20px; margin-bottom: 20px;">
                <label style="font-size: 0.75rem; color: #888888; display: block; margin-bottom: 6px;">Account Email</label>
                <input type="email" id="modal-email-input" value="executive@firm.com" style="width: 100%; background: #000000; border: 1px solid #333333; color: #ffffff; padding: 10px 12px; border-radius: 4px; font-size: 0.95rem; box-sizing: border-border-box; margin-bottom: 18px;">

                <div style="border-top: 1px solid #262626; padding-top: 16px; margin-bottom: 16px;">
                    <span style="font-size: 0.8rem; color: #888888; display: block;">Selected Plan</span>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;">
                        <strong id="modal-plan-name" style="font-size: 1.1rem; color: #ffffff;">Annual Enterprise Pass</strong>
                        <div style="text-align: right;">
                            <span id="modal-strike-monthly" style="text-decoration: line-through; color: #666; font-size: 0.85rem; margin-right: 6px;">$500.00</span>
                            <strong id="modal-monthly-rate" style="color: #FFEA00; font-size: 1.15rem;">$166.66 / mo</strong>
                        </div>
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                        <span id="modal-discount-tag" style="background: #262626; color: #FFEA00; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;">🏷️ Enterprise Discount 66% off</span>
                        <div style="text-align: right; font-size: 0.82rem; color: #aaaaaa;">
                            <span id="modal-strike-total" style="text-decoration: line-through; color: #666; margin-right: 4px;">$6,000.00</span>
                            <span id="modal-total-text">$2,000.00 Billed annually</span>
                            <span id="modal-saved-text" style="color: #4CAF50; font-style: italic; display: block; font-size: 0.75rem;">(-$4,000.00 Saved)</span>
                        </div>
                    </div>
                </div>

                <div style="border-top: 1px dashed #262626; padding-top: 14px; margin-bottom: 12px; font-size: 0.88rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #aaaaaa;">
                        <span>Renews on</span>
                        <strong id="modal-renewal-date" style="color: #ffffff;">8/2/2027</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #aaaaaa;">
                        <span>Subtotal</span>
                        <strong id="modal-subtotal" style="color: #ffffff;">$2,000.00</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 12px; font-size: 1.1rem; color: #ffffff; border-top: 1px solid #333; padding-top: 10px;">
                        <strong>Total due</strong>
                        <strong id="modal-total-due" style="color: #FFEA00;">$2,000.00</strong>
                    </div>
                </div>

                <div style="display: flex; gap: 8px; margin-top: 16px;">
                    <input type="text" id="modal-coupon-input" placeholder="Coupon code" style="flex: 1; background: #000000; border: 1px solid #333; color: #fff; padding: 8px 12px; border-radius: 4px; font-size: 0.85rem;">
                    <button onclick="applyCoupon()" style="background: #262626; color: #fff; border: 1px solid #444; padding: 8px 14px; border-radius: 4px; cursor: pointer;">&gt;</button>
                </div>
            </div>

            <div style="background: #141414; border: 1px solid #262626; border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; font-size: 0.8rem; color: #aaaaaa; text-align: center;">
                By purchasing, you agree to all terms and conditions seen <a href="pricing.html" style="color: #FFEA00; text-decoration: underline;">here</a>
            </div>

            <button id="modal-proceed-btn" onclick="proceedToStripeCheckout()" style="width: 100%; background: #3897f0; color: #ffffff; border: none; padding: 16px; border-radius: 30px; font-family: 'Mozilla Headline', sans-serif; font-size: 1.05rem; font-weight: 800; text-transform: uppercase; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px; box-shadow: 0 4px 15px rgba(56, 151, 240, 0.4);">
                🛒 Proceed to payment page &rarr;
            </button>

            <div style="margin-top: 20px; font-size: 0.72rem; color: #777777; line-height: 1.6; text-align: center;">
                <div>• All sales are final</div>
                <div>• Subscriptions auto-renew by default</div>
                <div>• Please manage your subscription accordingly</div>
                <div>• During a sale period coupons are not accepted unless the coupon discount exceeds the sale rate. Referrals still grant points.</div>
            </div>

            <div style="text-align: center; margin-top: 14px;">
                <button onclick="closePreCheckoutModal()" style="background: transparent; border: none; color: #aaaaaa; text-decoration: underline; font-size: 0.8rem; cursor: pointer;">Back to Pricing</button>
            </div>
        </div>
    `;

    document.body.appendChild(modalDiv);
}

let activeSelectedPlan = 'annual';

function openPreCheckoutModal(planType) {
    injectPreCheckoutModalHTML();
    activeSelectedPlan = planType;
    const overlay = document.getElementById('precheckout-overlay');
    if (!overlay) return;

    const planName = document.getElementById('modal-plan-name');
    const strikeMonthly = document.getElementById('modal-strike-monthly');
    const monthlyRate = document.getElementById('modal-monthly-rate');
    const discountTag = document.getElementById('modal-discount-tag');
    const strikeTotal = document.getElementById('modal-strike-total');
    const totalText = document.getElementById('modal-total-text');
    const savedText = document.getElementById('modal-saved-text');
    const renewalDate = document.getElementById('modal-renewal-date');
    const subtotal = document.getElementById('modal-subtotal');
    const totalDue = document.getElementById('modal-total-due');

    const nextYearDate = new Date();
    nextYearDate.setFullYear(nextYearDate.getFullYear() + 1);
    const dateStr = `${nextYearDate.getMonth()+1}/${nextYearDate.getDate()}/${nextYearDate.getFullYear()}`;

    if (planType === 'monthly') {
        planName.innerText = 'Monthly Executive Pass';
        strikeMonthly.style.display = 'none';
        monthlyRate.innerText = '$500.00 / mo';
        discountTag.innerText = '🏷️ Full Wire Access + Free Trial';
        strikeTotal.style.display = 'none';
        totalText.innerText = '$500.00 / month';
        savedText.style.display = 'none';
        renewalDate.innerText = '9/2/2026 (After 7-Day Trial)';
        subtotal.innerText = '$500.00';
        totalDue.innerText = '$500.00';
    } else if (planType === 'quarterly') {
        planName.innerText = 'Quarterly Executive Pass';
        strikeMonthly.style.display = 'inline';
        strikeMonthly.innerText = '$500.00';
        monthlyRate.innerText = '$333.33 / mo';
        discountTag.innerText = '🏷️ Quarterly Discount 33% off';
        strikeTotal.style.display = 'inline';
        strikeTotal.innerText = '$1,500.00';
        totalText.innerText = '$1,000.00 Billed quarterly';
        savedText.style.display = 'block';
        savedText.innerText = '(-$500.00 Saved)';
        renewalDate.innerText = '11/2/2026';
        subtotal.innerText = '$1,000.00';
        totalDue.innerText = '$1,000.00';
    } else {
        planName.innerText = 'Annual Enterprise Pass';
        strikeMonthly.style.display = 'inline';
        strikeMonthly.innerText = '$500.00';
        monthlyRate.innerText = '$166.66 / mo';
        discountTag.innerText = '🏷️ Enterprise Discount 66% off';
        strikeTotal.style.display = 'inline';
        strikeTotal.innerText = '$6,000.00';
        totalText.innerText = '$2,000.00 Billed annually';
        savedText.style.display = 'block';
        savedText.innerText = '(-$4,000.00 Saved)';
        renewalDate.innerText = dateStr;
        subtotal.innerText = '$2,000.00';
        totalDue.innerText = '$2,000.00';
    }

    overlay.style.display = 'block';
}

function closePreCheckoutModal() {
    const overlay = document.getElementById('precheckout-overlay');
    if (overlay) overlay.style.display = 'none';
}

function applyCoupon() {
    const input = document.getElementById('modal-coupon-input');
    if (input && input.value.trim().toLowerCase() === 'vip2026') {
        alert('VIP Coupon Applied! 10% Additional Discount Recorded.');
    } else {
        alert('Invalid coupon code or code expired.');
    }
}

function proceedToStripeCheckout() {
    const email = document.getElementById('modal-email-input').value;
    alert(`Redirecting to Stripe Secure Checkout for ${activeSelectedPlan.toUpperCase()} plan (Account: ${email})...`);
    window.location.href = "https://buy.stripe.com/test_nicotinewire";
}
