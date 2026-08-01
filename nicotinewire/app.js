// NicotineWire Minimal Interactive Logic

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

function askAi() {
    const input = document.getElementById('ai-input');
    const responseDiv = document.getElementById('ai-response');
    if (!input || !responseDiv) return;

    const query = input.value.trim();
    if (!query) {
        responseDiv.innerText = "Please enter a search prompt (e.g. PMTA status, TPD3 monograph)...";
        return;
    }

    responseDiv.innerText = "Searching NicotineWire Indexed FDA & Patent Database...";
    
    setTimeout(() => {
        responseDiv.innerText = `[Wire AI Analysis]: Found 3 FDA Warning Letters & 2 PMTA Monograph filings matching "${query}". Status: High Regulatory Sensitivity. Check the Wire before you acquire.`;
    }, 800);
}
