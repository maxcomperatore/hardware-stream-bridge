from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="NicotineWire API")

# Serve static root files (CSS, JS, SVG)
@app.get("/styles.css")
def get_styles():
    return FileResponse("styles.css")

@app.get("/app.js")
def get_app_js():
    return FileResponse("app.js")

@app.get("/favicon.svg")
def get_favicon():
    return FileResponse("favicon.svg")

# Clean HTML Page Routes
@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.get("/directory")
def read_directory():
    return FileResponse("directory.html")

@app.get("/reports")
def read_reports():
    return FileResponse("reports.html")

@app.get("/pricing")
def read_pricing():
    return FileResponse("pricing.html")

@app.get("/b2b-case")
def read_b2b_case():
    return FileResponse("b2b-case.html")

@app.get("/insights")
def read_insights():
    return FileResponse("newszoo-insights.html")

@app.get("/viewer")
def read_viewer():
    return FileResponse("report-template.html")

@app.get("/thank-you")
def read_thank_you():
    return FileResponse("thank-you.html")
