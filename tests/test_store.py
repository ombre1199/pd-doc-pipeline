"""Tests for persistence and idempotency (src/store.py)."""

import csv
import json
from datetime import date
from decimal import Decimal

from src.models import Confident, DocType, LineItem, Record
from src.store import CSV_NAME, JSONL_NAME, store


def make_record(*, vendor: str = "Muster GmbH", number: str = "RE-2026-001") -> Record:
    return Record(
        doc_type=Confident(value=DocType.RECHNUNG, confidence=0.95),
        vendor_name=Confident(value=vendor, confidence=0.9),
        document_number=Confident(value=number, confidence=0.92),
        document_date=Confident(value=date(2026, 6, 1), confidence=0.9),
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
        source_file="data/x.pdf",
    )


def _read_lines(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_store_writes_jsonl_and_csv(tmp_path):
    stored = store(make_record(), data_dir=tmp_path)

    assert stored is True
    jsonl = tmp_path / JSONL_NAME
    csv_path = tmp_path / CSV_NAME
    assert jsonl.exists()
    assert csv_path.exists()

    data = json.loads(_read_lines(jsonl)[0])
    assert data["vendor_name"]["value"] == "Muster GmbH"
    # Decimal is serialized as a string in JSON mode.
    assert data["gross_total"]["value"] == "120.00"


def test_duplicate_is_skipped(tmp_path):
    assert store(make_record(), data_dir=tmp_path) is True
    assert store(make_record(), data_dir=tmp_path) is False

    # Only one data line in the JSONL.
    assert len(_read_lines(tmp_path / JSONL_NAME)) == 1


def test_duplicate_ignores_case_and_whitespace(tmp_path):
    store(make_record(vendor="Muster GmbH", number="RE-2026-001"), data_dir=tmp_path)
    again = store(
        make_record(vendor="  muster gmbh ", number="re-2026-001"),
        data_dir=tmp_path,
    )

    assert again is False


def test_different_document_number_is_stored(tmp_path):
    assert store(make_record(number="RE-2026-001"), data_dir=tmp_path) is True
    assert store(make_record(number="RE-2026-002"), data_dir=tmp_path) is True

    assert len(_read_lines(tmp_path / JSONL_NAME)) == 2


def test_csv_has_single_header_and_flat_values(tmp_path):
    store(make_record(number="RE-2026-001"), data_dir=tmp_path)
    store(make_record(number="RE-2026-002"), data_dir=tmp_path)

    with (tmp_path / CSV_NAME).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["doc_type"] == "rechnung"
    assert rows[0]["gross_total"] == "120.00"
    assert "2x Beratung @ 50.00" in rows[0]["line_items"]
