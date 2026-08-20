import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="NicotineWire API", docs_url=None, redoc_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def serve_file(filename: str, media_type: str = None):
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type=media_type)
    raise HTTPException(status_code=404, detail="File not found")

# Static assets
@app.get("/styles.css")
def get_styles():
    return serve_file("styles.css", "text/css")

@app.get("/app.js")
def get_app_js():
    return serve_file("app.js", "application/javascript")

@app.get("/favicon.svg")
def get_favicon():
    return serve_file("favicon.svg", "image/svg+xml")

@app.get("/favicon.ico")
def get_favicon_ico():
    return serve_file("favicon.svg", "image/svg+xml")

# HTML Pages (Clean routes + .html fallbacks)
@app.get("/")
def get_index():
    return serve_file("index.html", "text/html")

@app.get("/index.html")
def get_index_html():
    return serve_file("index.html", "text/html")

@app.get("/directory")
@app.get("/directory.html")
def get_directory():
    return serve_file("directory.html", "text/html")

@app.get("/reports")
@app.get("/reports.html")
def get_reports():
    return serve_file("reports.html", "text/html")

@app.get("/pricing")
@app.get("/pricing.html")
def get_pricing():
    return serve_file("pricing.html", "text/html")

@app.get("/b2b-case")
@app.get("/b2b-case.html")
def get_b2b_case():
    return serve_file("b2b-case.html", "text/html")

@app.get("/insights")
@app.get("/newszoo-insights")
@app.get("/newszoo-insights.html")
def get_insights():
    return serve_file("newszoo-insights.html", "text/html")

@app.get("/viewer")
@app.get("/report-template")
@app.get("/report-template.html")
def get_viewer():
    return serve_file("report-template.html", "text/html")

@app.get("/thank-you")
@app.get("/thank-you.html")
def get_thank_you():
    return serve_file("thank-you.html", "text/html")

# PDF Reports Serving
@app.get("/reports_pdf/{pdf_name}")
def get_pdf(pdf_name: str):
    # sanitize filename to prevent directory traversal
    clean_name = os.path.basename(pdf_name)
    pdf_path = os.path.join(BASE_DIR, "reports_pdf", clean_name)
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename=clean_name)
    raise HTTPException(status_code=404, detail="PDF report not found")
