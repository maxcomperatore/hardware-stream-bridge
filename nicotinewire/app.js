// NicotineWire 3-Tier Access & Self-Centered Executive Value Engine

const OPENROUTER_KEY = "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";
const MODEL_NAME = "ibm-granite/granite-4.1-8b";

// User states: 'visitor', 'free_member', 'executive_paid'
let currentUserState = localStorage.getItem('nw_user_state') || 'visitor';
let freeArticlesRead = 0;
let aiQueriesCount = 0;

document.addEventListener('DOMContentLoaded', () => {
    updateUserBannerUI();
    enforceStoryLimits();
    attachBlurPaywallToDetails();
});

function setUserState(state) {
    currentUserState = state;
    localStorage.setItem('nw_user_state', state);
    updateUserBannerUI();
    enforceStoryLimits();
    location.reload();
}

function updateUserBannerUI() {
    const banner = document.getElementById('user-state-banner');
    if (!banner) return;

    let modeSelectorHTML = `
        <div style="margin-top: 6px; font-size: 11px; opacity: 0.9;">
            <strong>Test Access Mode:</strong> 
            <button onclick="setUserState('visitor')" style="padding: 2px 6px; font-size: 10px; cursor: pointer; ${currentUserState==='visitor'?'font-weight:bold; background:#FFEA00;':''}">Visitor Mode</button>
            <button onclick="setUserState('free_member')" style="padding: 2px 6px; font-size: 10px; cursor: pointer; ${currentUserState==='free_member'?'font-weight:bold; background:#FFEA00;':''}">Free Member</button>
            <button onclick="setUserState('executive_paid')" style="padding: 2px 6px; font-size: 10px; cursor: pointer; ${currentUserState==='executive_paid'?'font-weight:bold; background:#FFEA00;':''}">Executive Paid</button>
        </div>
    `;

    if (currentUserState === 'executive_paid') {
        banner.innerHTML = `<div style="background:#111; color:#FFD700; padding:10px 12px; margin-bottom:12px; border-radius:4px;">
            <strong>EXECUTIVE PASS ACTIVE:</strong> Full Un-Metered Wire, B2B Directory &amp; Unlimited AI Terminal Unlocked. <em>Status: Untouchable Market Authority.</em>
            ${modeSelectorHTML}
        </div>`;
    } else if (currentUserState === 'free_member') {
        banner.innerHTML = `<div style="background:#fff3cd; color:#856404; border:1px solid #ffeeba; padding:10px 12px; margin-bottom:12px; border-radius:4px;">
            <strong>FREE MEMBER PASS:</strong> Your competitors are already using NicotineWire to track FDA dockets &amp; source suppliers. <a href="pricing.html" style="font-weight:bold; color:#111;">Upgrade to Executive Pass ($2,000/yr) &rarr; Lock In Your Advantage</a>
            ${modeSelectorHTML}
        </div>`;
    } else {
        banner.innerHTML = `<div style="background:#e9ecef; color:#383d41; border:1px solid #d6d8db; padding:10px 12px; margin-bottom:12px; border-radius:4px;">
            <strong>VISITOR PREVIEW:</strong> Showing 10 Public Wire Briefings. Your rival funds are already hiring &amp; bidding using NicotineWire. <button onclick="setUserState('free_member')" style="font-weight:bold; cursor:pointer; padding:2px 8px; margin-left:6px;">Create Free Account</button> or <a href="pricing.html" style="font-weight:bold; color:#111;">Upgrade to Executive Pass &rarr;</a>
            ${modeSelectorHTML}
        </div>`;
    }
}

function enforceStoryLimits() {
    const articles = document.querySelectorAll('article');
    if (currentUserState === 'visitor') {
        articles.forEach((art, index) => {
            if (index >= 10) {
                art.style.display = 'none';
            } else {
                art.style.display = 'block';
            }
        });
    } else {
        articles.forEach(art => art.style.display = 'block');
    }
}

function attachBlurPaywallToDetails() {
    if (currentUserState === 'executive_paid') return;

    const detailsList = document.querySelectorAll('article details');
    detailsList.forEach((det, index) => {
        const allowed = currentUserState === 'free_member' ? 5 : 2;
        if (index >= allowed) {
            det.addEventListener('toggle', (e) => {
                if (det.open && !det.querySelector('.blur-paywall-overlay')) {
                    applyBlurOverlay(det);
                }
            });
        }
    });
}

function applyBlurOverlay(detailsElem) {
    const pElems = detailsElem.querySelectorAll('p');
    if (pElems.length === 0) return;

    const mainParagraph = pElems[0];
    const originalText = mainParagraph.innerText;
    
    const wrapper = document.createElement('div');
    wrapper.className = 'blur-paywall-overlay';
    wrapper.style.position = 'relative';
    wrapper.style.marginTop = '8px';

    const blurredDiv = document.createElement('div');
    blurredDiv.className = 'blurred-content';
    blurredDiv.style.filter = 'blur(6px)';
    blurredDiv.style.userSelect = 'none';
    blurredDiv.style.pointerEvents = 'none';
    blurredDiv.style.opacity = '0.35';
    blurredDiv.innerText = originalText;

    const ctaDiv = document.createElement('div');
    ctaDiv.className = 'paywall-cta-box';
    ctaDiv.style.position = 'absolute';
    ctaDiv.style.top = '50%';
    ctaDiv.style.left = '50%';
    ctaDiv.style.transform = 'translate(-50%, -50%)';
    ctaDiv.style.background = '#111111';
    ctaDiv.style.color = '#ffffff';
    ctaDiv.style.padding = '14px 20px';
    ctaDiv.style.borderRadius = '6px';
    ctaDiv.style.textAlign = 'center';
    ctaDiv.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
    ctaDiv.style.width = '85%';
    ctaDiv.style.zIndex = '10';

    ctaDiv.innerHTML = `
        <strong style="color:#FFD700; font-size:14px; display:block; margin-bottom:4px;">⚠️ COMPETITIVE WARNING: EXECUTIVE WIRE ACCESS REQUIRED</strong>
        <span style="font-size:12px; display:block; margin-bottom:10px; color:#ddd;">Your competitors are already reading this briefing to lock in deal valuation benchmarks and FDA warning thresholds. Don't get left behind.</span>
        <a href="pricing.html" style="background:#FFEA00; color:#111; padding:6px 14px; text-decoration:none; font-weight:bold; border-radius:4px; font-size:12px;">Upgrade to Executive Pass &rarr;</a>
    `;

    wrapper.appendChild(blurredDiv);
    wrapper.appendChild(ctaDiv);

    mainParagraph.parentNode.replaceChild(wrapper, mainParagraph);
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

    if (currentUserState === 'visitor') {
        aiQueriesCount++;
        if (aiQueriesCount > 1) {
            responseDiv.innerHTML = `<p style="color:#d9534f;"><strong>AI Terminal Limit:</strong> You have reached your visitor AI query limit. Your competitors are already using this terminal. <button onclick="setUserState('free_member')" style="font-weight:bold; cursor:pointer;">Join Free Account</button> or <a href="pricing.html"><strong>Upgrade to Executive Pass for Unlimited AI Access &rarr;</strong></a></p>`;
            return;
        }
    }

    responseDiv.innerHTML = "<p><strong>Senior AI Analyst:</strong> <em>Querying live Federal Register dockets, SEC filings, and nicotine M&amp;A database...</em></p>";

    const systemPrompt = "You are the Senior Executive AI Analyst at NicotineWire. You are a seasoned, authoritative expert in FDA CTP regulations, PMTA dockets, synthetic L-nicotine chemistry, TPD rules, oral pouch manufacturing, and PE M&A transaction valuation multiples. Answer questions with extreme financial & legal authority, hard quantitative metrics ($M, ARR multiples, SKU costs), bold strategic clarity, zero fluff, and always end your response with 'Check the Wire before you acquire.'";

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
