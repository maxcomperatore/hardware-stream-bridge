"""
CrewAI Multi-Agent Pipeline for NicotineWire.
Connects to OpenRouter API (model: ibm-granite/granite-4.1-8b) to produce opinionated, high-impact B2B executive intelligence.
"""

import json
import os
import urllib.request
from typing import List, Dict, Any

# Load environment variables
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v.strip('"').strip("'")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "ibm-granite/granite-4.1-8b")


def call_openrouter_completion(messages: List[Dict[str, str]]) -> str:
    """Utility wrapper for OpenRouter API call."""
    if not OPENROUTER_API_KEY:
        print("[CrewAI Warning] OPENROUTER_API_KEY missing. Using fallback response.")
        return ""
        
    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://nicotinewire.com",
        "X-Title": "NicotineWire Crew Pipeline"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.4
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            return content.strip()
    except Exception as e:
        print(f"[OpenRouter Error] API call failed: {e}")
        return ""


def is_relevant_nicotine_news(title: str, content: str) -> bool:
    """Filter out non-tobacco FDA pharma/drug news and generic SEC noise."""
    text = (title + " " + content).lower()
    
    # Non-tobacco FDA pharma/medical noise & generic SEC noise to drop
    noise_keywords = [
        "small business advisory", "small business forum", "24-hour trading", "roundtable on preparations",
        "sickle cell", "cholesterol", "horses", "screwworm", "blood cancer", "plasma product", 
        "gene therapy", "pcsk9", "color additives in food", "digital health devices", "poultry", "cotton board"
    ]
    for noise in noise_keywords:
        if noise in text:
            return False
            
    # Positive tobacco & nicotine keywords required
    relevant_keywords = [
        "nicotine", "tobacco", "pouch", "vape", "ends", "flue-cured", "leaf", 
        "pmta", "tpd", "ctp", "synthetic", "acquisition", "monograph",
        "docket", "injunction", "import alert", "menthol", "substantial equivalence"
    ]
    return any(kw in text for kw in relevant_keywords)


class RegulatoryAnalystAgent:
    """Agent specialized in FDA CTP, PMTA, and TPD3 regulatory analysis with sharp opinionated takeaways."""
    
    def process(self, raw_item: Dict[str, Any]) -> str:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a Senior Tobacco & Synthetic Nicotine Regulatory Analyst known for punchy, opinionated B2B insights. "
                    "Analyze raw FDA/CTP/TPD regulatory dockets. Ignore generic administrative noise. "
                    "Focus on the strategic impact: Who wins? Who loses? What is the compliance trap or financial cost? "
                    "Highlight hard numbers, PMTA docket numbers, deadlines, and operational risk."
                )
            },
            {
                "role": "user",
                "content": f"Analyze raw docket:\nTitle: {raw_item.get('title')}\nRaw Text: {raw_item.get('raw_content')}"
            }
        ]
        return call_openrouter_completion(prompt)


class MADealReporterAgent:
    """Agent specialized in M&A transactions, valuation multiples, and commodity trends with sharp financial commentary."""
    
    def process(self, raw_item: Dict[str, Any]) -> str:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a Senior Financial M&A Reporter for PE funds and institutional buyers. "
                    "Analyze B2B nicotine transactions, corporate earnings, and commodity auctions. "
                    "Provide a bold, opinionated financial take on valuation multiples, margin pressures, or competitive moats. "
                    "Highlight hard metrics: deal valuations ($M), ARR multiples (e.g. 4.1x ARR), and spot price shifts."
                )
            },
            {
                "role": "user",
                "content": f"Analyze market transaction:\nTitle: {raw_item.get('title')}\nRaw Text: {raw_item.get('raw_content')}"
            }
        ]
        return call_openrouter_completion(prompt)


from datetime import datetime

class SeniorB2BEditorAgent:
    """Senior Editorial Agent synthesizing analyst findings into memorable, opinionated B2B intelligence stories ending with 'Check the Wire before you acquire.'"""
    
    def process(self, raw_item: Dict[str, Any], analysis: str) -> Dict[str, str]:
        current_year = datetime.now().year
        prompt = [
            {
                "role": "system",
                "content": (
                    f"You are the Executive Editor at NicotineWire. Write a punchy, highly memorable, and opinionated B2B executive intelligence story.\n"
                    f"TEMPORAL GROUNDING MANDATE:\n"
                    f"- Today's current year is dynamically {current_year}.\n"
                    f"- All future compliance deadlines, PMTA submissions, and market forecasts MUST be set in {current_year}, {current_year + 1}, or {current_year + 2}.\n"
                    f"- NEVER cite past years (such as 2022, 2023, 2024, or 2025) as upcoming or future deadlines! If a raw source document mentions a historical filing from 2023 or 2024, frame it as historical context and state the current {current_year} business impact.\n"
                    f"WRITING STYLE GUIDELINES:\n"
                    f"1. Write with sharp editorial authority and clear opinion (call out compliance traps, margin squeezes, valuation compression, or strategic winners/losers).\n"
                    f"2. VARY HEADLINE OPENINGS! NEVER start multiple headlines with 'FDA Tightens' or 'Winners, Losers'. Use diverse action openers (e.g., 'Border Seizure Alert:', 'PMTA Mandate Squeezes...', 'M&A Valuation Shift:', 'CTP Rulemaking Hits...', 'Import Barrier Surges:').\n"
                    f"3. NO PLACEHOLDERS! Never output '20XX', 'TBD', or '[Insert]'.\n"
                    f"4. Clean category string: MUST be exactly 'FDA / CTP ALERT', 'M&A INTELLIGENCE', or 'CROP & COMMODITY'. Do not output 'M&Ac'.\n"
                    f"5. MUST end with the exact phrase: 'Check the Wire before you acquire.'\n"
                    f"6. ABSOLUTELY NO EM-DASHES (do NOT use — or -- or &mdash; anywhere). Use colons, commas, or parentheses instead.\n"
                    f"7. ABSOLUTELY NO BOLD MARKDOWN SYMBOLS (do NOT use ** anywhere in title or summary).\n"
                    f"Output strictly valid JSON with keys:\n"
                    f" - 'title': Unique, punchy, memorable executive headline without em-dashes, asterisks, repetitive patterns, or placeholders\n"
                    f" - 'category': Category tag (FDA / CTP ALERT, M&A INTELLIGENCE, CROP & COMMODITY)\n"
                    f" - 'meta': Format string (CATEGORY | TIMESTAMP | SOURCE)\n"
                    f" - 'summary': 2-3 sentence punchy, opinionated summary ending with 'Check the Wire before you acquire.'"
                )
            },
            {
                "role": "user",
                "content": (
                    f"Category: {raw_item.get('category')}\n"
                    f"Original Title: {raw_item.get('title')}\n"
                    f"Source: {raw_item.get('source')}\n"
                    f"Timestamp: {raw_item.get('timestamp')}\n"
                    f"Analyst Findings: {analysis}\n"
                    "Return ONLY JSON."
                )
            }
        ]
        response_text = call_openrouter_completion(prompt)
        
        try:
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            return data
        except Exception:
            summary_text = f"{raw_item.get('raw_content')} Check the Wire before you acquire."
            return {
                "title": raw_item.get("title", "Market Update"),
                "category": raw_item.get("category", "INTELLIGENCE WIRE"),
                "meta": f"{raw_item.get('category')} | {raw_item.get('timestamp')} | {raw_item.get('source')}",
                "summary": summary_text
            }


def run_crew_pipeline(raw_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Run the multi-agent Crew team across relevant ingested items."""
    print(f"[CrewAI Crew] Launching multi-agent team with model {MODEL_NAME}...")
    
    reg_agent = RegulatoryAnalystAgent()
    ma_agent = MADealReporterAgent()
    editor_agent = SeniorB2BEditorAgent()
    
    finished_articles = []
    
    for item in raw_items:
        title = item.get("title", "")
        content = item.get("raw_content", "")
        
        # 1. Filter out non-tobacco noise
        if not is_relevant_nicotine_news(title, content):
            print(f"[CrewAI Filter] Dropping non-tobacco noise: {title[:60]}")
            continue
            
        print(f"[CrewAI Agent Working] Processing relevant item: {title[:75]}")
        
        category = item.get("category", "")
        if "CROP" in category or "M&A" in category:
            analysis = ma_agent.process(item)
        else:
            analysis = reg_agent.process(item)
            
        final_story = editor_agent.process(item, analysis)
        if final_story and "summary" in final_story:
            finished_articles.append(final_story)
            
    print(f"[CrewAI Crew Complete] Generated {len(finished_articles)} high-metric B2B stories.")
    return finished_articles


if __name__ == "__main__":
    from news_ingest import ingest_all_sources
    items = ingest_all_sources()
    stories = run_crew_pipeline(items)
    print(f"[Pipeline Test] Generated {len(stories)} stories.")
