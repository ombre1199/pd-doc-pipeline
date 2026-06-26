"""Generate a German reply draft for a validated Record.

The draft is a polite acknowledgement of receipt ("Beleg erhalten, wird
bearbeitet") and is written as a Markdown file to out/. By default it makes
no commitments about amounts or deadlines.

An optional conditions block (amount, payment deadline) is only rendered when
ALL of the following hold (see IMPLEMENTIERUNGSPLAN.md, Schritt 7):

1. DRAFT_INCLUDE_CONDITIONS is set to true, and
2. the relevant fields (gross_total, due_date) are above the confidence
   threshold, and
3. the record is not flagged for review.

If the record needs review, a visible hint is always added so the draft is
never sent unchecked (Human-in-the-Loop).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from src.models import DocType, Record
from src.validate import resolve_threshold


def draft(record: Record, *, out_dir: str | Path = "out") -> str:
    """Build the German reply draft for *record* and write it to *out_dir*.

    Returns the draft text (also written as a .md file named after the
    document number and vendor).
    """
    text = render_draft(record)

    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _draft_filename(record)
    path.write_text(text, encoding="utf-8")

    return text


def render_draft(record: Record) -> str:
    """Render the draft text without touching the filesystem."""
    parts = [
        "# Antwort-Entwurf",
        "",
        "Sehr geehrte Damen und Herren,",
        "",
        _acknowledgement(record),
    ]

    conditions = _conditions_block(record)
    if conditions:
        parts += ["", conditions]

    if record.needs_review:
        parts += ["", _review_hint(record)]

    parts += [
        "",
        "Mit freundlichen Grüßen",
        "",
        "Platzhirsch Digital",
        "",
    ]
    return "\n".join(parts)


def _acknowledgement(record: Record) -> str:
    """The neutral receipt confirmation — no amounts, no promises."""
    if record.doc_type.value == DocType.ANGEBOT:
        beleg = f"Ihr Angebot {record.document_number.value}"
    else:
        beleg = f"Ihre Rechnung {record.document_number.value}"
    return (
        f"vielen Dank für {beleg}. Wir bestätigen den Eingang des Belegs; "
        "er wird bei uns bearbeitet."
    )


def _conditions_block(record: Record) -> str:
    """Optional amount/deadline block, only if explicitly enabled and safe."""
    if not _include_conditions_enabled():
        return ""
    if record.needs_review:
        return ""
    if record.due_date is None:
        return ""

    threshold = resolve_threshold(None)
    if record.gross_total.confidence < threshold:
        return ""
    if record.due_date.confidence < threshold:
        return ""

    return "\n".join(
        [
            "**Konditionen laut Beleg**",
            "",
            f"- Bruttobetrag: {record.gross_total.value} {record.currency.value}",
            f"- Zahlungsziel: {record.due_date.value.isoformat()}",
        ]
    )


def _review_hint(record: Record) -> str:
    """Visible warning shown whenever the record is flagged for review."""
    lines = [
        "> ⚠️ **Bitte vor Versand prüfen.** "
        "Dieser Beleg wurde als prüfbedürftig markiert.",
    ]
    for reason in record.review_reasons:
        lines.append(f"> - {reason}")
    return "\n".join(lines)


def _include_conditions_enabled() -> bool:
    """Read DRAFT_INCLUDE_CONDITIONS from the environment (default: false)."""
    raw = os.getenv("DRAFT_INCLUDE_CONDITIONS", "")
    return raw.strip().lower() in {"true", "1", "yes", "ja"}


def _draft_filename(record: Record) -> str:
    """Build a filesystem-safe .md filename from document number + vendor."""
    stem = f"{record.document_number.value}_{record.vendor_name.value}"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    return f"{safe or 'entwurf'}.md"
