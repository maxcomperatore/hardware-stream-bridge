import os
import re

INDEX_PATH = r"d:\crew\experiment\nicotinewire\index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Extract header and footer bounds
start_heading = "<h2>REGULATORY & M&A INTELLIGENCE WIRE</h2>"
end_heading = "<h2>B2B NICOTINE SUPPLY CHAIN DIRECTORY</h2>"

start_pos = content.find(start_heading)
end_pos = content.find(end_heading)

if start_pos == -1 or end_pos == -1:
    print("Headings not found")
    exit(1)

pre_content = content[:start_pos + len(start_heading)]
post_content = content[end_pos:]
wire_section = content[start_pos + len(start_heading):end_pos]

# Parse details blocks
pattern = re.compile(r'<article>\s*<details>\s*<summary><strong>(.*?)</strong></summary>\s*<p><small>(.*?)</small></p>\s*<p>(.*?)</p>\s*</details>\s*</article>', re.DOTALL)

matches = pattern.findall(wire_section)

# Noise keywords to strictly drop
noise_keywords = [
    "freeze-dried plasma", "tempo digital health", "color additive", "pcsk9", "ivermectin", 
    "horses", "drug manufacturing", "sickle cell", "tregzi", "blood cancer", "screwworm"
]

unique_stories = []
seen_titles = set()

for title, meta, text in matches:
    clean_title = title.strip()
    full_text = (clean_title + " " + text).lower()
    
    # Check noise
    if any(nk in full_text for nk in noise_keywords):
        continue
        
    # Check duplicates
    if clean_title in seen_titles:
        continue
        
    seen_titles.add(clean_title)
    unique_stories.append((clean_title, meta.strip(), text.strip()))

print(f"Retained {len(unique_stories)} unique, pure tobacco B2B stories.")

# Rebuild HTML
story_blocks = []
for title, meta, text in unique_stories:
    block = f"""
<article>
    <details>
        <summary><strong>{title}</strong></summary>
        <p><small>{meta}</small></p>
        <p>{text}</p>
    </details>
</article>"""
    story_blocks.append(block)

new_wire = "\n" + "\n".join(story_blocks) + "\n\n<hr>\n\n"
updated_html = pre_content + new_wire + post_content

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(updated_html)

print("index.html deduplicated and cleaned successfully!")
