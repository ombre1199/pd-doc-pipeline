"""Tests for the structured extraction (src/classify_extract.py).

The Anthropic client is faked so the tests run offline and deterministically
— no real API call is made. We only check that a tool_use response is parsed
into a Record correctly and that a missing tool_use is reported clearly.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.classify_extract import (
    TOOL_NAME,
    ClassifyError,
    classify_extract,
)
from src.models import DocType


def _tool_use_block(payload: dict) -> SimpleNamespace:
    """Build a fake Anthropic tool_use content block."""
    return SimpleNamespace(type="tool_use", name=TOOL_NAME, input=payload)


class FakeMessages:
    """Stand-in for client.messages that returns a canned response."""

    def __init__(self, response):
        self._response = response
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class FakeClient:
    """Minimal Anthropic-compatible client for tests."""

    def __init__(self, response):
        self.messages = FakeMessages(response)


def _full_payload() -> dict:
    return {
        "doc_type": {"value": "rechnung", "confidence": 0.97},
        "vendor_name": {"value": "Muster GmbH", "confidence": 0.93},
        "vendor_iban": {"value": "AT611904300234573201", "confidence": 0.8},
        "document_number": {"value": "RE-2026-001", "confidence": 0.95},
        "document_date": {"value": "2026-06-01", "confidence": 0.9},
        "due_date": {"value": "2026-06-15", "confidence": 0.85},
        "currency": {"value": "EUR", "confidence": 0.99},
        "net_total": {"value": "100.00", "confidence": 0.9},
        "vat_total": {"value": "20.00", "confidence": 0.9},
        "gross_total": {"value": "120.00", "confidence": 0.9},
        "line_items": [
            {"description": "Beratung", "quantity": "2", "unit_price": "50.00"},
        ],
    }


def test_parses_tool_use_into_record():
    response = SimpleNamespace(content=[_tool_use_block(_full_payload())])
    client = FakeClient(response)

    record = classify_extract("Belegtext ...", "data/x.pdf", client=client)

    assert record.doc_type.value is DocType.RECHNUNG
    assert record.vendor_name.value == "Muster GmbH"
    assert record.document_date.value == date(2026, 6, 1)
    assert record.gross_total.value == Decimal("120.00")
    assert record.line_items[0].unit_price == Decimal("50.00")
    assert record.source_file == "data/x.pdf"
    # Validation (needs_review) is a separate step.
    assert record.needs_review is False


def test_optional_fields_can_be_null():
    payload = _full_payload()
    payload["vendor_iban"] = None
    payload["due_date"] = None
    response = SimpleNamespace(content=[_tool_use_block(payload)])

    record = classify_extract("Belegtext ...", "data/x.pdf", client=FakeClient(response))

    assert record.vendor_iban is None
    assert record.due_date is None


def test_forces_the_extraction_tool():
    response = SimpleNamespace(content=[_tool_use_block(_full_payload())])
    client = FakeClient(response)

    classify_extract("Belegtext ...", "data/x.pdf", client=client)

    kwargs = client.messages.last_kwargs
    assert kwargs["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert kwargs["tools"][0]["name"] == TOOL_NAME


def test_missing_tool_use_raises_classify_error():
    text_block = SimpleNamespace(type="text", text="Kein Tool benutzt.")
    response = SimpleNamespace(content=[text_block])

    with pytest.raises(ClassifyError):
        classify_extract("Belegtext ...", "data/x.pdf", client=FakeClient(response))
