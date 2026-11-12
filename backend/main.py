"""
PDF Toolkit - Backend Main Application
FastAPI server for PDF processing operations
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
from pathlib import Path
from typing import Optional, List
import uuid

from routes import images_to_pdf, pdf_to_word, watermark_removal
from utils.file_handler import validate_file_type, get_file_size, sanitize_filename

# Initialize FastAPI app
app = FastAPI(
    title="PDF Toolkit API",
    description="Multi-purpose PDF processing web application",
    version="1.0.0"
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(images_to_pdf.router, prefix="/api/images-to-pdf", tags=["Images to PDF"])
app.include_router(pdf_to_word.router, prefix="/api/pdf-to-word", tags=["PDF to Word"])
app.include_router(watermark_removal.router, prefix="/api/watermark-removal", tags=["Watermark Removal"])

# Storage directories
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
OUTPUT_DIR = BASE_DIR / "storage" / "outputs"

# Ensure storage directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
async def serve_homepage():
    """Serve the main application page"""
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "PDF Toolkit API is running"}


@app.get("/api/files")
async def list_stored_files():
    """List all stored output files"""
    files = []
    if OUTPUT_DIR.exists():
        for f in OUTPUT_DIR.iterdir():
            if f.is_file():
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime
                })
    return {"files": files}


@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """Delete a stored file"""
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        file_path.unlink()
        return {"message": "File deleted successfully"}
    raise HTTPException(status_code=404, detail="File not found")


# Mount frontend static files at root — must be the LAST route, so that
# /style.css, /script.js and /assets/* are served, while /health and
# /api/* (registered above) always win.
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010)