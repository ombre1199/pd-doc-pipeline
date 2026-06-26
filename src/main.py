"""CLI entry point — run the full pipeline on a single PDF.

Usage:
    python -m src.main <pfad.pdf>

Flow: extract -> classify_extract -> validate -> store -> draft. At the end
a short German summary is printed. Expected error cases (scanned PDF, missing
API key, missing file) are reported with a clear message and a non-zero exit
code instead of a stack trace.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from anthropic import Anthropic, AnthropicError

from src.classify_extract import ClassifyError, classify_extract
from src.draft import draft, draft_filename
from src.extract import NoTextLayerError, extract_text
from src.models import Confident, Record
from src.store import store, stored_source_files
from src.validate import validate

_DOC_TYPE_LABEL = {"rechnung": "Rechnung", "angebot": "Angebot"}


@dataclass
class PipelineResult:
    """Outcome of one pipeline run."""

    source: str
    record: Record | None = None
    stored: bool = False
    draft_path: Path | None = None
    # True if the file was recognised as already processed and the whole
    # pipeline (including the paid Claude call) was skipped.
    skipped_existing: bool = False


def run_pipeline(
    pdf_path: str | Path,
    *,
    client: Anthropic | None = None,
    data_dir: str | Path = "data",
    out_dir: str | Path = "out",
) -> PipelineResult:
    """Run extract -> classify_extract -> validate -> store -> draft.

    A custom *client* can be injected so tests run offline. Raises the
    pipeline's own exceptions (NoTextLayerError, ClassifyError, ...) for the
    caller to translate into user-facing messages.

    If the exact same file was already processed, the pipeline returns early
    (skipped_existing=True) without calling the Claude API. The authoritative
    idempotency on vendor_name + document_number still runs in store() for
    the same invoice arriving as a different file.
    """
    source = str(Path(pdf_path).resolve())

    if source in stored_source_files(data_dir):
        return PipelineResult(source=source, skipped_existing=True)

    text = extract_text(pdf_path)
    record = classify_extract(text, source, client=client)
    record = validate(record)
    stored = store(record, data_dir=data_dir)
    draft(record, out_dir=out_dir)

    return PipelineResult(
        source=source,
        record=record,
        stored=stored,
        draft_path=Path(out_dir) / draft_filename(record),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper: parse args, run the pipeline, print a summary.

    Returns the process exit code (0 on success, non-zero on error).
    """
    # Ensure UTF-8 output so umlauts and math symbols (≠, ≈ in review
    # reasons) print on any console — Windows defaults to cp1252.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    # Load .env so ANTHROPIC_API_KEY/MODEL etc. are available. Optional
    # dependency-wise, but expected per the project setup.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("Aufruf: python -m src.main <pfad.pdf>", file=sys.stderr)
        return 2

    pdf_path = argv[0]

    if not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "Fehler: ANTHROPIC_API_KEY ist nicht gesetzt. Trage den Key in die "
            "Datei .env ein (siehe .env.example).",
            file=sys.stderr,
        )
        return 1

    try:
        result = run_pipeline(pdf_path)
    except FileNotFoundError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    except NoTextLayerError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    except ClassifyError as exc:
        print(f"Fehler bei der Extraktion: {exc}", file=sys.stderr)
        return 1
    except AnthropicError as exc:
        print(
            f"Fehler beim Aufruf der Claude API: {exc}",
            file=sys.stderr,
        )
        return 1

    _print_summary(result)
    return 0


def _print_summary(result: PipelineResult) -> None:
    """Print the German console summary for a finished run."""
    if result.skipped_existing:
        print(f"\nBeleg bereits verarbeitet: {result.source}")
        print("  Übersprungen — kein Claude-Aufruf, kein neuer Datensatz.")
        return

    record = result.record
    assert record is not None  # only None when skipped_existing
    doc_type = _DOC_TYPE_LABEL.get(
        record.doc_type.value.value, record.doc_type.value.value
    )

    print(f"\nBeleg verarbeitet: {record.source_file}")
    print(f"  Typ:           {doc_type}")
    print(f"  Lieferant:     {record.vendor_name.value}")
    print(f"  Belegnummer:   {record.document_number.value}")
    print(
        f"  Bruttobetrag:  {record.gross_total.value} {record.currency.value}"
    )
    print(f"  Confidence:    {_overall_confidence(record):.2f} (Durchschnitt)")

    if record.needs_review:
        print("  needs_review:  ja")
        for reason in record.review_reasons:
            print(f"    - {reason}")
    else:
        print("  needs_review:  nein")

    stored = "ja (neuer Datensatz)" if result.stored else "nein (Duplikat)"
    print(f"  Gespeichert:   {stored}")
    print(f"  Entwurf:       {result.draft_path}")


def _overall_confidence(record: Record) -> float:
    """Average confidence across all extracted fields."""
    scores = [
        value.confidence
        for _, value in record
        if isinstance(value, Confident)
    ]
    return sum(scores) / len(scores) if scores else 0.0


if __name__ == "__main__":
    sys.exit(main())
