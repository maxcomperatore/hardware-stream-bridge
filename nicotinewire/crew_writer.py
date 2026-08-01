"""
CrewAI Multi-Agent Pipeline for NicotineWire.
Connects to OpenRouter API (model: ibm-granite/granite-4.1-8b) to produce opinionated, high-impact B2B executive intelligence.
Enforces strict Wall Street financial terminology and temporal precision (2026).
"""

import json
import os
import urllib.request
from datetime import datetime
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
        "temperature": 0.3
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("choices"):
                return res_data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[CrewAI Error] OpenRouter API call failed: {e}")
    return ""


def filter_relevant_item(text: str) -> bool:
    """Pre-filter raw text to eliminate non-tobacco administrative noise."""
    text = text.lower()
    
    noise_keywords = [
        "small business advisory", "small business forum", "24-hour trading", "roundtable on preparations",
        "sickle cell", "cholesterol", "horses", "screwworm", "blood cancer", "plasma product", 
        "gene therapy", "pcsk9", "color additives in food", "digital health devices", "poultry", "cotton board"
    ]
    for noise in noise_keywords:
        if noise in text:
            return False
            
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
    """Agent specialized in M&A transactions, valuation multiples, and commodity trends with Wall Street precision."""
    
    def process(self, raw_item: Dict[str, Any]) -> str:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a Senior Wall Street M&A Analyst for PE funds and institutional buyers.\n"
                    "FINANCIAL METRIC MANDATE:\n"
                    "- For legacy CPG & public tobacco giants (Altria, PMI, BAT, Imperial Brands), use EV/EBITDA multiples (7.5x-9.5x), P/E multiples (11x-14x), Operating Margins (60%-65%), and Free Cash Flow Yields.\n"
                    "- NEVER use 'ARR' (Annual Recurring Revenue) for traditional consumer goods companies! Reserve ARR strictly for B2B SaaS platforms.\n"
                    "- For synthetic raw materials, use Spot Prices per kg ($3,450/kg).\n"
                    "- For oral pouches and ENDS, use SKU compliance costs ($1.5M/flavor line) and Shipment Can Volumes (e.g. 96M Cans)."
                )
            },
            {
                "role": "user",
                "content": f"Analyze market transaction:\nTitle: {raw_item.get('title')}\nRaw Text: {raw_item.get('raw_content')}"
            }
        ]
        return call_openrouter_completion(prompt)


class SeniorB2BEditorAgent:
    """Senior Editorial Agent synthesizing analyst findings into memorable, opinionated B2B intelligence stories ending with 'Check the Wire before you acquire.'"""
    
    def process(self, raw_item: Dict[str, Any], analysis: str) -> Dict[str, str]:
        current_year = datetime.now().year
        prompt = [
            {
                "role": "system",
                "content": (
                    f"You are the Executive Editor at NicotineWire. Write a punchy, highly memorable, and opinionated B2B executive intelligence story.\n"
                    f"TEMPORAL & FINANCIAL GROUNDING MANDATE:\n"
                    f"- Today's current year is dynamically {current_year}.\n"
                    f"- All future compliance deadlines, PMTA submissions, and market forecasts MUST be set in {current_year}, {current_year + 1}, or {current_year + 2}.\n"
                    f"- NEVER cite past years (such as 2022, 2023, 2024, or 2025) as upcoming or future deadlines!\n"
                    f"- FINANCIAL METRICS: Use EV/EBITDA and P/E multiples for legacy CPG firms (Altria, PMI, BAT). Never use ARR for CPG companies.\n"
                    f"WRITING STYLE GUIDELINES:\n"
                    f"1. Write with sharp editorial authority and clear opinion (call out compliance traps, margin squeezes, valuation compression, or strategic winners/losers).\n"
                    f"2. VARY HEADLINE OPENINGS! Use diverse action openers (e.g., 'Border Seizure Alert:', 'PMTA Mandate Squeezes...', 'M&A Valuation Shift:', 'CTP Rulemaking Hits...', 'Import Barrier Surges:').\n"
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
                )
            }
        ]
        
        raw_res = call_openrouter_completion(prompt)
        try:
            # Clean JSON string response
            clean_res = raw_res.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[1].split("```")[0].strip()
            return json.loads(clean_res)
        except Exception:
            # Fallback story construction if JSON parsing fails
            clean_title = raw_item.get('title', 'Executive Briefing').replace("20XX", "2026").replace("M&Ac", "M&A").replace("**", "").replace("—", ", ")
            return {
                "title": clean_title,
                "category": raw_item.get('category', 'FDA / CTP ALERT'),
                "meta": f"{raw_item.get('category', 'FDA / CTP ALERT')} | 2026-08-01 | {raw_item.get('source')}",
                "summary": f"{analysis[:240]} Check the Wire before you acquire."
            }


def run_crew_pipeline(raw_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Execute multi-agent Crew processing across ingested items."""
    print(f"[CrewAI Crew] Launching multi-agent team with model {MODEL_NAME}...")
    reg_agent = RegulatoryAnalystAgent()
    ma_agent = MADealReporterAgent()
    editor_agent = SeniorB2BEditorAgent()
    
    published_stories = []
    for item in raw_items:
        text_content = f"{item.get('title', '')} {item.get('raw_content', '')}"
        if not filter_relevant_item(text_content):
            print(f"[CrewAI Filter] Dropping non-tobacco noise: {item.get('title', '')[:40]}")
            continue
            
        print(f"[CrewAI Agent Working] Processing relevant item: {item.get('title', '')[:60]}")
        category = item.get("category", "FDA / CTP ALERT")
        
        if "M&A" in category or "CROP" in category:
            analysis = ma_agent.process(item)
        else:
            analysis = reg_agent.process(item)
            
        final_story = editor_agent.process(item, analysis)
        published_stories.append(final_story)
        
    print(f"[CrewAI Crew Complete] Generated {len(published_stories)} high-metric B2B stories.")
    return published_stories
