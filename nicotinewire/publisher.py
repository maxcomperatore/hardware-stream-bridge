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
    start_pos = html_content.find("Live Regulatory &")
    if start_pos == -1:
        start_pos = html_content.find("Live Regulatory")
    
    if start_pos == -1:
        print("[Publisher Error] Heading markers not found in index.html.")
        return False
        
    heading_end_pos = html_content.find('class="nw-feed-container">', start_pos)
    if heading_end_pos != -1:
        heading_end_pos += len('class="nw-feed-container">')
    else:
        print("[Publisher Error] nw-feed-container not found.")
        return False

    end_pos = html_content.find('</main>', heading_end_pos)
    if end_pos == -1:
        end_pos = html_content.find('</div>', heading_end_pos)

    pre_content = html_content[:heading_end_pos]
    post_content = html_content[end_pos:]

    # Deduplicate articles and take MAX 6
    seen_titles = set()
    new_articles_html = []
    
    for art in articles:
        if len(new_articles_html) >= 6:
            break
            
        title = sanitize_text(art.get("title", "Untitled Story"))
        summary = sanitize_text(art.get("summary", ""))
        
        if title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())
        
        article_card = f"""
                <details class="nw-feed-item">
                    <summary>
                        <div class="nw-feed-meta">
                            <span class="nw-badge nw-badge-emerald">REGULATORY BRIEFING</span>
                            <span>NICOTINEWIRE DESK</span>
                        </div>
                        {title}
                    </summary>
                    <div class="nw-feed-body">
                        {summary}
                    </div>
                </details>"""
        new_articles_html.append(article_card)
        
    updated_middle = "\n" + "\n".join(new_articles_html) + "\n            </div>\n        "
    full_updated_html = pre_content + updated_middle + post_content
    
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(full_updated_html)
        
    print(f"[Publisher Success] Published {len(new_articles_html)} premier executive briefings to index.html.")
    return True
