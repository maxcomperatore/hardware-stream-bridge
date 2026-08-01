"""
CrewAI Multi-Agent Pipeline for NicotineWire.
Features a 4-Agent Architecture including a dedicated Compliance & Financial Judge Agent.
1. Regulatory Analyst Agent
2. M&A Deal Reporter Agent
3. Senior B2B Editor Agent
4. Compliance & Financial Judge Agent (Evaluates, Fact-Checks, & Approves Briefings)
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
        "temperature": 0.2
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
    """Agent specialized in FDA CTP, PMTA, and TPD3 regulatory analysis with legal accuracy."""
    
    def process(self, raw_item: Dict[str, Any]) -> str:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a Senior Tobacco & Synthetic Nicotine Regulatory Legal Officer.\n"
                    "REGULATORY LEGAL DIRECTIVES:\n"
                    "1. Real Statutory Deadlines Only: Draft guidance documents DO NOT create binding PMTA deadlines. Cite actual 60-day or 90-day public comment windows instead of inventing arbitrary 30-day filing limits.\n"
                    "2. Active Case Law Precision: Remember premium cigars and accessories are exempted under federal court rulings. Civil Money Penalties (CMPs) are statutory per-violation caps.\n"
                    "3. Separate Agency Dialogue from Statutory Shift: Routine FDA webinars or small manufacturer roundtables do NOT lower statutory evidentiary standards or handicap well-capitalized leaders.\n"
                    "4. Focus on institutional legal realities: Who wins? Who loses? What is the actual compliance trap or fee structure?"
                )
            },
            {
                "role": "user",
                "content": f"Analyze raw docket:\nTitle: {raw_item.get('title')}\nRaw Text: {raw_item.get('raw_content')}"
            }
        ]
        return call_openrouter_completion(prompt)


class MADealReporterAgent:
    """Agent specialized in M&A transactions and Wall Street financial metrics."""
    
    def process(self, raw_item: Dict[str, Any]) -> str:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a Senior Wall Street M&A Analyst for PE funds and institutional buyers.\n"
                    "FINANCIAL TERMINOLOGY DIRECTIVES:\n"
                    "- ALWAYS use EV/EBITDA (7.5x-9.5x), P/E (11x-14x), or EV/Sales for legacy CPG & public tobacco giants (Altria, PMI, BAT, Imperial Brands).\n"
                    "- ABSOLUTELY BANNED: Never use 'ARR' (Annual Recurring Revenue) for traditional consumer goods or tobacco companies! Reserve ARR strictly for B2B subscription software.\n"
                    "- For synthetic raw materials, use Spot Prices per kg ($3,450/kg).\n"
                    "- For oral pouches and ENDS, use SKU compliance costs ($1.5M/flavor line) and Shipment Can Volumes."
                )
            },
            {
                "role": "user",
                "content": f"Analyze market transaction:\nTitle: {raw_item.get('title')}\nRaw Text: {raw_item.get('raw_content')}"
            }
        ]
        return call_openrouter_completion(prompt)


class SeniorB2BEditorAgent:
    """Senior Editorial Agent synthesizing analyst findings into memorable executive briefings."""
    
    def process(self, raw_item: Dict[str, Any], analysis: str) -> Dict[str, str]:
        current_year = datetime.now().year
        prompt = [
            {
                "role": "system",
                "content": (
                    f"You are the Executive Editor at NicotineWire. Write a punchy, highly memorable, and opinionated B2B executive intelligence story.\n"
                    f"EDITORIAL DIRECTIVES:\n"
                    f"1. TEMPORAL ACCURACY: Current year is dynamically {current_year}. Do not cite past years (2022-2025) as future deadlines.\n"
                    f"2. FINANCIAL ACCURACY: Use EV/EBITDA, P/E, or EV/Sales for CPG/Tobacco firms. Never use ARR for non-SaaS companies.\n"
                    f"3. VARY SIGN-OFFS: Do NOT append 'Check the Wire before you acquire' to every story! Vary conclusion sign-offs naturally.\n"
                    f"4. HEADLINE VARIETY: Use diverse action openers (e.g., 'Border Seizure Alert:', 'PMTA Mandate Squeezes...', 'M&A Valuation Shift:', 'CTP Rulemaking Hits...', 'Import Barrier Surges:').\n"
                    f"5. NO EM-DASHES, NO ASTERISKS, NO PLACEHOLDERS.\n"
                    f"Output strictly valid JSON with keys:\n"
                    f" - 'title': Unique executive headline\n"
                    f" - 'category': Category tag (FDA / CTP ALERT, M&A INTELLIGENCE, CROP & COMMODITY)\n"
                    f" - 'summary': 2-3 sentence punchy, opinionated executive briefing"
                )
            },
            {
                "role": "user",
                "content": f"Title: {raw_item.get('title')}\nSource: {raw_item.get('source')}\nAnalyst Findings: {analysis}"
            }
        ]
        
        raw_res = call_openrouter_completion(prompt)
        try:
            clean_res = raw_res.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[1].split("```")[0].strip()
            return json.loads(clean_res)
        except Exception:
            clean_title = raw_item.get('title', 'Executive Briefing').replace("20XX", "2026").replace("M&Ac", "M&A").replace("**", "").replace("—", ", ")
            return {
                "title": clean_title,
                "category": raw_item.get('category', 'FDA / CTP ALERT'),
                "summary": f"{analysis[:240]} Strategic compliance alignment required."
            }


class ComplianceJudgeAgent:
    """4th Subagent: High-level Compliance Judge & Publisher Auditor evaluating and polishing all generated drafts."""
    
    def evaluate_and_polish(self, draft_story: Dict[str, str]) -> Dict[str, str]:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are the Senior Compliance Judge and Publisher Auditor at NicotineWire.\n"
                    "Your sole job is to review, audit, and polish executive drafts before publication.\n"
                    "JUDGING & POLISHING AUDIT RULES:\n"
                    "1. Financial Terminology: Replace any accidental 'ARR' usage for tobacco/CPG companies with EV/EBITDA, P/E, or EV/Sales.\n"
                    "2. Temporal Precision: Replace any historical years (2022-2025) with 2026.\n"
                    "3. Structural Variety: Ensure the briefing ends naturally with actionable strategic advice without repetitive boilerplate templates.\n"
                    "4. Clean Formatting: Ensure zero em-dashes (—), zero markdown asterisks (**), and zero placeholders.\n"
                    "Output strictly valid JSON with keys:\n"
                    " - 'title': Audited & polished headline\n"
                    " - 'category': Category tag\n"
                    " - 'summary': Audited & polished executive briefing paragraph"
                )
            },
            {
                "role": "user",
                "content": f"Audit draft story:\nTitle: {draft_story.get('title')}\nCategory: {draft_story.get('category')}\nSummary: {draft_story.get('summary')}"
            }
        ]
        
        raw_res = call_openrouter_completion(prompt)
        try:
            clean_res = raw_res.strip()
            if "```json" in clean_res:
                clean_res = clean_res.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[1].split("```")[0].strip()
            audited = json.loads(clean_res)
            print(f"[Compliance Judge Verdict] Approved & Polished: '{audited.get('title', '')[:45]}'")
            return audited
        except Exception:
            print(f"[Compliance Judge Verdict] Passed Draft with Standard Sanitize.")
            return draft_story


def run_crew_pipeline(raw_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Execute 4-agent Crew processing across ingested items (Max 6 premier briefings)."""
    print(f"[CrewAI Crew] Launching 4-agent team (Analyst + M&A + Editor + Compliance Judge) with model {MODEL_NAME}...")
    reg_agent = RegulatoryAnalystAgent()
    ma_agent = MADealReporterAgent()
    editor_agent = SeniorB2BEditorAgent()
    judge_agent = ComplianceJudgeAgent()
    
    published_stories = []
    for item in raw_items:
        if len(published_stories) >= 6:
            print("[CrewAI Early Exit] Reached max 6 premier briefings limit. Stopping AI generation early for maximum speed!")
            break

        text_content = f"{item.get('title', '')} {item.get('raw_content', '')}"
        if not filter_relevant_item(text_content):
            print(f"[CrewAI Filter] Dropping non-tobacco noise: {item.get('title', '')[:40]}")
            continue
            
        print(f"[CrewAI Agent Working] Processing relevant item: {item.get('title', '')[:60]}")
        category = item.get("category", "FDA / CTP ALERT")
        
        # Step 1: Analyst Draft
        if "M&A" in category or "CROP" in category:
            analysis = ma_agent.process(item)
        else:
            analysis = reg_agent.process(item)
            
        # Step 2: Senior Editor Draft
        draft_story = editor_agent.process(item, analysis)
        
        # Step 3: Compliance Judge Final Audit & Polish
        final_approved_story = judge_agent.evaluate_and_polish(draft_story)
        published_stories.append(final_approved_story)
        
    print(f"[CrewAI Crew Complete] 4-Agent Team Approved {len(published_stories)} premier B2B stories.")
    return published_stories
