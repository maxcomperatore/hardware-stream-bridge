"""
Publisher Module for NicotineWire.
Takes generated B2B stories from CrewAI and updates nicotinewire/index.html with deduplication and clean section management.
"""

import os
import re
from typing import List, Dict

INDEX_PATH = os.path.join(os.path.dirname(__file__), "index.html")


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
        title = art.get("title", "Untitled Story").strip().replace("20XX", "2026").replace("M&Ac", "M&A").replace("**", "").replace("—", ", ").replace("--", ", ").replace("&mdash;", ", ")
        if title in seen_titles:
            continue
        seen_titles.add(title)
        
        meta = art.get("meta", "INTELLIGENCE WIRE | 2026-08-01 UTC").replace("20XX", "2026").replace("M&Ac", "M&A").replace("**", "").replace("—", ", ").replace("--", ", ").replace("&mdash;", ", ")
        summary = art.get("summary", "").replace("20XX", "2026").replace("M&Ac", "M&A").replace("**", "").replace("—", ", ").replace("--", ", ").replace("&mdash;", ", ")
        
        article_block = f"""
<article>
    <details>
        <summary><strong>{title}</strong></summary>
        <p><small>{meta}</small></p>
        <p>{summary}</p>
    </details>
</article>"""
        new_articles_html.append(article_block)
        
    wire_code = "\n" + "\n".join(new_articles_html) + "\n\n<hr>\n\n"
    updated_html = pre_content + wire_code + post_content
    
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(updated_html)
        
    print(f"[Publisher] Successfully published {len(new_articles_html)} unique stories to nicotinewire/index.html.")
    return True


def update_index_ticker(ticker_data: Dict[str, str]) -> bool:
    """Dynamically update the header ticker table in nicotinewire/index.html."""
    if not os.path.exists(INDEX_PATH):
        return False
        
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        syn_price = ticker_data.get("synthetic_price", "$3,450/kg")
        syn_change = ticker_data.get("synthetic_change", "+1.2%")
        leaf_price = ticker_data.get("leaf_price", "$3.12/kg")
        leaf_change = ticker_data.get("leaf_change", "+8.4%")
        pmta_count = ticker_data.get("pmta_count", "58")
        
        pattern = re.compile(r'<table border="1" cellpadding="6" cellspacing="0" width="100%">.*?</table>', re.DOTALL)
        
        new_ticker_html = f"""<table border="1" cellpadding="6" cellspacing="0" width="100%">
    <tr>
        <td><strong>SYNTHETIC L-NICOTINE:</strong> {syn_price} ({syn_change})</td>
        <td><strong>LEAF SPOT:</strong> {leaf_price} ({leaf_change})</td>
        <td><strong>ACTIVE PMTA DOCKETS:</strong> {pmta_count}</td>
        <td><a href="pricing.html"><strong>Pricing &amp; Membership</strong></a></td>
    </tr>
</table>"""
        
        updated_html = pattern.sub(new_ticker_html, html_content)
        with open(INDEX_PATH, "w", encoding="utf-8") as f:
            f.write(updated_html)
        print(f"[Publisher] Updated index.html ticker table (Active PMTA Dockets: {pmta_count}).")
        return True
    except Exception as e:
        print(f"[Publisher Warning] Could not update ticker: {e}")
        return False
