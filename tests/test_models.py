"""Tests for the Pydantic models (src/models.py)."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.models import Confident, DocType, LineItem, Record


def make_valid_record() -> Record:
    """Build a minimal but fully valid Record for the happy path."""
    return Record(
        doc_type=Confident(value=DocType.RECHNUNG, confidence=0.95),
        vendor_name=Confident(value="Muster GmbH", confidence=0.9),
        document_number=Confident(value="RE-2026-001", confidence=0.92),
        document_date=Confident(value=date(2026, 6, 1), confidence=0.88),
        currency=Confident(value="EUR", confidence=0.99),
        net_total=Confident(value=Decimal("100.00"), confidence=0.9),
        vat_total=Confident(value=Decimal("20.00"), confidence=0.9),
        gross_total=Confident(value=Decimal("120.00"), confidence=0.9),
        line_items=[
            LineItem(
                description="Beratung",
                quantity=Decimal("2"),
                unit_price=Decimal("50.00"),
            )
        ],
        source_file="data/samples/example.pdf",
    )


def test_valid_record_instantiates():
    record = make_valid_record()

    assert record.doc_type.value is DocType.RECHNUNG
    assert record.gross_total.value == Decimal("120.00")
    assert record.vendor_iban is None
    assert record.needs_review is False
    assert record.review_reasons == []
    assert len(record.line_items) == 1


def test_invalid_doc_type_is_rejected():
    with pytest.raises(ValidationError):
        Confident[DocType](value="storno", confidence=0.9)


def test_confidence_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        Confident(value="x", confidence=1.5)
