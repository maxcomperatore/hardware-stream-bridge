"""
Knob.Monster - KnobKraft-orm SysEx API Bridge Module
Exposes 80+ synthesizer SysEx adaptation parsers directly via FastAPI REST API.
"""

import sys
import os
import glob
import importlib
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("knobkraft_api")

# Add KnobKraft adaptations directory to Python path
ADAPTATIONS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "knobkraft_src", "adaptations"))
if ADAPTATIONS_DIR not in sys.path:
    sys.path.insert(0, ADAPTATIONS_DIR)

from knobkraft.sysex import splitSysexMessage, syxToString, splitSysex

ADAPTER_CACHE: Dict[str, Any] = {}
SYNTH_METADATA: Dict[str, Dict[str, Any]] = {}

def initialize_adapters():
    """Scan and index all KnobKraft adaptation modules."""
    global ADAPTER_CACHE, SYNTH_METADATA
    if ADAPTER_CACHE:
        return

    pattern = os.path.join(ADAPTATIONS_DIR, "*.py")
    for py_file in glob.glob(pattern):
        mod_name = os.path.splitext(os.path.basename(py_file))[0]
        if mod_name.startswith("test_") or mod_name in ("conftest", "PythonUtils"):
            continue
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "name"):
                display_name = mod.name()
                ADAPTER_CACHE[mod_name] = mod
                SYNTH_METADATA[mod_name] = {
                    "id": mod_name,
                    "name": display_name,
                    "has_extract_bank": hasattr(mod, "extractPatchesFromBank"),
                    "has_name_from_dump": hasattr(mod, "nameFromDump"),
                    "has_parse_bank": hasattr(mod, "parse_bank"),
                }
        except Exception as err:
            logger.warning(f"Could not load adaptation {mod_name}: {err}")

    logger.info(f"Initialized {len(ADAPTER_CACHE)} KnobKraft synth adaptations.")

# Initialize on module load
initialize_adapters()

router = APIRouter(prefix="/api/v1/knobkraft", tags=["KnobKraft SysEx Engine"])

@router.get("/synths")
def list_supported_synths():
    """Returns a list of all 80+ supported synthesizers and their capabilities."""
    synths_list = sorted(list(SYNTH_METADATA.values()), key=lambda x: x["name"].lower())
    return {
        "status": "success",
        "total_synths": len(synths_list),
        "synths": synths_list
    }

@router.post("/parse")
async def parse_sysex_file(
    synth_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Parses an uploaded .syx MIDI SysEx file using the specified KnobKraft synth adaptation.
    Returns parsed patch count, individual patch names, hex representations, and patch indices.
    """
    if synth_id not in ADAPTER_CACHE:
        raise HTTPException(
            status_code=400,
            detail=f"Synthesizer ID '{synth_id}' not found. Check GET /api/v1/knobkraft/synths for available IDs."
        )

    adapter = ADAPTER_CACHE[synth_id]
    contents = await file.read()
    byte_list = list(contents)

    patches_output = []
    
    try:
        single_patches = []
        
        # Method A: KnobKraft extractPatchesFromBank
        if hasattr(adapter, "extractPatchesFromBank"):
            raw_extracted = adapter.extractPatchesFromBank(byte_list)
            if raw_extracted:
                single_patches = splitSysexMessage(raw_extracted)
        
        # Method B: KnobKraft parse_bank
        if not single_patches and hasattr(adapter, "parse_bank"):
            res = adapter.parse_bank(byte_list)
            if isinstance(res, list):
                single_patches = res

        # Method C: Generic splitSysex fallback
        if not single_patches:
            single_patches = splitSysex(byte_list)

        for idx, patch_bytes in enumerate(single_patches):
            name_str = f"Patch {idx+1:02d}"
            
            # Extract name using adapter.nameFromDump if available
            if hasattr(adapter, "nameFromDump"):
                try:
                    extracted_name = adapter.nameFromDump(patch_bytes)
                    if extracted_name and isinstance(extracted_name, str) and extracted_name.strip():
                        name_str = extracted_name.strip()
                except Exception:
                    pass

            hex_str = syxToString(patch_bytes) if isinstance(patch_bytes, list) else ""

            patches_output.append({
                "index": idx + 1,
                "name": name_str,
                "size_bytes": len(patch_bytes) if isinstance(patch_bytes, list) else 0,
                "hex_preview": hex_str[:60] + "..." if len(hex_str) > 60 else hex_str
            })

        return {
            "status": "success",
            "synth_id": synth_id,
            "synth_name": SYNTH_METADATA[synth_id]["name"],
            "file_name": file.filename,
            "file_size_bytes": len(contents),
            "patch_count": len(patches_output),
            "patches": patches_output
        }

    except Exception as err:
        logger.error(f"Error parsing SysEx with adapter {synth_id}: {err}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse SysEx with adapter '{synth_id}': {str(err)}"
        )

@router.post("/detect")
async def detect_sysex_synth(file: UploadFile = File(...)):
    """
    Attempts to auto-detect which synthesizer generated the uploaded SysEx file
    by testing against all KnobKraft adaptation signatures.
    """
    contents = await file.read()
    byte_list = list(contents)
    
    matches = []
    
    for synth_id, adapter in ADAPTER_CACHE.items():
        try:
            if hasattr(adapter, "isPartOfBankDump") and adapter.isPartOfBankDump(byte_list):
                matches.append({
                    "synth_id": synth_id,
                    "name": SYNTH_METADATA[synth_id]["name"],
                    "match_type": "bank_dump"
                })
            elif hasattr(adapter, "isEditBufferDump") and adapter.isEditBufferDump(byte_list):
                matches.append({
                    "synth_id": synth_id,
                    "name": SYNTH_METADATA[synth_id]["name"],
                    "match_type": "edit_buffer"
                })
        except Exception:
            continue

    return {
        "status": "success",
        "file_name": file.filename,
        "file_size_bytes": len(contents),
        "matches_count": len(matches),
        "matches": matches
    }
