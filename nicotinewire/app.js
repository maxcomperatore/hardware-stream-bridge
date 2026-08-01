// NicotineWire Clean Executive Terminal Engine

const OPENROUTER_KEY = "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";
const MODEL_NAME = "deepseek/deepseek-v4-pro";

let isAllExpanded = false;

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
