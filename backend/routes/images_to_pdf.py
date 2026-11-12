"""
Routes for Images to PDF conversion
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import shutil
from typing import List, Optional

from services.images_to_pdf_service import ImagesToPDFService
from utils.file_handler import validate_file_type, get_file_size, sanitize_filename, ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE, MAX_IMAGES

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
OUTPUT_DIR = BASE_DIR / "storage" / "outputs"

service = ImagesToPDFService()


@router.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    """Upload multiple images for PDF conversion"""
    
    if len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES} images allowed")
    
    uploaded_files = []
    temp_dir = UPLOAD_DIR / f"temp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        for file in files:
            # Save to temp
            temp_path = temp_dir / sanitize_filename(file.filename)
            with open(temp_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Validate file
            if not validate_file_type(str(temp_path), ALLOWED_IMAGE_TYPES):
                temp_path.unlink()
                raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")
            
            if not get_file_size(str(temp_path)) <= MAX_FILE_SIZE:
                temp_path.unlink()
                raise HTTPException(status_code=400, detail=f"File too large: {file.filename}")
            
            uploaded_files.append({
                "name": file.filename,
                "path": str(temp_path),
                "size": len(content)
            })
        
        return {
            "message": "Files uploaded successfully",
            "files": uploaded_files,
            "temp_dir": str(temp_dir)
        }
    
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert")
async def convert_images_to_pdf(
    files: List[UploadFile] = File(...),
    output_name: str = Form("output.pdf"),
    page_size: str = Form("A4"),
    orientation: str = Form("portrait"),
    margin: int = Form(20)
):
    """Convert images to PDF with specified settings"""
    
    if len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES} images allowed")
    
    # Create temp directory for this conversion
    temp_dir = UPLOAD_DIR / f"convert_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    
    try:
        # Save all uploaded files
        for file in files:
            temp_path = temp_dir / sanitize_filename(file.filename)
            with open(temp_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Validate
            if not validate_file_type(str(temp_path), ALLOWED_IMAGE_TYPES):
                temp_path.unlink()
                raise HTTPException(status_code=400, detail=f"Invalid image: {file.filename}")
            
            saved_files.append(str(temp_path))
        
        # Generate output filename
        if not output_name.endswith('.pdf'):
            output_name += '.pdf'
        
        output_path = OUTPUT_DIR / sanitize_filename(output_name)
        
        # Convert to PDF
        result_path = service.convert(
            image_paths=saved_files,
            output_path=str(output_path),
            page_size=page_size,
            orientation=orientation,
            margin=margin
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


@router.get("/preview/{file_id}")
async def preview_image(file_id: str):
    """Get preview of uploaded image"""
    # This would serve a preview of the image
    raise HTTPException(status_code=501, detail="Preview not implemented yet")