import os
from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="NicotineWire API", docs_url=None, redoc_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/svg+xml",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".png": "image/png"
}

def get_file_response(rel_path: str):
    # Ensure safe path
    clean_path = os.path.normpath(rel_path).lstrip("/\\")
    full_path = os.path.join(BASE_DIR, clean_path)
    
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    _, ext = os.path.splitext(full_path)
    media_type = MEDIA_TYPES.get(ext.lower(), "application/octet-stream")
    
    with open(full_path, "rb") as f:
        content = f.read()
        
    return Response(content=content, media_type=media_type)

ROUTE_MAP = {
    "": "index.html",
    "main.py": "index.html",
    "index": "index.html",
    "index.html": "index.html",
    "directory": "directory.html",
    "directory.html": "directory.html",
    "reports": "reports.html",
    "reports.html": "reports.html",
    "pricing": "pricing.html",
    "pricing.html": "pricing.html",
    "b2b-case": "b2b-case.html",
    "b2b-case.html": "b2b-case.html",
    "insights": "newszoo-insights.html",
    "newszoo-insights": "newszoo-insights.html",
    "newszoo-insights.html": "newszoo-insights.html",
    "viewer": "report-template.html",
    "report-template": "report-template.html",
    "report-template.html": "report-template.html",
    "thank-you": "thank-you.html",
    "thank-you.html": "thank-you.html",
    "styles.css": "styles.css",
    "app.js": "app.js",
    "favicon.svg": "favicon.svg",
    "favicon.ico": "favicon.svg"
}

@app.get("/")
async def root():
    return get_file_response("index.html")

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    path_key = full_path.strip("/").lower()
    
    # Check if exact route alias exists
    if path_key in ROUTE_MAP:
        return get_file_response(ROUTE_MAP[path_key])
        
    # Check if direct static file exists (e.g. reports_pdf/NW-SYNTH-2026.pdf)
    local_file = os.path.join(BASE_DIR, full_path.strip("/"))
    if os.path.isfile(local_file):
        return get_file_response(full_path.strip("/"))
        
    # Check with .html appended
    if path_key + ".html" in ROUTE_MAP:
        return get_file_response(ROUTE_MAP[path_key + ".html"])

    raise HTTPException(status_code=404, detail="Page not found")
