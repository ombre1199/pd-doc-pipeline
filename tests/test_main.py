"""Tests for the CLI wiring (src/main.py).

extract runs for real against a fixture PDF (it has a real text layer); the
Claude call is faked so the pipeline runs offline and deterministically.
"""

from pathlib import Path
from types import SimpleNamespace

from src.classify_extract import TOOL_NAME
from src.main import main, run_pipeline

FIXTURES = Path(__file__).parent / "fixtures"


def _payload() -> dict:
    return {
        "doc_type": {"value": "rechnung", "confidence": 0.96},
        "vendor_name": {"value": "Bürowelt Handels GmbH", "confidence": 0.94},
        "vendor_iban": {"value": "AT611904300234573201", "confidence": 0.88},
        "document_number": {"value": "RE-2026-0042", "confidence": 0.95},
        "document_date": {"value": "2026-06-03", "confidence": 0.92},
        "due_date": {"value": "2026-06-17", "confidence": 0.9},
        "currency": {"value": "EUR", "confidence": 0.99},
        "net_total": {"value": "100.00", "confidence": 0.9},
        "vat_total": {"value": "20.00", "confidence": 0.9},
        "gross_total": {"value": "120.00", "confidence": 0.9},
        "line_items": [
            {"description": "Druckerpapier", "quantity": "5", "unit_price": "20.00"},
        ],
    }


class _FakeClient:
    """Anthropic-compatible stub returning a canned tool_use response."""

    def __init__(self, payload: dict):
        block = SimpleNamespace(type="tool_use", name=TOOL_NAME, input=payload)
        response = SimpleNamespace(content=[block])
        self.messages = SimpleNamespace(create=lambda **kwargs: response)


def test_run_pipeline_writes_outputs(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "out"

    result = run_pipeline(
        FIXTURES / "rechnung_01_buerobedarf.pdf",
        client=_FakeClient(_payload()),
        data_dir=data_dir,
        out_dir=out_dir,
    )

    assert result.stored is True
    assert result.record.needs_review is False
    assert (data_dir / "records.jsonl").exists()
    assert (data_dir / "records.csv").exists()
    assert result.draft_path.exists()
    assert result.draft_path.parent == out_dir


def test_run_pipeline_is_idempotent(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "out"
    pdf = FIXTURES / "rechnung_01_buerobedarf.pdf"

    first = run_pipeline(pdf, client=_FakeClient(_payload()), data_dir=data_dir, out_dir=out_dir)
    second = run_pipeline(pdf, client=_FakeClient(_payload()), data_dir=data_dir, out_dir=out_dir)

    assert first.stored is True
    assert second.stored is False  # same vendor + number → duplicate

    lines = (data_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


class _ExplodingClient:
    """A client whose use fails the test — proves no API call was made."""

    class _Messages:
        def create(self, **kwargs):
            raise AssertionError("Claude API wurde trotz Duplikat aufgerufen")

    messages = _Messages()


def test_rerun_same_file_skips_api_call(tmp_path):
    pdf = FIXTURES / "rechnung_01_buerobedarf.pdf"
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "out"

    first = run_pipeline(pdf, client=_FakeClient(_payload()), data_dir=data_dir, out_dir=out_dir)
    assert first.stored is True

    # The second run must short-circuit before touching the (exploding) client.
    second = run_pipeline(pdf, client=_ExplodingClient(), data_dir=data_dir, out_dir=out_dir)

    assert second.skipped_existing is True
    assert second.stored is False
    assert second.record is None


def test_scanned_pdf_raises_no_text_layer(tmp_path):
    from src.extract import NoTextLayerError

    try:
        run_pipeline(
            FIXTURES / "gescannt_ohne_textebene.pdf",
            client=_FakeClient(_payload()),
            data_dir=tmp_path / "data",
            out_dir=tmp_path / "out",
        )
    except NoTextLayerError:
        return
    raise AssertionError("NoTextLayerError wurde erwartet")


def test_main_wrong_arg_count_returns_2():
    assert main([]) == 2
    assert main(["a.pdf", "b.pdf"]) == 2
