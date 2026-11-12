"""
Routes for PDF Watermark Removal
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import shutil
from typing import List, Optional

from services.watermark_removal_service import WatermarkRemovalService
from utils.file_handler import validate_file_type, get_file_size, sanitize_filename, get_pdf_page_count, ALLOWED_PDF_TYPE, MAX_FILE_SIZE, MAX_PDF_PAGES

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
OUTPUT_DIR = BASE_DIR / "storage" / "outputs"

service = WatermarkRemovalService()


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF file for watermark removal"""
    
    temp_dir = UPLOAD_DIR / f"watermark_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        temp_path = temp_dir / sanitize_filename(file.filename)
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Validate file type
        if not validate_file_type(str(temp_path), {ALLOWED_PDF_TYPE}):
            temp_path.unlink()
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")
        
        # Validate file size
        if not get_file_size(str(temp_path)) <= MAX_FILE_SIZE:
            temp_path.unlink()
            raise HTTPException(status_code=400, detail=f"File too large: {file.filename}")
        
        return {
            "message": "PDF uploaded successfully",
            "filename": file.filename,
            "temp_path": str(temp_path),
            "temp_dir": str(temp_dir),
            "page_count": get_pdf_page_count(str(temp_path))
        }
    
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remove")
async def remove_watermark(
    file: UploadFile = File(...),
    output_name: str = Form("clean.pdf"),
    method: str = Form("auto")
):
    """Remove watermark from PDF"""
    
    temp_dir = UPLOAD_DIR / f"watermark_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        temp_path = temp_dir / sanitize_filename(file.filename)
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Validate file type
        if not validate_file_type(str(temp_path), {ALLOWED_PDF_TYPE}):
            temp_path.unlink()
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")
        
        # Validate file size
        if not get_file_size(str(temp_path)) <= MAX_FILE_SIZE:
            temp_path.unlink()
            raise HTTPException(status_code=400, detail=f"File too large: {file.filename}")
        
        # Generate output filename
        if not output_name.endswith('.pdf'):
            output_name += '.pdf'
        
        output_path = OUTPUT_DIR / sanitize_filename(output_name)
        
        # Remove watermark
        result_path = service.remove_watermark(
            pdf_path=str(temp_path),
            output_path=str(output_path),
            method=method
        )
        
        # Cleanup temp files
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return FileResponse(
            path=result_path,
            media_type="application/pdf",
            filename=output_name
        )
    
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))