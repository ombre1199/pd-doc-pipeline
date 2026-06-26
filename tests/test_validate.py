"""Tests for validation and needs_review flagging (src/validate.py)."""

from datetime import date
from decimal import Decimal

from src.models import Confident, DocType, LineItem, Record
from src.validate import validate


def make_record(
    *,
    confidence: float = 0.95,
    net: str = "100.00",
    vat: str = "20.00",
    gross: str = "120.00",
) -> Record:
    """Build a Record; defaults are high-confidence and plausible."""
    return Record(
        doc_type=Confident(value=DocType.RECHNUNG, confidence=confidence),
        vendor_name=Confident(value="Muster GmbH", confidence=confidence),
        document_number=Confident(value="RE-2026-001", confidence=confidence),
        document_date=Confident(value=date(2026, 6, 1), confidence=confidence),
        currency=Confident(value="EUR", confidence=confidence),
        net_total=Confident(value=Decimal(net), confidence=confidence),
        vat_total=Confident(value=Decimal(vat), confidence=confidence),
        gross_total=Confident(value=Decimal(gross), confidence=confidence),
        line_items=[
            LineItem(
                description="Beratung",
                quantity=Decimal("2"),
                unit_price=Decimal("50.00"),
            )
        ],
        source_file="data/x.pdf",
    )


def test_clean_record_needs_no_review():
    record = validate(make_record())

    assert record.needs_review is False
    assert record.review_reasons == []


def test_low_confidence_field_is_flagged():
    record = validate(make_record(confidence=0.5))

    assert record.needs_review is True
    # Every Confident field is below 0.8 here.
    assert any("niedrige Confidence" in r for r in record.review_reasons)
    assert any("vendor_name" in r for r in record.review_reasons)


def test_implausible_sum_is_flagged():
    record = validate(make_record(net="100.00", vat="20.00", gross="999.00"))

    assert record.needs_review is True
    assert any("Plausibilität verletzt" in r for r in record.review_reasons)


def test_one_cent_rounding_is_tolerated():
    # 100.00 + 19.99 = 119.99, gross 120.00 → diff 0.01, within tolerance.
    record = validate(make_record(net="100.00", vat="19.99", gross="120.00"))

    assert record.needs_review is False


def test_explicit_threshold_overrides_default():
    # confidence 0.85 is fine by default (0.8) but fails a stricter 0.9.
    record = validate(make_record(confidence=0.85), threshold=0.9)

    assert record.needs_review is True


def test_threshold_from_env(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.99")
    record = validate(make_record(confidence=0.95))

    assert record.needs_review is True
