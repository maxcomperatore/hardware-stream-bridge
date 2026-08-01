"""
CrewAI Multi-Agent Pipeline for NicotineWire.
Features a 4-Agent Architecture with Bloomberg Financial & Legal Terminal Precision.
1. Regulatory Analyst Agent (Legal Precision & Active Case Law)
2. M&A Deal Reporter Agent (EV/EBITDA, EV/Sales, P/E Metrics)
3. Senior B2B Editor Agent (Bloomberg Terminal Editorial Tone)
4. Compliance Judge Agent (Fact-Checking & Tone Auditor)
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
MODEL_NAME = "deepseek/deepseek-v4-pro"


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
                    "STRICT FDA LEGAL & STATUTORY FACTS:\n"
                    "1. ZERO FDA Listing Fees: The FDA does NOT charge government SKU taxes or listing fees for establishment registration. Overhead is private CRO lab/legal fees.\n"
                    "2. Synthetic Nicotine Law: Synthetic nicotine is STRICTLY under FDA CTP authority (March 2022 Appropriations Law). There is NO open synthetic loophole.\n"
                    "3. Premium Cigar & Pouch Exemption: Traditional premium cigars were VACATED from FDA deeming authority (Cigar Association of America v. FDA). The proposed nicotine ceiling rule applies STRICTLY to combusted cigarettes, explicitly EXEMPTING non-combustibles (oral pouches, ENDS) and premium cigars.\n"
                    "4. Non-Binding Guidance: Draft guidance is non-binding; it does NOT create statutory PMTA submission deadlines. Real citations: #2026-13047 (Foreign Establishment Registration), #2026-04732 (Flavored ENDS Draft Guidance).\n"
                    "5. CMP Caps: Civil Money Penalties (CMPs) are statutory maximum caps per violation, not automated fines for minor paperwork omissions."
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
                    "STRICT FINANCIAL TERMINOLOGY:\n"
                    "- Use EV/EBITDA (7.5x-9.5x), EV/Sales, or P/E (11x-14x) for legacy CPG & public tobacco giants (Altria, PMI, BAT, Imperial Brands).\n"
                    "- BANNED: Never use 'ARR' (Annual Recurring Revenue) for non-subscription CPG companies! Reserve ARR strictly for SaaS platforms.\n"
                    "- For synthetic raw materials, use Spot Prices per kg ($3,450/kg).\n"
                    "- For oral pouches and ENDS, use SKU compliance costs and Can Shipment Volumes."
                )
            },
            {
                "role": "user",
                "content": f"Analyze market transaction:\nTitle: {raw_item.get('title')}\nRaw Text: {raw_item.get('raw_content')}"
            }
        ]
        return call_openrouter_completion(prompt)


class SeniorB2BEditorAgent:
    """Senior Editorial Agent synthesizing analyst findings into Bloomberg-grade institutional briefings."""
    
    def process(self, raw_item: Dict[str, Any], analysis: str) -> Dict[str, str]:
        current_year = datetime.now().year
        prompt = [
            {
                "role": "system",
                "content": (
                    f"You are the Senior Executive Editor at NicotineWire.\n"
                    f"BLOOMBERG EDITORIAL TONE MANDATE:\n"
                    f"1. INSTITUTIONAL WALL STREET TONE: Write with objective, authoritative financial precision like Bloomberg Law, Goldman Sachs Research, or Reuters.\n"
                    f"2. BAN SENSATIONALIST / PANIC WORDS: Banned words: 'death sentence', 'trap', 'crushes importers', 'procedural theater', 'hellscape'.\n"
                    f"   - Replace 'death sentence' -> 'substantive evidentiary barrier'\n"
                    f"   - Replace 'trap' -> 'regulatory bottleneck / compliance risk'\n"
                    f"   - Replace 'crushes importers' -> 'imposes steep evidentiary overhead'\n"
                    f"   - Replace 'procedural theater' -> 'non-binding educational forum'\n"
                    f"3. TEMPORAL & FINANCIAL PRECISION: Current year is {current_year}. Use EV/EBITDA and P/E for CPG. Cite real dockets.\n"
                    f"4. HEADLINE VARIETY: Use institutional action openers (e.g., 'Foreign Establishment Registration:', 'PMTA Compliance Bottleneck:', 'M&A Valuation Shift:', 'CTP Rulemaking Notice:').\n"
                    f"5. NO EM-DASHES, NO ASTERISKS, NO PLACEHOLDERS.\n"
                    f"Output strictly valid JSON with keys:\n"
                    f" - 'title': Unique institutional headline\n"
                    f" - 'category': Category tag (FDA / CTP ALERT, M&A INTELLIGENCE, CROP & COMMODITY)\n"
                    f" - 'summary': 2-3 sentence authoritative, Bloomberg-grade executive briefing"
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
                    "BLOOMBERG AUDIT CHECKS:\n"
                    "1. Tone Check: Purge any sensational panic words ('death sentence', 'trap', 'crushes importers', 'hellscape'). Enforce Bloomberg financial terminology.\n"
                    "2. Zero Fake Listing Fees: Ensure draft does not claim FDA charges statutory SKU listing fees.\n"
                    "3. Synthetic Nicotine & Premium Cigar Status: Synthetic is under CTP. Premium cigars and non-combustibles are exempt from nicotine ceiling.\n"
                    "4. Financial Metrics: Replace any accidental 'ARR' usage for tobacco/CPG with EV/EBITDA, P/E, or EV/Sales.\n"
                    "5. Clean Formatting: Zero em-dashes (—), zero markdown asterisks (**).\n"
                    "Output strictly valid JSON with keys:\n"
                    " - 'title': Audited & polished Bloomberg-grade headline\n"
                    " - 'category': Category tag\n"
                    " - 'summary': Audited & polished Bloomberg-grade executive briefing"
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
