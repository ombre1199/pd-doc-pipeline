"""Structured extraction of invoice/quote fields via the Claude API.

Sends the extracted PDF text together with a fixed JSON schema (an
Anthropic "tool") to the model and parses the returned tool input back
into a Record. Every field carries its own confidence score (0-1).

Plausibility checks and the needs_review flags are *not* set here — that
happens later in src/validate.py. This module only turns text into a
structured (but not yet validated) Record.
"""

from __future__ import annotations

import os
from typing import Any

from anthropic import Anthropic

from src.models import Record

# Default model when ANTHROPIC_MODEL is unset (mirrors .env.example).
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Name of the tool the model is forced to call. Keep in sync with the
# tool_choice below.
TOOL_NAME = "rechnungsfelder_erfassen"


class ClassifyError(Exception):
    """Raised when the Claude response contains no usable structured output."""


def _confident(value_schema: dict[str, Any], description: str) -> dict[str, Any]:
    """Wrap a value schema as a {value, confidence} object schema."""
    return {
        "type": "object",
        "description": description,
        "properties": {
            "value": value_schema,
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Sicherheit der Extraktion dieses Feldes (0-1).",
            },
        },
        "required": ["value", "confidence"],
    }


# A monetary amount or quantity, returned as a decimal string ("100.00")
# so we keep exact precision when parsing into Decimal.
_DECIMAL_STRING = {
    "type": "string",
    "description": "Dezimalzahl als String, z.B. \"100.00\" (Punkt als Trenner).",
}

_DATE_STRING = {
    "type": "string",
    "description": "Datum im Format YYYY-MM-DD.",
}

# The JSON schema handed to the model as a tool. It mirrors the Record
# model: each field is a {value, confidence} pair; optional fields are
# nullable.
EXTRACTION_TOOL = {
    "name": TOOL_NAME,
    "description": (
        "Erfasst die Felder einer Rechnung oder eines Angebots strukturiert. "
        "Gib für jedes Feld einen Wert und eine Confidence (0-1) an. Erfinde "
        "keine Werte: ist ein optionales Feld nicht im Text, setze es auf null."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "doc_type": _confident(
                {"type": "string", "enum": ["rechnung", "angebot"]},
                "Art des Dokuments.",
            ),
            "vendor_name": _confident(
                {"type": "string"}, "Name des Absenders/Lieferanten."
            ),
            "vendor_iban": {
                "oneOf": [
                    _confident({"type": "string"}, "IBAN des Absenders."),
                    {"type": "null"},
                ],
                "description": "IBAN, falls vorhanden, sonst null.",
            },
            "document_number": _confident(
                {"type": "string"}, "Rechnungs- bzw. Angebotsnummer."
            ),
            "document_date": _confident(_DATE_STRING, "Ausstellungsdatum."),
            "due_date": {
                "oneOf": [
                    _confident(_DATE_STRING, "Zahlungsziel/Fälligkeitsdatum."),
                    {"type": "null"},
                ],
                "description": "Fälligkeitsdatum, falls vorhanden, sonst null.",
            },
            "currency": _confident(
                {"type": "string"}, "Währung als ISO-Code, z.B. EUR."
            ),
            "net_total": _confident(_DECIMAL_STRING, "Nettobetrag (Summe)."),
            "vat_total": _confident(_DECIMAL_STRING, "Umsatzsteuerbetrag (Summe)."),
            "gross_total": _confident(_DECIMAL_STRING, "Bruttobetrag (Summe)."),
            "line_items": {
                "type": "array",
                "description": "Einzelpositionen des Dokuments.",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": _DECIMAL_STRING,
                        "unit_price": _DECIMAL_STRING,
                    },
                    "required": ["description", "quantity", "unit_price"],
                },
            },
        },
        "required": [
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
        ],
    },
}

SYSTEM_PROMPT = (
    "Du bist ein präziser Assistent zur Belegerfassung. Du erhältst den "
    "Rohtext einer deutschsprachigen Rechnung oder eines Angebots und gibst "
    "die Felder ausschließlich über das bereitgestellte Tool zurück. "
    "Halte dich strikt an den Text — rate nicht. Wenn ein Wert unsicher oder "
    "nicht eindeutig ist, vergib eine niedrige Confidence. Optionale Felder, "
    "die nicht im Text stehen, setzt du auf null. Beträge gibst du als "
    "Dezimal-String mit Punkt als Trenner zurück (z.B. \"1234.50\"), Datums- "
    "werte im Format YYYY-MM-DD."
)


def classify_extract(
    text: str,
    source_file: str,
    *,
    client: Anthropic | None = None,
    model: str | None = None,
) -> Record:
    """Extract structured fields from *text* via the Claude API.

    Returns a Record built from the model's tool output. The needs_review
    flags are left at their defaults — validation happens separately.

    A custom *client* can be injected for testing; otherwise a default
    Anthropic client is created (it reads ANTHROPIC_API_KEY from the env).
    """
    client = client or Anthropic()
    model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": (
                    "Erfasse die Felder aus folgendem Belegtext:\n\n" + text
                ),
            }
        ],
    )

    payload = _tool_input(response)
    return Record.model_validate({**payload, "source_file": source_file})


def _tool_input(response: Any) -> dict[str, Any]:
    """Return the input of the first tool_use block in *response*."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
            return dict(block.input)
    raise ClassifyError(
        "Die Claude-Antwort enthielt keinen strukturierten Tool-Output."
    )
