"""
Service for converting PDF to Word

Text is extracted line by line (spans of one visual line are joined into a
single paragraph) so the Word document keeps the original reading order.
Persian/Arabic lines get RTL paragraph direction and right alignment.
"""
from pathlib import Path
from typing import List, Optional
import subprocess
import os
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

# Persian / Arabic character ranges (incl. presentation forms + ZWNJ/marks)
_RTL_CHARS = re.compile(
    "[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)


class PDFToWordService:
    """Service for converting PDF to Word"""

    def convert(
        self,
        pdf_path: str,
        output_path: str,
        page_range: Optional[str] = None
    ) -> str:
        """
        Convert PDF to Word document

        Args:
            pdf_path: Path to input PDF file
            output_path: Path for output Word document
            page_range: Optional page range (e.g., "1-5", "1,3,5" or "all")

        Returns:
            Path to generated Word document
        """

        try:
            # Try to convert using PyMuPDF and python-docx
            return self._convert_with_pymupdf(pdf_path, output_path, page_range)
        except Exception:
            # Fallback if anything goes wrong in the primary path
            return self._convert_with_tesseract(pdf_path, output_path, page_range)

    def _convert_with_pymupdf(
        self,
        pdf_path: str,
        output_path: str,
        page_range: Optional[str] = None
    ) -> str:
        """Convert PDF to Word using PyMuPDF (recommended for PDFs with text)"""

        doc = fitz.open(pdf_path)

        # Handle page range
        pages = self._parse_page_range(len(doc), page_range)

        # Create new Word document
        word_doc = Document()

        for page_num in pages:
            if page_num < 1 or page_num > len(doc):
                continue

            page = doc.load_page(page_num - 1)

            text_dict = page.get_text("dict")
            image_list = page.get_images()

            # Add page heading if multiple pages are converted
            if len(pages) > 1:
                word_doc.add_heading(f"Page {page_num}", level=1)

            # Extract text, one Word paragraph per visual line
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:  # 0 = text block
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue

                    # PyMuPDF stores RTL lines in visual order (left to
                    # right); reverse the span order so the joined string
                    # is in logical reading order
                    direction = line.get("dir", (1.0, 0.0))
                    if direction[0] < 0:
                        spans = list(reversed(spans))

                    text = "".join(s.get("text", "") for s in spans)
                    text = text.strip()
                    if not text:
                        continue

                    paragraph = word_doc.add_paragraph(text)
                    self._apply_text_direction(paragraph, text)

            # Extract and add images
            for img_info in image_list:
                try:
                    xref = img_info[0]
                    pix = fitz.Pixmap(doc, xref)

                    # Normalize colorspace (CMYK etc.) then convert to PIL
                    if pix.colorspace not in (fitz.csRGB, fitz.csGRAY):
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    mode = "L" if pix.colorspace == fitz.csGRAY else "RGB"
                    pil_img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

                    # Save image to temp buffer
                    img_bytes = io.BytesIO()
                    pil_img.save(img_bytes, format="PNG")
                    img_bytes.seek(0)

                    # Add image to document
                    word_doc.add_picture(img_bytes, width=200)  # Default width

                except Exception:
                    # Skip if image cannot be processed
                    pass

        doc.close()
        word_doc.save(output_path)

        return output_path

    def _convert_with_tesseract(
        self,
        pdf_path: str,
        output_path: str,
        page_range: Optional[str] = None
    ) -> str:
        """Fallback: plain text extraction (for scanned PDFs OCR would be needed)"""

        doc = fitz.open(pdf_path)
        pages = self._parse_page_range(len(doc), page_range)

        word_doc = Document()

        for page_num in pages:
            if page_num < 1 or page_num > len(doc):
                continue

            page = doc.load_page(page_num - 1)
            raw = page.get_text("text", sort=True)

            if raw.strip():
                word_doc.add_heading(f"Page {page_num}", level=1)
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    paragraph = word_doc.add_paragraph(line)
                    self._apply_text_direction(paragraph, line)

        doc.close()
        word_doc.save(output_path)

        return output_path

    @staticmethod
    def _apply_text_direction(paragraph, text: str) -> None:
        """Give Persian/Arabic paragraphs RTL direction + right alignment."""
        if not _RTL_CHARS.search(text):
            return
        try:
            p_pr = paragraph._p.get_or_add_pPr()
            if p_pr.find(qn("w:bidi")) is None:
                p_pr.append(OxmlElement("w:bidi"))
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        except Exception:
            pass

    def _parse_page_range(self, total_pages: int, page_range: Optional[str]) -> List[int]:
        """Parse page range specification ("all", "1-5", "1,3,5", None)"""

        if not page_range or page_range.strip().lower() == "all":
            return list(range(1, total_pages + 1))

        pages = []

        # Handle ranges like "1-5" or individual pages like "1,3,5"
        for part in page_range.split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                # Range like "1-5"
                start, end = part.split('-')
                start, end = int(start), int(end)
                for i in range(start, end + 1):
                    if 1 <= i <= total_pages:
                        pages.append(i)
            else:
                # Single page like "1"
                page_num = int(part)
                if 1 <= page_num <= total_pages:
                    pages.append(page_num)

        # Remove duplicates and sort
        return sorted(list(set(pages)))
