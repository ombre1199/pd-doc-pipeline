"""Tests for the German reply draft (src/draft.py)."""

from datetime import date
from decimal import Decimal

from src.draft import draft, render_draft
from src.models import Confident, DocType, LineItem, Record


def make_record(
    *,
    confidence: float = 0.95,
    with_due_date: bool = True,
    needs_review: bool = False,
    doc_type: DocType = DocType.RECHNUNG,
) -> Record:
    """Build a high-confidence, plausible Record by default."""
    record = Record(
        doc_type=Confident(value=doc_type, confidence=confidence),
        vendor_name=Confident(value="Muster GmbH", confidence=confidence),
        document_number=Confident(value="RE-2026-001", confidence=confidence),
        document_date=Confident(value=date(2026, 6, 1), confidence=confidence),
        currency=Confident(value="EUR", confidence=confidence),
        net_total=Confident(value=Decimal("100.00"), confidence=confidence),
        vat_total=Confident(value=Decimal("20.00"), confidence=confidence),
        gross_total=Confident(value=Decimal("120.00"), confidence=confidence),
        line_items=[
            LineItem(
                description="Beratung",
                quantity=Decimal("2"),
                unit_price=Decimal("50.00"),
            )
        ],
        source_file="data/x.pdf",
    )
    if with_due_date:
        record.due_date = Confident(value=date(2026, 7, 1), confidence=confidence)
    record.needs_review = needs_review
    return record


def test_default_has_no_conditions_block():
    # Flag not set → no conditions block, regardless of confidence.
    text = render_draft(make_record())

    assert "Konditionen laut Beleg" not in text
    assert "Eingang des Belegs" in text


def test_flag_with_high_confidence_renders_conditions(monkeypatch):
    monkeypatch.setenv("DRAFT_INCLUDE_CONDITIONS", "true")

    text = render_draft(make_record())

    assert "Konditionen laut Beleg" in text
    assert "120.00 EUR" in text
    assert "2026-07-01" in text


def test_flag_but_needs_review_omits_block_and_shows_hint(monkeypatch):
    monkeypatch.setenv("DRAFT_INCLUDE_CONDITIONS", "true")
    record = make_record(needs_review=True)
    record.review_reasons = ["Plausibilität verletzt: ..."]

    text = render_draft(record)

    assert "Konditionen laut Beleg" not in text
    assert "Bitte vor Versand prüfen" in text
    assert "Plausibilität verletzt" in text


def test_low_confidence_omits_block(monkeypatch):
    monkeypatch.setenv("DRAFT_INCLUDE_CONDITIONS", "true")

    text = render_draft(make_record(confidence=0.5))

    assert "Konditionen laut Beleg" not in text


def test_angebot_uses_offer_wording():
    text = render_draft(make_record(doc_type=DocType.ANGEBOT))

    assert "Ihr Angebot RE-2026-001" in text


def test_draft_writes_markdown_file(tmp_path):
    record = make_record()
    text = draft(record, out_dir=tmp_path)

    expected = tmp_path / "RE-2026-001_Muster_GmbH.md"
    assert expected.exists()
    assert expected.read_text(encoding="utf-8") == text
