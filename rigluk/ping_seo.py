import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import json
import sys

def ping_indexnow(local=False):
    sitemap_url = "http://127.0.0.1:8000/sitemap.xml" if local else "https://rigluk.com/sitemap.xml"
    print(f"Fetching sitemap from {sitemap_url}...")
    try:
        req = urllib.request.Request(sitemap_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            sitemap_xml = response.read()
    except urllib.error.URLError as e:
        print(f"Error fetching sitemap: {e}")
        print("Please make sure the app is running locally if using --local flag, or check your connection.")
        sys.exit(1)

    try:
        root = ET.fromstring(sitemap_xml)
    except ET.ParseError as e:
        print(f"Error parsing XML sitemap: {e}")
        sys.exit(1)

    urls = []
    # Handle XML namespace
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    for url_tag in root.findall('.//ns:loc', ns):
        url = url_tag.text
        if local:
            # Swap production domain for local testing if requested
            url = url.replace("https://rigluk.com", "http://127.0.0.1:8000")
        urls.append(url)

    print(f"Found {len(urls)} URLs to submit:")
    for u in urls:
        print(f" - {u}")

    payload = {
        "host": "rigluk.com" if not local else "127.0.0.1:8000",
        "key": "7f8b9e6c5d4c3b2a1a0f9e8d7c6b5a4f",
        "keyLocation": "https://rigluk.com/7f8b9e6c5d4c3b2a1a0f9e8d7c6b5a4f.txt" if not local else "http://127.0.0.1:8000/7f8b9e6c5d4c3b2a1a0f9e8d7c6b5a4f.txt",
        "urlList": urls
    }

    # Submit to IndexNow
    indexnow_endpoint = "https://api.indexnow.org/IndexNow"
    print(f"Submitting payload to IndexNow: {indexnow_endpoint}...")
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        indexnow_endpoint,
        data=data,
        headers={'Content-Type': 'application/json; charset=utf-8'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            print(f"Success! Response Status Code: {status}")
            print("Search engines participating in IndexNow will now update their indexes.")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error submitting to IndexNow: {e.code} - {e.reason}")
        print(e.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print(f"URL Error submitting to IndexNow: {e}")

if __name__ == "__main__":
    local_flag = "--local" in sys.argv
    ping_indexnow(local=local_flag)
