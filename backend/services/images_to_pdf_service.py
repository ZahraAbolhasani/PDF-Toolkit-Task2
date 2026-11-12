"""
Service for converting images to PDF
"""
from PIL import Image
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional
import os


class ImagesToPDFService:
    """Service for converting images to PDF"""
    
    # Page size mappings (in points: 1 point = 1/72 inch)
    PAGE_SIZES = {
        "A4": (595, 842),
        "A3": (842, 1191),
        "A5": (420, 595),
        "Letter": (612, 792),
        "Legal": (612, 1008)
    }
    
    def convert(
        self,
        image_paths: List[str],
        output_path: str,
        page_size: str = "A4",
        orientation: str = "portrait",
        margin: int = 20
    ) -> str:
        """
        Convert multiple images to a single PDF
        
        Args:
            image_paths: List of paths to image files
            output_path: Path for output PDF
            page_size: Page size (A4, A3, A5, Letter, Legal, or 'fit')
            orientation: 'portrait' or 'landscape'
            margin: Margin in points
            
        Returns:
            Path to generated PDF
        """
        
        if not image_paths:
            raise ValueError("No images provided")
        
        # Create new PDF document
        doc = fitz.open()
        
        for img_path in image_paths:
            try:
                # Open image
                img = Image.open(img_path)
                
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Determine page dimensions
                if page_size.lower() == 'fit':
                    # Fit page to image dimensions (convert pixels to points)
                    img_width = img.width * 0.75  # Approximate conversion
                    img_height = img.height * 0.75
                    page_rect = fitz.Rect(0, 0, img_width, img_height)
                else:
                    # Use standard page size
                    width, height = self.PAGE_SIZES.get(page_size, self.PAGE_SIZES["A4"])
                    if orientation == "landscape":
                        width, height = height, width
                    page_rect = fitz.Rect(0, 0, width, height)
                
                # Create new page
                page = doc.new_page(width=page_rect.width, height=page_rect.height)
                
                # Calculate image placement
                if page_size.lower() == 'fit':
                    # Fill entire page
                    img_rect = page_rect
                else:
                    # Calculate scaled dimensions with margins
                    available_width = page_rect.width - (2 * margin)
                    available_height = page_rect.height - (2 * margin)
                    
                    # Scale image to fit while maintaining aspect ratio
                    img_aspect = img.width / img.height
                    avail_aspect = available_width / available_height
                    
                    if img_aspect > avail_aspect:
                        # Image is wider than available space
                        new_width = available_width
                        new_height = available_width / img_aspect
                    else:
                        # Image is taller than available space
                        new_height = available_height
                        new_width = available_height * img_aspect
                    
                    # Center the image
                    x = (page_rect.width - new_width) / 2
                    y = (page_rect.height - new_height) / 2
                    img_rect = fitz.Rect(x, y, x + new_width, y + new_height)
                
                # Insert image into PDF
                img_data = self._image_to_bytes(img)
                page.insert_image(img_rect, stream=img_data)
                
            except Exception as e:
                raise ValueError(f"Failed to process image {img_path}: {str(e)}")
        
        # Save PDF
        doc.save(output_path)
        doc.close()
        
        return output_path
    
    def _image_to_bytes(self, img: Image.Image) -> bytes:
        """Convert PIL Image to bytes"""
        import io
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr
    
    def reorder_images(self, image_paths: List[str], new_order: List[int]) -> List[str]:
        """Reorder images based on new order indices"""
        if len(new_order) != len(image_paths):
            raise ValueError("New order must have same length as image list")
        
        return [image_paths[i] for i in new_order]