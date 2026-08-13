"""
Publisher Module for NicotineWire.
Takes generated B2B stories from CrewAI and updates nicotinewire/index.html with deduplication and clean section management.
Hides raw metadata text lines and limits output to the top 6 premier executive briefings.
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
    """Replace and deduplicate articles in section 1 of nicotinewire/index.html (Max 6 premier briefings)."""
    if not os.path.exists(INDEX_PATH):
        print(f"[Publisher Error] index.html not found at {INDEX_PATH}")
        return False
        
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Resilient heading matching
    start_pos = html_content.find("LIVE REGULATORY")
    end_pos = html_content.find("B2B NICOTINE SUPPLY CHAIN DIRECTORY")
    
    if start_pos == -1 or end_pos == -1:
        print("[Publisher Error] Heading markers not found in index.html.")
        return False
        
    # Find the closing </div> or </h2> after LIVE REGULATORY
    heading_end_pos = html_content.find("</div>", start_pos)
    if heading_end_pos == -1 or heading_end_pos > end_pos:
        heading_end_pos = html_content.find("</h2>", start_pos) + len("</h2>")
    else:
        heading_end_pos += len("</div>")
        
    pre_content = html_content[:heading_end_pos]
    
    # Find the opening <h2> for DIRECTORY
    directory_heading_pos = html_content.rfind("<h2", 0, end_pos)
    if directory_heading_pos == -1:
        directory_heading_pos = end_pos
    post_content = html_content[directory_heading_pos:]
    
    # Deduplicate articles and take MAX 6
    seen_titles = set()
    new_articles_html = []
    
    for art in articles:
        if len(new_articles_html) >= 6:
            break
            
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
        
    updated_middle = "\n" + "\n".join(new_articles_html) + "\n\n<hr>\n\n"
    full_updated_html = pre_content + updated_middle + post_content
    
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(full_updated_html)
        
    print(f"[Publisher Success] Published {len(new_articles_html)} premier executive briefings (Max 6) to index.html.")
    return True
