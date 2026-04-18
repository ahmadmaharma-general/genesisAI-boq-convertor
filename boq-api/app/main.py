"""FastAPI application exposing the BOQ extraction pipeline."""

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.boq_extractor import extract_boq
from app.dwg_to_dxf import ensure_dxf, ODANotFoundError, ConversionError

app = FastAPI(
    title="GenesisAI BOQ Convertor API",
    version="1.0.0",
    description="Accepts DXF or DWG files and returns a Bill of Quantities (BOQ).",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/boq")
async def create_boq(file: UploadFile = File(...)):
    """Upload a DXF or DWG file and receive a structured BOQ response.

    Returns JSON with a `items` array, each containing:
    - item_no, description, layer, quantity, unit
    """
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in {".dxf", ".dwg"}:
        raise HTTPException(status_code=400, detail="Only .dxf and .dwg files are supported.")

    with tempfile.TemporaryDirectory() as tmp:
        upload_path = Path(tmp) / (file.filename or f"upload{suffix}")
        upload_path.write_bytes(await file.read())

        try:
            dxf_path = ensure_dxf(str(upload_path), output_dir=tmp)
        except ODANotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except ConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        try:
            boq_items = extract_boq(dxf_path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"BOQ extraction failed: {exc}")

    return JSONResponse(content={"items": boq_items})
