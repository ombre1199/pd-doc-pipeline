"""Pydantic models for the extracted document record.

Field definitions follow SPEC.md, section "Zu extrahierende Felder".
Every extracted value carries its own confidence score (0-1) so that
downstream validation can flag low-confidence fields for human review.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class DocType(str, Enum):
    """Supported document types."""

    RECHNUNG = "rechnung"
    ANGEBOT = "angebot"


class Confident(BaseModel, Generic[T]):
    """Wraps an extracted value together with the model's confidence (0-1)."""

    value: T
    confidence: float = Field(ge=0.0, le=1.0)


class LineItem(BaseModel):
    """A single position on the invoice/quote."""

    description: str
    quantity: Decimal
    unit_price: Decimal


class Record(BaseModel):
    """A fully extracted and validated document record."""

    # Extracted fields (each with its own confidence score)
    doc_type: Confident[DocType]
    vendor_name: Confident[str]
    vendor_iban: Confident[str] | None = None
    document_number: Confident[str]
    document_date: Confident[date]
    due_date: Confident[date] | None = None
    currency: Confident[str]
    net_total: Confident[Decimal]
    vat_total: Confident[Decimal]
    gross_total: Confident[Decimal]
    line_items: list[LineItem] = Field(default_factory=list)

    # Meta fields filled in during validation
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    source_file: str
