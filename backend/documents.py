"""Document extraction, OCR and retrieval helpers.

The extractor deliberately keeps native text and OCR as separate decisions at
page level.  Native PDF text is preferred when it is usable; only pages with
too little text are rendered and sent to the local Tesseract engine.  The
result is a small, serialisable document-intelligence report which the RAG
layer stores alongside its chunks.

The local OCR stack is intentionally small:

* PyMuPDF renders PDF pages without loading an entire document as images.
* Pillow performs EXIF orientation, contrast, denoising and scale handling.
* pytesseract invokes the installed, local Tesseract binary and exposes its
  token confidence and bounding boxes when available.

No document bytes or OCR text are sent to an external service.
"""

from __future__ import annotations

import io
import logging
import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import Any, List, Tuple

from backend import settings

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)
_PAGE_RE = re.compile(r"\[Page\s+(\d+)\]", re.IGNORECASE)
_ROTATE_RE = re.compile(r"Rotate:\s*(\d+)", re.IGNORECASE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i",
    "in", "is", "it", "me", "of", "on", "or", "the", "this", "to", "was", "what",
    "when", "where", "which", "who", "with", "you", "your", "about", "does", "do",
    "document", "documents", "file", "files", "information", "info", "details", "detail",
    "facts", "fact", "content", "text", "important", "key", "main", "points", "point",
    "say", "says", "mention", "mentions", "tell", "list", "show", "give", "provide",
}

PDF_SUFFIXES = frozenset({".pdf"})
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".heic", ".heif"})
TEXT_SUFFIXES = frozenset({".txt", ".md", ".csv", ".json", ".py", ".js"})
DOCX_SUFFIXES = frozenset({".docx"})
SUPPORTED_SUFFIXES = PDF_SUFFIXES | IMAGE_SUFFIXES | TEXT_SUFFIXES | DOCX_SUFFIXES


class DocumentError(ValueError):
    """Base class for safe, user-facing document processing failures."""

    code = "document_error"


class UnsupportedFileType(DocumentError):
    code = "unsupported_file_type"


class InvalidDocument(DocumentError):
    code = "invalid_document"


class TooManyPages(DocumentError):
    code = "too_many_pages"


class OCRUnavailable(DocumentError):
    code = "ocr_unavailable"


class OCRLanguageUnavailable(DocumentError):
    code = "ocr_language_unavailable"


class EmptyExtraction(DocumentError):
    code = "empty_extraction"


@dataclass
class ExtractionPage:
    page_number: int
    text: str
    method: str
    blocks: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    ocr_confidence: float | None = None
    confidence_source: str | None = None
    needs_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        quality: dict[str, Any] = {
            "ocr_confidence": self.ocr_confidence,
            "needs_review": self.needs_review,
        }
        if self.confidence_source:
            quality["confidence_source"] = self.confidence_source
        return {
            "page_number": self.page_number,
            "text": self.text,
            "blocks": self.blocks,
            "tables": self.tables,
            "warnings": self.warnings,
            "quality": quality,
            "extraction_method": self.method,
        }


@dataclass
class ExtractionReport:
    filename: str
    file_type: str
    status: str
    detected_language: str | None
    extraction_method: str
    pages: list[ExtractionPage]
    full_text: str
    warnings: list[str] = field(default_factory=list)
    document_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "document_id": self.document_id,
            "filename": self.filename,
            "status": self.status,
            "detected_language": self.detected_language,
            "extraction_method": self.extraction_method,
            "page_count": None if self.file_type == "docx" else len(self.pages),
            "pages": [page.to_dict() for page in self.pages],
            "full_text": self.full_text,
            "warnings": list(dict.fromkeys(self.warnings)),
            "char_count": len(_visible_text(self.full_text)),
        }


@dataclass
class OCRResult:
    text: str
    blocks: list[dict[str, Any]]
    confidence: float | None
    confidence_source: str | None


# ---------------------------------------------------------------------------
# File validation and capability reporting
# ---------------------------------------------------------------------------

def _suffix(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def _looks_like_text(data: bytes, filename: str) -> bool:
    if _suffix(filename) not in TEXT_SUFFIXES or b"\x00" in data[:4096]:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _validate_archive(archive: zipfile.ZipFile) -> None:
    entries = archive.infolist()
    if len(entries) > settings.MAX_ARCHIVE_ENTRIES:
        raise InvalidDocument(
            f"archive has too many entries; the limit is {settings.MAX_ARCHIVE_ENTRIES}"
        )
    total = 0
    for entry in entries:
        if entry.file_size < 0:
            raise InvalidDocument("archive contains an invalid entry size")
        total += entry.file_size
        if total > settings.MAX_ARCHIVE_UNCOMPRESSED_BYTES:
            raise InvalidDocument(
                "archive expands beyond the configured uncompressed-size limit"
            )


def detect_file_type(data: bytes, filename: str = "") -> str:
    """Identify a supported type from content signatures, not extension alone."""
    if not data:
        raise InvalidDocument("empty document")
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                _validate_archive(archive)
                names = set(archive.namelist())
                if "[Content_Types].xml" in names and "word/document.xml" in names:
                    return "docx"
        except (OSError, zipfile.BadZipFile):
            raise InvalidDocument("the Office document is corrupted")
    if _looks_like_text(data, filename):
        return "text"

    # Pillow validates the image container.  HEIC/HEIF is accepted only when
    # the installed Pillow build (or its optional plugin) can decode it.
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > settings.MAX_IMAGE_PIXELS:
                raise InvalidDocument(
                    f"image has too many pixels; the limit is {settings.MAX_IMAGE_PIXELS}"
                )
            image.verify()
            image_format = (image.format or "").upper()
        if image_format in {"PNG", "JPEG", "JPG", "TIFF", "BMP", "WEBP", "HEIC", "HEIF"}:
            return "image"
    except ImportError:
        pass
    except InvalidDocument:
        raise
    except Exception:
        # Do not turn arbitrary binary files into images just because they have
        # an image-looking suffix.
        pass
    raise UnsupportedFileType(
        "unsupported or corrupted file; upload a PDF, DOCX, TXT, Markdown, "
        "PNG, JPEG, TIFF, BMP, WebP, or a Pillow-supported HEIC/HEIF image"
    )


def inspect_document(data: bytes, filename: str = "") -> dict[str, Any]:
    """Validate a document and return cheap metadata before OCR begins."""
    file_type = detect_file_type(data, filename)
    page_count: int | None = 1 if file_type in {"image", "text"} else None
    if file_type == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data), strict=False)
            page_count = len(reader.pages)
        except Exception as exc:
            raise InvalidDocument(f"could not read the PDF: {exc}") from exc
    elif file_type == "docx":
        page_count = None  # DOCX does not carry stable pagination without layout.
    if page_count is not None and page_count > settings.MAX_DOCUMENT_PAGES:
        raise TooManyPages(
            f"document has {page_count} pages; the limit is {settings.MAX_DOCUMENT_PAGES}"
        )
    return {"file_type": file_type, "page_count": page_count}


def ocr_capabilities() -> dict[str, Any]:
    """Return truthful local OCR capabilities for health/configuration UIs."""
    result: dict[str, Any] = {
        "enabled": bool(settings.OCR_ENABLED),
        "engine": "tesseract",
        "available": False,
        "pdf_available": False,
        "languages": [],
        "requested_language": settings.OCR_LANG,
        "missing_language": None,
    }
    if not settings.OCR_ENABLED:
        return result
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        result["languages"] = sorted(pytesseract.get_languages(config=""))
        requested = [part for part in settings.OCR_LANG.split("+") if part]
        missing = [part for part in requested if part not in result["languages"]]
        if missing:
            result["missing_language"] = missing
        result["available"] = not missing
        try:
            import fitz  # noqa: F401

            result["pdf_available"] = not missing
        except Exception:
            result["pdf_available"] = False
    except Exception as exc:
        result["error"] = type(exc).__name__
    return result


def ocr_available() -> bool:
    """Compatibility boolean used by the health endpoint."""
    return bool(ocr_capabilities().get("available"))


# ---------------------------------------------------------------------------
# Extraction entry points
# ---------------------------------------------------------------------------

def extract_document(file_bytes: bytes, filename: str) -> ExtractionReport:
    """Extract a validated document into a stable page-aware report."""
    info = inspect_document(file_bytes, filename)
    file_type = info["file_type"]
    if file_type == "pdf":
        report = _extract_pdf(file_bytes, filename)
    elif file_type == "image":
        report = _extract_image(file_bytes, filename)
    elif file_type == "docx":
        report = _extract_docx_report(file_bytes, filename)
    else:
        text = file_bytes.decode("utf-8", errors="strict").replace("\r\n", "\n").strip()
        page = ExtractionPage(1, text, "native_text", needs_review=not bool(text))
        report = ExtractionReport(filename, "text", "completed", _detect_language(text), "native_text", [page], text)
    if not _visible_text(report.full_text):
        report.status = "failed"
        report.warnings.append("no_extractable_text")
    return report


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Backward-compatible plain-text facade used by existing callers/tests."""
    return extract_document(file_bytes, filename).full_text


def _extract_pdf(data: bytes, filename: str) -> ExtractionReport:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
    except Exception as exc:
        raise InvalidDocument(f"could not read the PDF: {exc}") from exc
    if len(reader.pages) > settings.MAX_DOCUMENT_PAGES:
        raise TooManyPages(
            f"document has {len(reader.pages)} pages; the limit is {settings.MAX_DOCUMENT_PAGES}"
        )

    native: list[str] = []
    needs_ocr: list[int] = []
    warnings: list[str] = []
    for index, page in enumerate(reader.pages, 1):
        try:
            text = (page.extract_text() or "").replace("\x00", "").strip()
        except Exception as exc:
            logger.info("native PDF extraction failed on page %d: %s", index, type(exc).__name__)
            text = ""
            warnings.append(f"page_{index}_native_extraction_failed")
        native.append(text)
        if len(_visible_text(text)) < settings.OCR_MIN_TEXT_CHARS:
            needs_ocr.append(index)

    ocr_pages: dict[int, OCRResult] = {}
    if needs_ocr and settings.OCR_ENABLED:
        try:
            ocr_pages = _ocr_pdf_pages(data, needs_ocr)
        except OCRUnavailable:
            warnings.append("pdf_ocr_unavailable")
        except OCRLanguageUnavailable:
            warnings.append("ocr_language_unavailable")
        except Exception as exc:
            logger.warning("PDF OCR failed: %s", type(exc).__name__)
            warnings.append("pdf_ocr_failed")
    elif needs_ocr:
        warnings.append("ocr_disabled")

    pages: list[ExtractionPage] = []
    for index, native_text in enumerate(native, 1):
        ocr = ocr_pages.get(index)
        page_warnings: list[str] = []
        blocks: list[dict[str, Any]] = []
        method = "native_text"
        text = native_text
        confidence = None
        confidence_source = None
        if ocr and ocr.text:
            blocks = ocr.blocks
            confidence = ocr.confidence
            confidence_source = ocr.confidence_source
            if native_text and _visible_text(native_text):
                text = f"{native_text}\n{ocr.text}".strip()
                method = "hybrid"
                page_warnings.append("native_text_short_ocr_added")
            else:
                text = ocr.text
                method = "ocr"
            if confidence is not None and confidence < settings.OCR_REVIEW_CONFIDENCE:
                page_warnings.append("low_ocr_confidence")
        if not text:
            method = "none"
            page_warnings.append("no_text_on_page")
        pages.append(ExtractionPage(
            index, text, method, blocks=blocks, warnings=page_warnings,
            ocr_confidence=confidence, confidence_source=confidence_source,
            needs_review=method == "none" or "low_ocr_confidence" in page_warnings,
        ))

    full_text = "\n".join(f"[Page {page.page_number}]\n{page.text}" for page in pages if page.text).strip()
    methods = {page.method for page in pages}
    extraction_method = "hybrid" if "hybrid" in methods or ("native_text" in methods and "ocr" in methods) else (
        "ocr" if "ocr" in methods else "native_text"
    )
    warnings.extend(warning for page in pages for warning in page.warnings)
    return ExtractionReport(
        filename, "pdf", "completed", _detect_language(_visible_text(full_text)),
        extraction_method, pages, full_text, list(dict.fromkeys(warnings)),
    )


def _extract_image(data: bytes, filename: str) -> ExtractionReport:
    try:
        result = _ocr_image_bytes(data)
    except OCRUnavailable:
        raise
    except OCRLanguageUnavailable:
        raise
    page_warnings = []
    if result.confidence is not None and result.confidence < settings.OCR_REVIEW_CONFIDENCE:
        page_warnings.append("low_ocr_confidence")
    page = ExtractionPage(
        1, result.text, "ocr" if result.text else "none", blocks=result.blocks,
        warnings=page_warnings + ([] if result.text else ["no_text_on_page"]),
        ocr_confidence=result.confidence, confidence_source=result.confidence_source,
        needs_review=not result.text or bool(page_warnings),
    )
    warnings = list(page.warnings)
    return ExtractionReport(
        filename, "image", "completed", _detect_language(result.text), "ocr", [page],
        f"[Page 1]\n{result.text}".strip(), warnings,
    )


def _extract_docx_report(data: bytes, filename: str) -> ExtractionReport:
    from docx import Document

    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        raise InvalidDocument(f"could not read the DOCX: {exc}") from exc
    parts: list[str] = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
    tables: list[dict[str, Any]] = []
    for table_number, table in enumerate(doc.tables, 1):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip().replace("|", "\\|") for cell in row.cells]
            if any(cells):
                rows.append(cells)
                parts.append(" | ".join(cells))
        if rows:
            tables.append({"table_number": table_number, "rows": rows, "format": "pipe"})

    warnings: list[str] = []
    embedded_text: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            images = sorted(name for name in archive.namelist() if name.startswith("word/media/"))
            for number, name in enumerate(images, 1):
                try:
                    result = _ocr_image_bytes(archive.read(name))
                    if result.text:
                        embedded_text.append(f"[Embedded image {number}]\n{result.text}")
                except (OCRUnavailable, OCRLanguageUnavailable):
                    warnings.append("embedded_image_ocr_unavailable")
                    break
                except Exception:
                    warnings.append(f"embedded_image_{number}_ocr_failed")
    except zipfile.BadZipFile as exc:
        raise InvalidDocument("the Office document is corrupted") from exc
    parts.extend(embedded_text)
    text = "\n".join(parts).strip()
    if tables:
        warnings.append("docx_table_structure_preserved_as_rows")
    if embedded_text:
        warnings.append("embedded_images_ocr_added")
    page = ExtractionPage(1, text, "native_text" if not embedded_text else "hybrid", tables=tables)
    return ExtractionReport(
        filename, "docx", "completed", _detect_language(text),
        "hybrid" if embedded_text else "native_text", [page], text, warnings,
    )


# ---------------------------------------------------------------------------
# Local OCR implementation
# ---------------------------------------------------------------------------

def _check_ocr_dependencies(*, pdf: bool = False) -> tuple[Any, Any, Any]:
    try:
        import pytesseract
        from PIL import Image
        if pdf:
            import fitz
        else:
            fitz = None
        pytesseract.get_tesseract_version()
    except Exception as exc:
        raise OCRUnavailable(
            "local OCR is unavailable; install pytesseract, Pillow, Tesseract "
            + ("and PyMuPDF for PDF OCR" if pdf else "")
        ) from exc
    languages = set(pytesseract.get_languages(config=""))
    requested = [part for part in settings.OCR_LANG.split("+") if part]
    missing = [part for part in requested if part not in languages]
    if missing:
        raise OCRLanguageUnavailable(
            f"Tesseract language pack(s) not installed: {', '.join(missing)}; "
            "set OCR_LANG to an installed language combination"
        )
    return pytesseract, Image, fitz


def _ocr_pdf_pages(data: bytes, page_numbers: list[int]) -> dict[int, OCRResult]:
    pytesseract, Image, fitz = _check_ocr_dependencies(pdf=True)
    results: dict[int, OCRResult] = {}
    with fitz.open(stream=data, filetype="pdf") as pdf:
        for number in page_numbers:
            page = pdf[number - 1]
            requested_scale = max(1.0, min(float(settings.OCR_DPI) / 72.0, 4.0))
            page_area = max(float(page.rect.width * page.rect.height), 1.0)
            max_scale = (settings.MAX_RENDER_PIXELS / page_area) ** 0.5
            scale = min(requested_scale, max_scale)
            if scale < 0.5:
                raise InvalidDocument("PDF page exceeds the safe rendering limit")
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                results[number] = _run_ocr(image, pytesseract, Image)
    return results


def _ocr_image_bytes(data: bytes) -> OCRResult:
    pytesseract, Image, _ = _check_ocr_dependencies()
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > settings.MAX_IMAGE_PIXELS:
                raise InvalidDocument(
                    f"image has too many pixels; the limit is {settings.MAX_IMAGE_PIXELS}"
                )
            image.load()
            return _run_ocr(image, pytesseract, Image)
    except OCRLanguageUnavailable:
        raise
    except Exception as exc:
        raise InvalidDocument(f"could not decode the image: {exc}") from exc


def _prepare_image(image: Any, pytesseract: Any, Image: Any) -> Any:
    from PIL import ImageEnhance, ImageFilter, ImageOps

    image = ImageOps.exif_transpose(image).convert("RGB")
    # OSD is best-effort.  It is not used as a confidence claim and is skipped
    # when the page is too small or Tesseract cannot classify its orientation.
    try:
        osd = pytesseract.image_to_osd(image, config="--psm 0", timeout=settings.OCR_TIMEOUT_SECONDS)
        rotation = int(_ROTATE_RE.search(osd).group(1)) if _ROTATE_RE.search(osd) else 0
        if rotation in {90, 180, 270}:
            # Tesseract reports the clockwise correction; Pillow's positive
            # angle is counter-clockwise.
            image = image.rotate(-rotation, expand=True)
    except Exception:
        pass
    width, height = image.size
    target_width = settings.OCR_TARGET_WIDTH
    if target_width and width < target_width:
        scale = min(target_width / max(width, 1), settings.OCR_MAX_SCALE)
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return ImageEnhance.Contrast(gray).enhance(settings.OCR_CONTRAST)


def _run_ocr(image: Any, pytesseract: Any, Image: Any) -> OCRResult:
    from pytesseract import Output

    prepared = _prepare_image(image, pytesseract, Image)
    try:
        data = pytesseract.image_to_data(
            prepared, lang=settings.OCR_LANG, config=settings.OCR_CONFIG,
            output_type=Output.DICT, timeout=settings.OCR_TIMEOUT_SECONDS,
        )
    except TypeError:  # small test doubles may not implement timeout/config.
        data = pytesseract.image_to_data(prepared, lang=settings.OCR_LANG, output_type=Output.DICT)
    words: list[str] = []
    confidence_values: list[float] = []
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    count = len(data.get("text", []))
    for index in range(count):
        word = str(data["text"][index] or "").strip()
        if not word:
            continue
        words.append(word)
        try:
            confidence = float(data.get("conf", [""] * count)[index])
            if confidence >= 0:
                confidence_values.append(confidence)
        except (TypeError, ValueError, IndexError):
            pass
        key = (
            str(data.get("block_num", [0] * count)[index]),
            str(data.get("par_num", [0] * count)[index]),
            str(data.get("line_num", [0] * count)[index]),
        )
        block = grouped.setdefault(key, {"text": [], "bbox": {
            "x": int(data.get("left", [0] * count)[index]),
            "y": int(data.get("top", [0] * count)[index]),
            "width": int(data.get("width", [0] * count)[index]),
            "height": int(data.get("height", [0] * count)[index]),
        }})
        block["text"].append(word)
        # Expand the line bounding box as additional words are added.
        bbox = block["bbox"]
        left = int(data.get("left", [0] * count)[index])
        top = int(data.get("top", [0] * count)[index])
        right = left + int(data.get("width", [0] * count)[index])
        bottom = top + int(data.get("height", [0] * count)[index])
        bbox["x"] = min(bbox["x"], left)
        bbox["y"] = min(bbox["y"], top)
        bbox["width"] = max(bbox["x"] + bbox["width"], right) - bbox["x"]
        bbox["height"] = max(bbox["y"] + bbox["height"], bottom) - bbox["y"]
    blocks = [{"text": " ".join(value["text"]), "bbox": value["bbox"]} for value in grouped.values()]
    text = "\n".join(block["text"] for block in blocks).strip()
    confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else None
    return OCRResult(text, blocks, confidence, "tesseract_token_mean" if confidence is not None else None)


def _detect_language(text: str) -> str | None:
    if len(_visible_text(text)) < 12:
        return None
    try:
        from src.detection import detect_meta

        meta = detect_meta(_visible_text(text))
        # Short invoices and names are frequently misclassified by statistical
        # detectors.  Returning null is safer than presenting a weak guess as
        # document truth.
        return meta.get("language") if meta.get("confidence", 0.0) >= 0.75 else None
    except Exception:
        return None


def _visible_text(text: str) -> str:
    return re.sub(r"\[Page\s+\d+\]", "", text or "", flags=re.IGNORECASE).strip()


def page_number(text: str) -> int | None:
    """Return the nearest PDF page marker retained in a chunk, if present."""
    pages = _PAGE_RE.findall(text or "")
    return int(pages[-1]) if pages else None


# ---------------------------------------------------------------------------
# Chunking and dependency-free retrieval fallback
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    """Split text into overlapping chunks of ~chunk_size chars on word boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            for offset in range(end, max(start, end - 50), -1):
                if text[offset].isspace():
                    end = offset
                    break
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]


def chunk_report(report: ExtractionReport, chunk_size: int = 1200, overlap: int = 150) -> list[tuple[str, int | None]]:
    """Chunk pages independently so every chunk retains its source page.

    Flattening a report before chunking loses the page for long pages and makes
    a boundary chunk ambiguous.  The explicit tuple metadata is persisted by
    the RAG layer; the page marker is retained in the text for LLM grounding.
    """
    result: list[tuple[str, int | None]] = []
    for page in report.pages:
        if not page.text.strip():
            continue
        prefix = f"[Page {page.page_number}]\n" if report.file_type == "pdf" else ""
        for chunk in chunk_text(prefix + page.text.strip(), chunk_size=chunk_size, overlap=overlap):
            result.append((chunk, page.page_number if report.file_type == "pdf" else None))
    return result


def _tokens(text: str) -> set:
    return {token.lower() for token in _WORD_RE.findall(text) if token.lower() not in _STOPWORDS}


def score_chunks(query: str, chunks: List[str], top_k: int = 5) -> List[Tuple[float, int, str]]:
    if not chunks:
        return []
    query_tokens = _tokens(query)
    if not query_tokens:
        return [(0.0, index, chunk) for index, chunk in enumerate(chunks[:top_k])]
    scored = []
    for index, chunk in enumerate(chunks):
        chunk_tokens = _tokens(chunk)
        union = len(query_tokens | chunk_tokens)
        score = len(query_tokens & chunk_tokens) / union if union else 0.0
        scored.append((score, index, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:top_k]


def keyword_overlap(query: str, text: str) -> tuple[int, int]:
    """Return (matching meaningful terms, meaningful query terms).

    This is used only as a conservative grounding rescue when a semantic
    embedding is relevant but falls just below the calibrated cosine gate.
    """
    query_tokens = _tokens(query)
    return len(query_tokens & _tokens(text)), len(query_tokens)


def matching_keywords(query: str, text: str) -> set[str]:
    """Return meaningful query terms that occur verbatim in a candidate chunk."""
    return _tokens(query) & _tokens(text)


def build_context(query: str, chunks: List[str], top_k: int = 5) -> Tuple[str, List[int]]:
    top = score_chunks(query, chunks, top_k=top_k)
    return "\n\n".join(f"[{rank}] {chunk}" for rank, (_, _, chunk) in enumerate(top, 1)), [index for _, index, _ in top]
