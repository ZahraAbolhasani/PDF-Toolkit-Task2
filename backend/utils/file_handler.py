"""
Utility functions for file handling and validation
"""
import os
import re
import uuid
from pathlib import Path
from typing import List
import magic

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PDF_TYPE = "application/pdf"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_IMAGES = 20
MAX_PDF_PAGES = 100


def get_file_mime_type(file_path: str) -> str:
    """Get actual MIME type of file using magic bytes"""
    try:
        return magic.from_file(file_path, mime=True)
    except Exception:
        return "unknown"


def validate_file_type(file_path: str, allowed_types: set) -> bool:
    """Validate file type using actual content, not just extension"""
    mime_type = get_file_mime_type(file_path)
    return mime_type in allowed_types


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    return os.path.getsize(file_path)


def validate_file_size(file_path: str, max_size: int = MAX_FILE_SIZE) -> bool:
    """Validate file size"""
    return os.path.getsize(file_path) <= max_size


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and injection"""
    # Remove path components
    filename = os.path.basename(filename)
    # Remove special characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Prevent hidden files
    if filename.startswith('.'):
        filename = '_' + filename
    return filename


def generate_unique_filename(original_name: str, extension: str = None) -> str:
    """Generate unique filename to avoid collisions"""
    base_name = Path(original_name).stem
    if extension is None:
        extension = Path(original_name).suffix
    unique_id = str(uuid.uuid4())[:8]
    return f"{base_name}_{unique_id}{extension}"


def save_upload_file(upload_file, destination_dir: Path) -> str:
    """Save uploaded file to destination directory"""
    filename = sanitize_filename(upload_file.filename)
    file_path = destination_dir / filename
    
    # Handle name collisions
    counter = 1
    while file_path.exists():
        name_parts = filename.split('.')
        if len(name_parts) > 1:
            name = '.'.join(name_parts[:-1])
            ext = '.' + name_parts[-1]
            file_path = destination_dir / f"{name}_{counter}{ext}"
        else:
            file_path = destination_dir / f"{filename}_{counter}"
        counter += 1
    
    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())
    
    return str(file_path)


def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary files"""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def get_pdf_page_count(file_path: str) -> int:
    """Get number of pages in PDF file"""
    try:
        import fitz
        doc = fitz.open(file_path)
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def is_pdf_encrypted(file_path: str) -> bool:
    """Check if PDF is encrypted/password protected"""
    try:
        import fitz
        doc = fitz.open(file_path)
        is_enc = doc.is_encrypted
        doc.close()
        return is_enc
    except Exception:
        return True