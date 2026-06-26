"""PDF text extraction from the text layer.

Reads the embedded text layer with pdfplumber and falls back to pypdf.
Scanned PDFs without a usable text layer are detected and rejected via
NoTextLayerError — OCR is explicitly out of scope (see SPEC.md).
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber
from pypdf import PdfReader

# Below this many non-whitespace characters we assume there is no usable
# text layer (i.e. the PDF is most likely a scan / pure image).
MIN_TEXT_LENGTH = 20


class NoTextLayerError(Exception):
    """Raised when a PDF has no usable text layer (likely a scan)."""


def extract_text(pdf_path: str | Path) -> str:
    """Return the text layer of *pdf_path*.

    Tries pdfplumber first, then pypdf as a fallback. Raises
    NoTextLayerError if neither yields a usable amount of text.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF nicht gefunden: {path}")

    text = _extract_with_pdfplumber(path)
    if len(text.strip()) < MIN_TEXT_LENGTH:
        text = _extract_with_pypdf(path)

    if len(text.strip()) < MIN_TEXT_LENGTH:
        raise NoTextLayerError(
            f"Das PDF '{path.name}' enthält keine nutzbare Textebene "
            "(vermutlich gescannt). OCR ist nicht im Funktionsumfang."
        )

    return text.strip()


def _extract_with_pdfplumber(path: Path) -> str:
    """Join the text of all pages using pdfplumber."""
    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _extract_with_pypdf(path: Path) -> str:
    """Join the text of all pages using pypdf (fallback)."""
    reader = PdfReader(str(path))
    parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(parts)
