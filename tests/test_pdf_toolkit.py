"""
Test suite for PDF Toolkit
"""
import pytest
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from utils.file_handler import (
    sanitize_filename,
    validate_file_type,
    get_file_size,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_PDF_TYPE
)
from services.images_to_pdf_service import ImagesToPDFService
from services.pdf_to_word_service import PDFToWordService
from services.watermark_removal_service import WatermarkRemovalService


class TestFileHandler:
    """Test file handling utilities"""
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        assert sanitize_filename("normal.pdf") == "normal.pdf"
        assert sanitize_filename("file with spaces.pdf") == "file_with_spaces.pdf"
        assert sanitize_filename("../etc/passwd") == "etc_passwd"
        assert sanitize_filename(".hidden") == "_hidden"
        assert sanitize_filename("file<script>.pdf") == "file_script_.pdf"
    
    def test_validate_file_type(self):
        """Test file type validation"""
        # This test requires actual files, so it's a placeholder
        pass
    
    def test_get_file_size(self):
        """Test file size checking"""
        # This test requires actual files, so it's a placeholder
        pass


class TestImagesToPDFService:
    """Test Images to PDF service"""
    
    def test_init(self):
        """Test service initialization"""
        service = ImagesToPDFService()
        assert service is not None
        assert "A4" in service.PAGE_SIZES
        assert "Letter" in service.PAGE_SIZES
    
    def test_page_sizes(self):
        """Test page size mappings"""
        service = ImagesToPDFService()
        assert service.PAGE_SIZES["A4"] == (595, 842)
        assert service.PAGE_SIZES["A3"] == (842, 1191)
    
    def test_reorder_images(self):
        """Test image reordering"""
        service = ImagesToPDFService()
        images = ["img1.jpg", "img2.jpg", "img3.jpg"]
        new_order = [2, 0, 1]
        result = service.reorder_images(images, new_order)
        assert result == ["img3.jpg", "img1.jpg", "img2.jpg"]


class TestPDFToWordService:
    """Test PDF to Word service"""
    
    def test_init(self):
        """Test service initialization"""
        service = PDFToWordService()
        assert service is not None
    
    def test_parse_page_range(self):
        """Test page range parsing"""
        service = PDFToWordService()
        assert service._parse_page_range(10, None) == list(range(1, 11))
        assert service._parse_page_range(10, "1-5") == [1, 2, 3, 4, 5]
        assert service._parse_page_range(10, "1,3,5") == [1, 3, 5]
        assert service._parse_page_range(10, "8-10") == [8, 9, 10]


class TestWatermarkRemovalService:
    """Test Watermark removal service"""
    
    def test_init(self):
        """Test service initialization"""
        service = WatermarkRemovalService()
        assert service is not None
        assert len(service.WATERMARK_TEXT_PATTERNS) > 0
    
    def test_is_watermark_text(self):
        """Test watermark text detection"""
        service = WatermarkRemovalService()
        assert service._is_watermark_text("DRAFT") == True
        assert service._is_watermark_text("CONFIDENTIAL") == True
        assert service._is_watermark_text("SAMPLE") == True
        assert service._is_watermark_text("Hello World") == False
        assert service._is_watermark_text("This is a normal text") == False


class TestProjectStructure:
    """Test project structure"""
    
    def test_required_files_exist(self):
        """Test that all required files exist"""
        base_dir = Path(__file__).parent.parent
        
        required_files = [
            "README.md",
            "LEARNING-NOTES.md",
            "UI-UX-DOCUMENT.md",
            "requirements.txt",
            "start.bat",
            "setup.bat",
            ".gitignore",
            "backend/main.py",
            "backend/utils/file_handler.py",
            "backend/services/images_to_pdf_service.py",
            "backend/services/pdf_to_word_service.py",
            "backend/services/watermark_removal_service.py",
            "backend/routes/images_to_pdf.py",
            "backend/routes/pdf_to_word.py",
            "backend/routes/watermark_removal.py",
            "frontend/index.html",
            "frontend/style.css",
            "frontend/script.js",
        ]
        
        for file_path in required_files:
            full_path = base_dir / file_path
            assert full_path.exists(), f"Required file not found: {file_path}"
    
    def test_storage_directories_exist(self):
        """Test that storage directories exist"""
        base_dir = Path(__file__).parent.parent
        
        required_dirs = [
            "storage/uploads",
            "storage/outputs",
        ]
        
        for dir_path in required_dirs:
            full_path = base_dir / dir_path
            assert full_path.exists(), f"Required directory not found: {dir_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])