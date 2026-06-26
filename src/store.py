"""Persistence for validated records — append to JSONL and CSV.

Each record is appended as one line to data/records.jsonl (full structured
data) and as one flat row to data/records.csv (for opening in Excel).

Idempotency: a record whose (vendor_name, document_number) pair is already
present in the JSONL is treated as a duplicate and skipped — the same
invoice fed in twice yields only one stored record (see SPEC.md).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.models import Record

JSONL_NAME = "records.jsonl"
CSV_NAME = "records.csv"

# Flat columns for the CSV export (values only, plus review meta).
CSV_FIELDS = [
    "doc_type",
    "vendor_name",
    "vendor_iban",
    "document_number",
    "document_date",
    "due_date",
    "currency",
    "net_total",
    "vat_total",
    "gross_total",
    "line_items",
    "needs_review",
    "review_reasons",
    "source_file",
]


def store(record: Record, *, data_dir: str | Path = "data") -> bool:
    """Append *record* to the JSONL and CSV stores under *data_dir*.

    Returns True if the record was newly stored, False if it was skipped as
    a duplicate (same vendor_name + document_number already present).
    """
    directory = Path(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    jsonl_path = directory / JSONL_NAME
    csv_path = directory / CSV_NAME

    key = _record_key(record)
    if key in _existing_keys(jsonl_path):
        return False

    _append_jsonl(jsonl_path, record)
    _append_csv(csv_path, record)
    return True


def stored_source_files(data_dir: str | Path = "data") -> set[str]:
    """Return the set of source_file paths already present in the JSONL store.

    Used for a cheap early-out: a file that was already ingested can be
    skipped before the (paid) Claude call. The authoritative idempotency on
    vendor_name + document_number still happens in store().
    """
    jsonl_path = Path(data_dir) / JSONL_NAME
    sources: set[str] = set()
    if not jsonl_path.exists():
        return sources

    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            source = data.get("source_file")
            if source:
                sources.add(source)
    return sources


def _norm_key(vendor: str, number: str) -> tuple[str, str]:
    """Normalize the idempotency key (case- and whitespace-insensitive)."""
    return (vendor.strip().casefold(), number.strip().casefold())


def _record_key(record: Record) -> tuple[str, str]:
    return _norm_key(record.vendor_name.value, record.document_number.value)


def _existing_keys(jsonl_path: Path) -> set[tuple[str, str]]:
    """Read the (vendor, number) keys already present in the JSONL store."""
    keys: set[tuple[str, str]] = set()
    if not jsonl_path.exists():
        return keys

    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            keys.add(
                _norm_key(data["vendor_name"]["value"], data["document_number"]["value"])
            )
    return keys


def _append_jsonl(jsonl_path: Path, record: Record) -> None:
    line = json.dumps(record.model_dump(mode="json"), ensure_ascii=False)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _append_csv(csv_path: Path, record: Record) -> None:
    is_new = not csv_path.exists()
    # utf-8-sig so Excel shows umlauts correctly; newline="" per csv docs.
    with csv_path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(_record_to_csv_row(record))


def _record_to_csv_row(record: Record) -> dict[str, str]:
    """Flatten a Record into a single CSV row (values only)."""
    return {
        "doc_type": record.doc_type.value.value,
        "vendor_name": record.vendor_name.value,
        "vendor_iban": record.vendor_iban.value if record.vendor_iban else "",
        "document_number": record.document_number.value,
        "document_date": record.document_date.value.isoformat(),
        "due_date": record.due_date.value.isoformat() if record.due_date else "",
        "currency": record.currency.value,
        "net_total": str(record.net_total.value),
        "vat_total": str(record.vat_total.value),
        "gross_total": str(record.gross_total.value),
        "line_items": _format_line_items(record),
        "needs_review": str(record.needs_review),
        "review_reasons": " | ".join(record.review_reasons),
        "source_file": record.source_file,
    }


def _format_line_items(record: Record) -> str:
    """Render line items as a compact, human-readable string for the CSV."""
    return "; ".join(
        f"{item.quantity}x {item.description} @ {item.unit_price}"
        for item in record.line_items
    )
