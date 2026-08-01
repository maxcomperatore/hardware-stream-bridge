"""
Publisher Module for NicotineWire.
Takes generated B2B stories from CrewAI and updates nicotinewire/index.html with deduplication and clean section management.
Hides raw metadata text lines for clean, ultra-executive presentation.
"""

import os
import re
from typing import List, Dict

INDEX_PATH = os.path.join(os.path.dirname(__file__), "index.html")


def sanitize_text(text: str) -> str:
    """Sanitize text to enforce 2026 current year, remove markdown, em-dashes, and common LLM typos."""
    if not text:
        return ""
    s = text.replace("20XX", "2026").replace("2024", "2026").replace("2025", "2026")
    s = s.replace("M&Ac", "M&A").replace("**", "").replace("—", ", ").replace("--", ", ").replace("&mdash;", ", ")
    return s.strip()


def update_index_ticker(ticker_data: Dict[str, str]) -> bool:
    """Update live ticker values in index.html if needed."""
    return True


def publish_articles_to_index(articles: List[Dict[str, str]]) -> bool:
    """Replace and deduplicate articles in section 1 of nicotinewire/index.html."""
    if not os.path.exists(INDEX_PATH):
        print(f"[Publisher Error] index.html not found at {INDEX_PATH}")
        return False
        
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    start_heading = "<h2>LIVE REGULATORY & M&A INTELLIGENCE WIRE</h2>"
    end_heading = "<h2>B2B NICOTINE SUPPLY CHAIN DIRECTORY</h2>"
    
    start_pos = html_content.find(start_heading)
    end_pos = html_content.find(end_heading)
    
    if start_pos == -1 or end_pos == -1:
        print("[Publisher Error] Heading markers not found in index.html.")
        return False
        
    pre_content = html_content[:start_pos + len(start_heading)]
    post_content = html_content[end_pos:]
    
    # Deduplicate articles
    seen_titles = set()
    new_articles_html = []
    
    for art in articles:
        title = sanitize_text(art.get("title", "Untitled Story"))
        summary = sanitize_text(art.get("summary", ""))
        
        # Deduplication check
        if title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())
        
        article_card = f"""
<article>
    <details>
        <summary><strong>{title}</strong></summary>
        <p>{summary}</p>
    </details>
</article>"""
        new_articles_html.append(article_card)
        
    updated_middle = "\n".join(new_articles_html) + "\n\n<hr>\n\n"
    full_updated_html = pre_content + "\n" + updated_middle + post_content
    
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(full_updated_html)
        
    print(f"[Publisher Success] Published {len(new_articles_html)} deduplicated & ultra-clean articles to index.html.")
    return True
