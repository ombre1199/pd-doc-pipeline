"""Tests for the PDF text extraction (src/extract.py).

PDFs are generated on the fly with reportlab so the tests run offline
and deterministically. Real fixtures follow in a later step.
"""

from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from src.extract import NoTextLayerError, extract_text


def _make_text_pdf(path: Path, text: str) -> None:
    """Create a one-page PDF with a real text layer."""
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, text)
    c.save()


def _make_blank_pdf(path: Path) -> None:
    """Create a one-page PDF without any text (simulates a scan)."""
    c = canvas.Canvas(str(path))
    c.showPage()
    c.save()


def test_extract_text_returns_text_layer(tmp_path):
    pdf = tmp_path / "rechnung.pdf"
    _make_text_pdf(pdf, "Rechnung Nummer RE-2026-001 Muster GmbH")

    text = extract_text(pdf)

    assert "RE-2026-001" in text
    assert "Muster GmbH" in text


def test_blank_pdf_raises_no_text_layer_error(tmp_path):
    pdf = tmp_path / "scan.pdf"
    _make_blank_pdf(pdf)

    with pytest.raises(NoTextLayerError):
        extract_text(pdf)


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_text(tmp_path / "gibtsnicht.pdf")
