"""End-to-end tests for the success criteria from SPEC.md ("Erfolgskriterien").

Each test traces one acceptance criterion against the synthetic fixtures. The
Claude call is faked so everything runs offline and deterministically — the
real semantic extraction is covered separately by the manual smoke test
(siehe README / IMPLEMENTIERUNGSPLAN Schritt 10).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.classify_extract import TOOL_NAME
from src.extract import NoTextLayerError, extract_text
from src.main import run_pipeline

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_client(payload: dict) -> SimpleNamespace:
    """Anthropic-compatible stub returning a canned tool_use response."""
    block = SimpleNamespace(type="tool_use", name=TOOL_NAME, input=payload)
    response = SimpleNamespace(content=[block])
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **k: response))


def _base_payload() -> dict:
    """A valid, plausible, high-confidence extraction payload."""
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


# --- Kriterium 1: 5 Beispiel-PDFs werden korrekt ausgelesen ----------------

# Kernfelder (vendor_name, document_number, Bruttobetrag), die in der
# Textebene jeder korrekten Fixture vorkommen müssen.
CORE_FIELDS = [
    ("rechnung_01_buerobedarf.pdf", "Bürowelt Handels GmbH", "RE-2026-0042", "217,80"),
    ("rechnung_02_it_dienstleistung.pdf", "NetzWerk IT-Services e.U.", "2026-114", "1.224,00"),
    ("rechnung_03_handwerk.pdf", "Tischlerei Moser", "R2026/87", "1.170,00"),
    ("angebot_01_webdesign.pdf", "Pixelschmiede Werbeagentur", "AN-2026-018", "3.840,00"),
    ("angebot_02_beratung.pdf", "Consult & Co Unternehmensberatung", "ANG-2026-205", "4.320,00"),
]


@pytest.mark.parametrize("filename,vendor,number,gross", CORE_FIELDS)
def test_kriterium1_fixtures_werden_korrekt_ausgelesen(filename, vendor, number, gross):
    text = extract_text(FIXTURES / filename)

    assert vendor in text
    assert number in text
    assert gross in text


def test_kriterium1_iban_wird_ausgelesen():
    # Nur die Bürobedarf-Rechnung trägt eine IBAN.
    text = extract_text(FIXTURES / "rechnung_01_buerobedarf.pdf")

    assert "AT61" in text


# --- Kriterium 2: unklarer Beleg flaggt die richtigen Felder ---------------

def test_kriterium2_unklarer_beleg_wird_geflaggt(tmp_path):
    # Faithful mock of the contradictory totals printed on unklar_summen.pdf:
    # net 600 + vat 120 = 720, but the document states gross 700.
    payload = _base_payload()
    payload["document_number"] = {"value": "RE-2026-0099", "confidence": 0.9}
    payload["net_total"] = {"value": "600.00", "confidence": 0.9}
    payload["vat_total"] = {"value": "120.00", "confidence": 0.9}
    payload["gross_total"] = {"value": "700.00", "confidence": 0.9}

    result = run_pipeline(
        FIXTURES / "unklar_summen.pdf",
        client=_fake_client(payload),
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "out",
    )

    assert result.record.needs_review is True
    assert any("Plausibilität" in r for r in result.record.review_reasons)


# --- Kriterium 3: Idempotenz -----------------------------------------------

def test_kriterium3_dieselbe_rechnung_nur_einmal(tmp_path):
    pdf = FIXTURES / "rechnung_01_buerobedarf.pdf"
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "out"

    first = run_pipeline(pdf, client=_fake_client(_base_payload()), data_dir=data_dir, out_dir=out_dir)
    second = run_pipeline(pdf, client=_fake_client(_base_payload()), data_dir=data_dir, out_dir=out_dir)

    assert first.stored is True
    assert second.stored is False

    lines = [
        line
        for line in (data_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(lines) == 1


# --- Kriterium 4: net + vat != gross erzeugt eine Warnung ------------------

def test_kriterium4_summenabweichung_erzeugt_warnung(tmp_path):
    payload = _base_payload()  # net 100 + vat 20 = 120
    payload["gross_total"] = {"value": "999.00", "confidence": 0.95}

    result = run_pipeline(
        FIXTURES / "rechnung_01_buerobedarf.pdf",
        client=_fake_client(payload),
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "out",
    )

    assert result.record.needs_review is True
    assert any("Plausibilität" in r for r in result.record.review_reasons)


# --- Kriterium 5: gescanntes PDF wird sauber abgewiesen --------------------

def test_kriterium5_gescanntes_pdf_wird_abgewiesen(tmp_path):
    with pytest.raises(NoTextLayerError):
        run_pipeline(
            FIXTURES / "gescannt_ohne_textebene.pdf",
            client=_fake_client(_base_payload()),
            data_dir=tmp_path / "data",
            out_dir=tmp_path / "out",
        )
