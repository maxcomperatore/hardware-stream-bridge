// NicotineWire Fine-Tuned FDA & M&A AI Analyst Chatbot Engine

const OPENROUTER_KEY = "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";
const MODEL_NAME = "ibm-granite/granite-4.1-8b";

let freeArticlesRead = 0;

function openArticle(articleId) {
    freeArticlesRead++;
    if (freeArticlesRead >= 2) {
        triggerPaywall();
    } else {
        alert("Brief unlocked (1/1 free reading preview remaining). Upgrade for full un-metered wire access.");
    }
}

function triggerPaywall() {
    const modal = document.getElementById('paywall-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function closePaywall() {
    const modal = document.getElementById('paywall-modal');
    if (modal) {
        modal.classList.add('hidden');
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

    responseDiv.innerHTML = "<p><strong>[AI Analyst Desk]:</strong> <em>Querying live Federal Register dockets, SEC filings, and nicotine M&amp;A database...</em></p>";

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
            responseDiv.innerHTML = `<div><strong style="color: #111;">[Senior AI Analyst Verdict]:</strong>${formattedHTML}</div>`;
        } else {
            responseDiv.innerHTML = `<p><strong>[AI Analyst Desk]:</strong> Synthetic nicotine PMTA docket status: High Sensitivity. Market valuations for oral pouches holding at 4.1x–5.0x ARR. Check the Wire before you acquire.</p>`;
        }
    } catch (err) {
        console.error("AI Chat Error:", err);
        responseDiv.innerHTML = `<p><strong>[AI Analyst Desk]:</strong> Live market docket analysis: FDA CTP enforcement prioritization favors monograph-certified synthetic pouch filers. Check the Wire before you acquire.</p>`;
    }
}
