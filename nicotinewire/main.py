import os
from fastapi import FastAPI, Response, HTTPException

app = FastAPI(title="NicotineWire API", docs_url=None, redoc_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def read_file(filename: str):
    path = os.path.join(BASE_DIR, filename)
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return f.read()
    return None

# Explicit static asset endpoints with guaranteed Content-Type headers
@app.get("/styles.css")
@app.get("/styles.css/")
async def serve_styles():
    content = read_file("styles.css")
    if content:
        return Response(
            content=content,
            media_type="text/css; charset=utf-8",
            headers={
                "Content-Type": "text/css; charset=utf-8",
                "Cache-Control": "public, max-age=3600"
            }
        )
    raise HTTPException(status_code=404, detail="styles.css not found")

@app.get("/app.js")
@app.get("/app.js/")
async def serve_app_js():
    content = read_file("app.js")
    if content:
        return Response(
            content=content,
            media_type="application/javascript; charset=utf-8",
            headers={
                "Content-Type": "application/javascript; charset=utf-8",
                "Cache-Control": "public, max-age=3600"
            }
        )
    raise HTTPException(status_code=404, detail="app.js not found")

@app.get("/favicon.svg")
@app.get("/favicon.ico")
async def serve_favicon():
    content = read_file("favicon.svg")
    if content:
        return Response(
            content=content,
            media_type="image/svg+xml",
            headers={
                "Content-Type": "image/svg+xml",
                "Cache-Control": "public, max-age=86400"
            }
        )
    raise HTTPException(status_code=404, detail="favicon not found")

# PDF Reports handler
@app.get("/reports_pdf/{pdf_name}")
async def serve_pdf(pdf_name: str):
    clean_name = os.path.basename(pdf_name)
    content = read_file(os.path.join("reports_pdf", clean_name))
    if content:
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{clean_name}"'}
        )
    raise HTTPException(status_code=404, detail="PDF not found")

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
}

@app.get("/")
async def root():
    content = read_file("index.html")
    if content:
        return Response(content=content, media_type="text/html; charset=utf-8", headers={"Content-Type": "text/html; charset=utf-8"})
    raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    path_key = full_path.strip("/").lower()
    
    # Handle styles/js if hit via catch-all
    if path_key == "styles.css":
        return await serve_styles()
    if path_key == "app.js":
        return await serve_app_js()
    if path_key in ["favicon.svg", "favicon.ico"]:
        return await serve_favicon()
        
    if path_key in ROUTE_MAP:
        target_html = ROUTE_MAP[path_key]
        content = read_file(target_html)
        if content:
            return Response(content=content, media_type="text/html; charset=utf-8", headers={"Content-Type": "text/html; charset=utf-8"})
            
    if path_key + ".html" in ROUTE_MAP:
        target_html = ROUTE_MAP[path_key + ".html"]
        content = read_file(target_html)
        if content:
            return Response(content=content, media_type="text/html; charset=utf-8", headers={"Content-Type": "text/html; charset=utf-8"})

    raise HTTPException(status_code=404, detail="Page not found")
