"""Validation and human-in-the-loop flagging for an extracted Record.

Type validation already happens when the Record is parsed (pydantic). This
module adds the two remaining checks from SPEC.md:

1. Plausibility: net_total + vat_total must (approximately) equal gross_total.
2. Confidence: any field whose confidence is below the threshold (default
   0.8, overridable via CONFIDENCE_THRESHOLD) is flagged.

If anything is off, needs_review is set and the reasons are collected in
review_reasons — nothing is silently accepted.
"""

from __future__ import annotations

import os
from decimal import Decimal

from src.models import Confident, Record

# Default confidence threshold (mirrors SPEC.md and .env.example).
DEFAULT_THRESHOLD = 0.8

# Allowed rounding slack when checking net + vat ≈ gross (one cent).
PLAUSIBILITY_TOLERANCE = Decimal("0.01")


def validate(record: Record, *, threshold: float | None = None) -> Record:
    """Flag the Record for review where confidence is low or sums don't add up.

    Mutates and returns *record*: sets needs_review and fills review_reasons.
    """
    threshold = resolve_threshold(threshold)

    reasons = _low_confidence_reasons(record, threshold)
    reasons += _plausibility_reasons(record)

    record.needs_review = bool(reasons)
    record.review_reasons = reasons
    return record


def resolve_threshold(threshold: float | None) -> float:
    """Pick the threshold: explicit arg > CONFIDENCE_THRESHOLD env > default."""
    if threshold is not None:
        return threshold
    raw = os.getenv("CONFIDENCE_THRESHOLD")
    if raw:
        return float(raw)
    return DEFAULT_THRESHOLD


def _low_confidence_reasons(record: Record, threshold: float) -> list[str]:
    """Return a reason for every Confident field below *threshold*."""
    reasons: list[str] = []
    for name, value in record:
        if isinstance(value, Confident) and value.confidence < threshold:
            reasons.append(
                f"Feld '{name}' hat niedrige Confidence "
                f"({value.confidence:.2f} < {threshold:.2f})."
            )
    return reasons


def _plausibility_reasons(record: Record) -> list[str]:
    """Check that net + vat ≈ gross within the tolerance."""
    net = record.net_total.value
    vat = record.vat_total.value
    gross = record.gross_total.value

    if abs(net + vat - gross) > PLAUSIBILITY_TOLERANCE:
        return [
            f"Plausibilität verletzt: Netto ({net}) + USt ({vat}) "
            f"= {net + vat} ≠ Brutto ({gross})."
        ]
    return []
