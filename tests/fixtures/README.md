# Test-Fixtures (synthetische PDFs)

Diese PDFs sind **synthetisch** erzeugt — keine echten Kundendaten. Sie werden
reproduzierbar von `scripts/make_fixtures.py` generiert:

```bash
uv run python scripts/make_fixtures.py
```

| Datei | Was sie testen soll |
|---|---|
| `rechnung_01_buerobedarf.pdf` | Korrekte Rechnung **mit IBAN**, mehrere Positionen. |
| `rechnung_02_it_dienstleistung.pdf` | Korrekte Rechnung (Dienstleistung), ohne IBAN. |
| `rechnung_03_handwerk.pdf` | Korrekte Rechnung (Handwerk), mit Zahlungsziel. |
| `angebot_01_webdesign.pdf` | Korrektes **Angebot** (kein Zahlungsziel). |
| `angebot_02_beratung.pdf` | Korrektes Angebot (Beratungsleistung). |
| `unklar_summen.pdf` | Unplausibel: Netto + USt ≠ Brutto → muss `needs_review` auslösen. |
| `gescannt_ohne_textebene.pdf` | Reines Bild ohne Textebene → muss mit `NoTextLayerError` abgewiesen werden. |

Alle PDFs sind deutschsprachig und (bis auf das gescannte) mit echter Textebene,
damit `extract` sie ohne OCR auslesen kann.
