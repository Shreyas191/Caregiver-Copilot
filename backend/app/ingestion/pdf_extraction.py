"""CC-039: PDF text extraction using PyMuPDF with OCR fallback detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PageContent:
    page_number: int  # 1-based
    text: str


@dataclass
class ExtractedDocument:
    pages: list[PageContent] = field(default_factory=list)
    full_text: str = ""
    page_count: int = 0
    ocr_used: bool = False

    @property
    def is_empty(self) -> bool:
        return len(self.full_text.strip()) < 50


_MIN_TEXT_CHARS_PER_PAGE = 30  # below this we consider the page scanned


def extract_text(file_path: str | Path) -> ExtractedDocument:
    """Extract text from a PDF file.

    For text-based PDFs uses PyMuPDF directly.
    Scanned PDFs (sparse text) are flagged via ocr_used=True and we
    attempt a basic text layer extraction — full OCR via PaddleOCR
    would be wired here in production but is skipped to avoid the
    heavy install; the flag is set so callers know the text is poor.
    """
    import fitz  # PyMuPDF

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(str(path))
    pages: list[PageContent] = []
    sparse_pages = 0

    for i, page in enumerate(doc):
        text = page.get_text("text")
        # Normalise whitespace
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < _MIN_TEXT_CHARS_PER_PAGE:
            sparse_pages += 1
        pages.append(PageContent(page_number=i + 1, text=text))

    doc.close()

    full_text = "\n\n".join(
        f"[Page {p.page_number}]\n{p.text}" for p in pages if p.text
    )

    ocr_used = sparse_pages > len(pages) / 2

    return ExtractedDocument(
        pages=pages,
        full_text=full_text,
        page_count=len(pages),
        ocr_used=ocr_used,
    )


def extract_text_from_bytes(data: bytes, filename: str = "document.pdf") -> ExtractedDocument:
    """Extract text from PDF bytes (used when file is already in memory)."""
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    pages: list[PageContent] = []
    sparse_pages = 0

    for i, page in enumerate(doc):
        text = page.get_text("text")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < _MIN_TEXT_CHARS_PER_PAGE:
            sparse_pages += 1
        pages.append(PageContent(page_number=i + 1, text=text))

    doc.close()

    full_text = "\n\n".join(
        f"[Page {p.page_number}]\n{p.text}" for p in pages if p.text
    )
    ocr_used = sparse_pages > len(pages) / 2

    return ExtractedDocument(
        pages=pages,
        full_text=full_text,
        page_count=len(pages),
        ocr_used=ocr_used,
    )
