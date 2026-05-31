from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import io
import os
import database
import parser

app = FastAPI(title="Knob Monster - Vintage Synth Patch Manager")

# Ensure static and templates directories exist
os.makedirs("d:/crew/experiment/templates", exist_ok=True)
os.makedirs("d:/crew/experiment/static", exist_ok=True)

# Templates
templates = Jinja2Templates(directory="d:/crew/experiment/templates")

# Mount Static Files
app.mount("/static", StaticFiles(directory="d:/crew/experiment/static"), name="static")

# Initialize SQLite database and copy assets on startup
@app.on_event("startup")
async def startup_event():
    database.init_db()
    import shutil
    src_dir = "C:/Users/Usuario/.gemini/antigravity/brain/21cc624c-71d6-4620-83a8-f77a95f2af34"
    dest_dir = "d:/crew/experiment/static"
    os.makedirs(dest_dir, exist_ok=True)
    
    hero_src = os.path.join(src_dir, "vintage_synth_hero_1780240317485.png")
    if os.path.exists(hero_src):
        shutil.copy(hero_src, os.path.join(dest_dir, "vintage_synth_hero.png"))
        
    detail_src = os.path.join(src_dir, "studio_detail_1780240351621.png")
    if os.path.exists(detail_src):
        shutil.copy(detail_src, os.path.join(dest_dir, "studio_detail.png"))

    camera_src = os.path.join(src_dir, "vintage_camera_404_1780240561882.png")
    if os.path.exists(camera_src):
        shutil.copy(camera_src, os.path.join(dest_dir, "vintage_camera_404.png"))

    troll_src = os.path.join(src_dir, "troll.png")
    troll_dest = os.path.join(dest_dir, "troll.png")
    if os.path.exists(troll_src):
        shutil.copy(troll_src, troll_dest)
        
    if os.path.exists(troll_dest):
        shutil.copy(troll_dest, os.path.join(dest_dir, "logo.png"))
    else:
        logo_src = os.path.join(src_dir, "vaultsynth_logo_1780240683932.png")
        if os.path.exists(logo_src):
            shutil.copy(logo_src, os.path.join(dest_dir, "logo.png"))

    # Copy green and gold trolls
    for filename, dest_filename in [("troll (1).png", "troll_green.png"), ("troll (2).png", "troll_gold.png")]:
        path_dest = os.path.join(dest_dir, filename)
        path_src = os.path.join(src_dir, filename)
        if os.path.exists(path_dest):
            shutil.copy(path_dest, os.path.join(dest_dir, dest_filename))
        elif os.path.exists(path_src):
            shutil.copy(path_src, os.path.join(dest_dir, dest_filename))

    handshake_src = os.path.join(src_dir, "midi_handshake_1780240701609.png")
    if os.path.exists(handshake_src):
        shutil.copy(handshake_src, os.path.join(dest_dir, "midi_handshake.png"))

    extraction_src = os.path.join(src_dir, "index_extraction_1780240720083.png")
    if os.path.exists(extraction_src):
        shutil.copy(extraction_src, os.path.join(dest_dir, "index_extraction.png"))

    recall_src = os.path.join(src_dir, "recall_button_1780240735209.png")
    if os.path.exists(recall_src):
        shutil.copy(recall_src, os.path.join(dest_dir, "recall_button.png"))

# Custom 404 Error handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    banks = database.get_all_banks()
    return templates.TemplateResponse("index.html", {"request": request, "banks": banks})

@app.get("/banks", response_class=HTMLResponse)
async def get_banks(request: Request):
    banks = database.get_all_banks()
    return templates.TemplateResponse("bank_list.html", {"request": request, "banks": banks})

@app.get("/banks/{bank_id}", response_class=HTMLResponse)
async def get_bank_details(request: Request, bank_id: int):
    bank = database.get_bank(bank_id)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return templates.TemplateResponse("patch_list.html", {"request": request, "bank": bank})

@app.post("/banks", response_class=HTMLResponse)
async def create_bank(
    request: Request,
    name: str = Form(...),
    synth_model: str = Form(...),
    sysex_hex: str = Form(...)
):
    try:
        # Convert hex string back to bytes for parsing
        # Strip any whitespace/newlines that might be in the hex string
        clean_hex = sysex_hex.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        sysex_bytes = bytes.fromhex(clean_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid hexadecimal string data")
    
    # Parse voice names based on model
    if synth_model == "Yamaha DX7":
        patch_names = parser.parse_dx7_sysex(sysex_bytes)
    elif synth_model == "Roland Juno-106":
        patch_names = parser.parse_juno106_sysex(sysex_bytes)
    elif synth_model == "Korg M1":
        patch_names = parser.parse_korg_m1_sysex(sysex_bytes)
    else:
        patch_names = parser.parse_generic_sysex(sysex_bytes)
        
    # Save to database
    database.save_bank(name, synth_model, clean_hex, patch_names)
    
    # Return re-rendered bank list
    banks = database.get_all_banks()
    return templates.TemplateResponse("bank_list.html", {"request": request, "banks": banks})

@app.post("/banks/upload", response_class=HTMLResponse)
async def upload_bank_file(
    request: Request,
    name: str = Form(...),
    synth_model: str = Form(...),
    file: UploadFile = File(...)
):
    # Read raw bytes of the file
    sysex_bytes = await file.read()
    sysex_hex = sysex_bytes.hex()
    
    # Parse voice names
    if synth_model == "Yamaha DX7":
        patch_names = parser.parse_dx7_sysex(sysex_bytes)
    elif synth_model == "Roland Juno-106":
        patch_names = parser.parse_juno106_sysex(sysex_bytes)
    elif synth_model == "Korg M1":
        patch_names = parser.parse_korg_m1_sysex(sysex_bytes)
    else:
        patch_names = parser.parse_generic_sysex(sysex_bytes)
        
    # Save to database
    database.save_bank(name, synth_model, sysex_hex, patch_names)
    
    # Return re-rendered bank list
    banks = database.get_all_banks()
    return templates.TemplateResponse("bank_list.html", {"request": request, "banks": banks})

@app.delete("/banks/{bank_id}", response_class=HTMLResponse)
async def delete_bank(request: Request, bank_id: int):
    database.delete_bank(bank_id)
    banks = database.get_all_banks()
    return templates.TemplateResponse("bank_list.html", {"request": request, "banks": banks})

@app.get("/banks/{bank_id}/download")
async def download_bank(bank_id: int):
    bank = database.get_bank(bank_id)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
        
    try:
        sysex_bytes = bytes.fromhex(bank["sysex_hex"])
    except ValueError:
        raise HTTPException(status_code=500, detail="Database data corruption: invalid hex")
        
    # Stream the raw bytes back as a file download
    file_stream = io.BytesIO(sysex_bytes)
    
    # Generate a clean filename
    safe_name = bank["name"].lower().replace(" ", "_")
    filename = f"{safe_name}.syx"
    
    return StreamingResponse(
        file_stream, 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/banks/{bank_id}/hex")
async def get_bank_hex(bank_id: int):
    bank = database.get_bank(bank_id)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return {"sysex_hex": bank["sysex_hex"]}
