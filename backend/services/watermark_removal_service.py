"""
Service for PDF Watermark Removal

Real removal is done with PDF redactions (text) and image deletion (images).
Heuristics used to detect watermarks:
  - Rotated text (classic diagonal watermark)
  - Known watermark keywords (DRAFT, CONFIDENTIAL, ...)
  - Light gray / large text that repeats on every page
  - The same image displayed on every page covering a large area
  - Watermark / Stamp annotations
"""
import fitz  # PyMuPDF
from typing import Dict, List, Set, Tuple
import hashlib
import re


class WatermarkRemovalService:
    """Service for removing watermarks from PDFs"""

    # Common watermark text patterns (checked case-insensitively)
    WATERMARK_TEXT_PATTERNS = [
        r'\bDRAFT\b',
        r'\bCONFIDENTIAL\b',
        r'\bSAMPLE\b',
        r'\bPROTOTYPE\b',
        r'\bPREVIEW\b',
        r'\bPROPRIETARY\b',
        r'\bCOPY\b',
        r'\bWATERMARK\b',
        r'\bDO\s*NOT\s*COPY\b',
        r'\bDONOTCOPY\b',
        r'\bنمونه\b',
        r'\bپیش\s*نویس\b',
        r'\bمحرمانه\b',
    ]

    # A repeated image covering at least this fraction of the page is
    # treated as a watermark overlay (small header logos are kept)
    IMAGE_WATERMARK_MIN_AREA_RATIO = 0.15

    def remove_watermark(
        self,
        pdf_path: str,
        output_path: str,
        method: str = "auto"
    ) -> str:
        """
        Remove watermark from PDF.

        Args:
            pdf_path: Path to input PDF
            output_path: Path for output PDF
            method: 'auto' (safe heuristics) or 'manual' (more aggressive:
                    also drops repeated images of any size and repeated
                    text regardless of styling)

        Returns:
            Path to cleaned PDF
        """
        aggressive = (method != "auto")
        doc = fitz.open(pdf_path)

        try:
            removed_something = False
            removed_something |= self._remove_watermark_annotations(doc)
            removed_something |= self._remove_repeated_images(doc, aggressive)
            removed_something |= self._remove_vector_watermarks(doc, aggressive)
            removed_something |= self._remove_text_watermarks(doc, aggressive)

            doc.save(output_path, garbage=3, deflate=True)
        finally:
            doc.close()

        return output_path

    # ------------------------------------------------------------------
    # Vector (line-art) watermarks — e.g. text converted to outlines
    # ------------------------------------------------------------------
    def _remove_vector_watermarks(self, doc, aggressive: bool) -> bool:
        """
        Detect and remove vector watermark shapes.

        Many watermark tools stamp text as *outlines* (filled curves), so
        the watermark is neither extractable text nor an image. Those show
        up as vector drawing paths. We treat a drawing repeated identically
        on every page as a watermark; in safe mode its fill must also be a
        light gray (typical watermark styling).
        """
        total_pages = len(doc)
        if total_pages == 0:
            return False

        page_paths: List[List[dict]] = []
        for page in doc:
            paths: List[dict] = []
            try:
                for d in page.get_drawings():
                    if d.get("fill") is None:
                        continue  # only filled shapes (letter outlines etc.)
                    paths.append({
                        "rect": fitz.Rect(d["rect"]),
                        "fill": d["fill"],
                        "sig": self._path_signature(d),
                    })
            except Exception:
                pass
            page_paths.append(paths)

        sig_pages: Dict[str, Set[int]] = {}
        for idx, paths in enumerate(page_paths):
            for p in paths:
                sig_pages.setdefault(p["sig"], set()).add(idx)

        selected: List[Tuple[int, fitz.Rect]] = []
        for idx, paths in enumerate(page_paths):
            for p in paths:
                repeated = len(sig_pages.get(p["sig"], set())) >= total_pages
                if not repeated:
                    continue
                if aggressive or self._is_gray_light(p["fill"]):
                    selected.append((idx, p["rect"]))

        # Fallback when nothing repeated: a cluster of light-gray filled
        # paths covering a noticeable part of the page is likely a
        # single-page vector watermark
        if not selected:
            for idx, paths in enumerate(page_paths):
                gray = [p for p in paths if self._is_gray_light(p["fill"])]
                if len(gray) < 3:
                    continue
                union = fitz.Rect()
                for p in gray:
                    union |= p["rect"]
                if union.get_area() >= 0.12 * abs(doc[idx].rect.get_area()):
                    for p in gray:
                        selected.append((idx, p["rect"]))

        if not selected:
            return False

        removed = False
        for idx, page in enumerate(doc):
            rects = [r for (i, r) in selected if i == idx]
            if not rects:
                continue
            for r in rects:
                try:
                    page.add_redact_annot(r, fill=False)
                    removed = True
                except Exception:
                    continue
            try:
                # Remove the line-art but keep text AND images untouched —
                # the watermark rects may overlap body text.
                # NOTE: REMOVE_IF_TOUCHED is required — MuPDF's "covered"
                # test does not match paths whose rect equals the redact
                # rect exactly (verified empirically).
                page.apply_redactions(
                    images=fitz.PDF_REDACT_IMAGE_NONE,
                    graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                    text=fitz.PDF_REDACT_TEXT_NONE,
                )
            except TypeError:
                try:
                    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                except Exception:
                    pass
            except Exception:
                pass
        return removed

    @staticmethod
    def _path_signature(d: dict) -> str:
        r = fitz.Rect(d["rect"])
        fill = d.get("fill")
        items = d.get("items") or []
        return (f"{r.x0:.1f}|{r.y0:.1f}|{r.x1:.1f}|{r.y1:.1f}|"
                f"{fill}|{len(items)}|{d.get('type')}")

    @staticmethod
    def _is_gray_light(fill) -> bool:
        """fill is an RGB tuple in 0..1. Detect light grays."""
        if fill is None or len(fill) < 3:
            return False
        r, g, b = fill[0], fill[1], fill[2]
        if abs(r - g) > 0.06 or abs(g - b) > 0.06:
            return False
        return (r + g + b) / 3 >= 0.55

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------
    def _remove_watermark_annotations(self, doc) -> bool:
        """Delete Stamp/Watermark annotations on every page."""
        removed = False
        for page in doc:
            annots = list(page.annots()) if page.first_annot else []
            for annot in annots:
                try:
                    type_name = annot.type[1]
                    if type_name in ("Watermark", "Stamp"):
                        page.delete_annot(annot)
                        removed = True
                except Exception:
                    continue
        return removed

    # ------------------------------------------------------------------
    # Image watermarks
    # ------------------------------------------------------------------
    def _remove_repeated_images(self, doc, aggressive: bool) -> bool:
        """
        Remove images that appear on EVERY page covering a large area
        (aggressive mode: any repeated image, any size).
        """
        total_pages = len(doc)
        if total_pages == 0:
            return False

        # Collect per page: xref -> displayed area ratio, and xref digest
        page_images: List[Dict[int, float]] = []
        digest_of: Dict[int, str] = {}
        for page in doc:
            infos: Dict[int, float] = {}
            page_area = abs(page.rect.get_area()) or 1.0
            try:
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        rects = page.get_image_rects(xref)
                    except Exception:
                        rects = []
                    area = 0.0
                    for r in rects:
                        area += abs(r.get_area())
                    if xref not in digest_of:
                        try:
                            raw = doc.extract_image(xref)
                            digest = raw.get("digest")
                            if not digest:
                                digest = hashlib.md5(raw["image"]).hexdigest()
                            digest_of[xref] = digest
                        except Exception:
                            digest_of[xref] = f"x{xref}"
                    infos[xref] = area / page_area
            except Exception:
                continue
            page_images.append(infos)

        if not page_images:
            return False

        # Map digest -> set of xrefs using it
        xrefs_by_digest: Dict[str, Set[int]] = {}
        for xref, digest in digest_of.items():
            xrefs_by_digest.setdefault(digest, set()).add(xref)

        # A digest is a "watermark candidate" if some xref of it appears
        # on every page
        watermark_digests: Set[str] = set()
        for digest, xrefs in xrefs_by_digest.items():
            pages_using = sum(1 for infos in page_images
                              if any(x in infos for x in xrefs))
            if pages_using >= total_pages:
                if aggressive:
                    watermark_digests.add(digest)
                else:
                    # safe mode: require a large overlay area on some page
                    max_ratio = max(
                        (infos.get(x, 0.0)
                         for infos in page_images for x in xrefs),
                        default=0.0,
                    )
                    if max_ratio >= self.IMAGE_WATERMARK_MIN_AREA_RATIO:
                        watermark_digests.add(digest)

        if not watermark_digests:
            return False

        watermark_xrefs: Set[int] = set()
        for digest in watermark_digests:
            watermark_xrefs |= xrefs_by_digest[digest]

        removed = False
        for page in doc:
            try:
                for img in page.get_images(full=True):
                    if img[0] in watermark_xrefs:
                        try:
                            page.delete_image(img[0])
                            removed = True
                        except Exception:
                            continue
            except Exception:
                continue
        return removed

    # ------------------------------------------------------------------
    # Text watermarks
    # ------------------------------------------------------------------
    def _remove_text_watermarks(self, doc, aggressive: bool) -> bool:
        """
        Detect watermark-like text spans and redact their rectangles.
        """
        total_pages = len(doc)
        if total_pages == 0:
            return False

        # 1) Collect spans per page
        page_spans: List[List[dict]] = []
        for page in doc:
            spans: List[dict] = []
            try:
                blocks = page.get_text("dict").get("blocks", [])
            except Exception:
                blocks = []
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    direction = line.get("dir", (1.0, 0.0))
                    rotated = abs(direction[0]) < 0.99
                    for span in line.get("spans", []):
                        text = (span.get("text") or "").strip()
                        if not text:
                            continue
                        spans.append({
                            "text": text,
                            "bbox": fitz.Rect(span["bbox"]),
                            "size": span.get("size", 0.0),
                            "color": span.get("color", 0),
                            "rotated": rotated,
                        })
            page_spans.append(spans)

        # 2) Find body font size (median of span sizes) for "large" tests
        all_sizes = sorted(s["size"] for spans in page_spans for s in spans)
        median_size = all_sizes[len(all_sizes) // 2] if all_sizes else 10.0

        # 3) Repetition map: normalized text -> pages it appears on
        text_pages: Dict[str, Set[int]] = {}
        for idx, spans in enumerate(page_spans):
            for s in spans:
                key = self._normalize(s["text"])
                if key:
                    text_pages.setdefault(key, set()).add(idx)

        # 4) Select spans to redact
        rects_to_redact: List[Tuple[int, fitz.Rect]] = []
        for idx, spans in enumerate(page_spans):
            for s in spans:
                if self._is_watermark_span(
                    s, idx, total_pages, text_pages, median_size, aggressive
                ):
                    # Tight rect: PyMuPDF redaction removes every character
                    # whose bbox intersects the rect, so padding would eat
                    # neighbouring body text as well
                    rects_to_redact.append((idx, fitz.Rect(s["bbox"])))

        if not rects_to_redact:
            return False

        # 5) Apply redactions (keep images intact for text redactions)
        removed = False
        for idx, page in enumerate(doc):
            page_rects = [r for (i, r) in rects_to_redact if i == idx]
            if not page_rects:
                continue
            for rect in page_rects:
                try:
                    page.add_redact_annot(rect, fill=False)
                    removed = True
                except Exception:
                    continue
            if removed:
                try:
                    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                except TypeError:
                    page.apply_redactions()
                except Exception:
                    pass
        return removed

    def _is_watermark_span(
        self,
        span: dict,
        page_idx: int,
        total_pages: int,
        text_pages: Dict[str, Set[int]],
        median_size: float,
        aggressive: bool,
    ) -> bool:
        text = span["text"]
        key = self._normalize(text)

        # 1) Known watermark keywords -> always remove
        upper = text.upper()
        for pattern in self.WATERMARK_TEXT_PATTERNS:
            try:
                if re.search(pattern, upper) or re.search(pattern, text):
                    return True
            except re.error:
                continue

        # 2) Rotated text (diagonal watermark) -> remove
        if span["rotated"]:
            return True

        appearances = len(text_pages.get(key, set()))
        repeated_everywhere = total_pages > 1 and appearances >= total_pages

        light_gray = self._is_light_gray(span["color"])
        large = span["size"] >= max(14.0, median_size * 1.8)

        if repeated_everywhere:
            if aggressive:
                return True
            if light_gray or large or span["rotated"]:
                return True

        # 3) Even on a single page: big, light-gray text is very likely
        #    a watermark
        if light_gray and large:
            return True

        return False

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()

    @staticmethod
    def _is_light_gray(color: int) -> bool:
        """color is an sRGB integer like 0xRRGGBB. Detect light grays."""
        if color is None:
            return False
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        if not (abs(r - g) < 12 and abs(g - b) < 12):
            return False  # not a gray tone
        brightness = (r + g + b) / (3 * 255)
        return brightness >= 0.45

    # ------------------------------------------------------------------
    # Helpers kept for compatibility
    # ------------------------------------------------------------------
    def get_page_count(self, pdf_path: str) -> int:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count

    def is_encrypted(self, pdf_path: str) -> bool:
        doc = fitz.open(pdf_path)
        is_enc = doc.is_encrypted
        doc.close()
        return is_enc
