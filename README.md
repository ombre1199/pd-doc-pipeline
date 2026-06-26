# pd-doc-pipeline

Ein Showcase-Projekt von [platzhirschdigital.at](https://platzhirschdigital.at).

## Was es macht
Liest Rechnungen und Angebote aus PDFs aus, validiert die Daten (Typen,
Plausibilität, Confidence) und erzeugt einen deutschen Antwort-Entwurf als
Markdown-Datei unter `out/`. Unklare oder unplausible Belege werden als
`needs_review` geflaggt statt still übernommen (Human-in-the-Loop) — der
Entwurf trägt dann einen sichtbaren Prüf-Hinweis.

## Tech
- Python 3.12, Paketmanager [`uv`](https://docs.astral.sh/uv/)
- PDF: `pdfplumber` (Fallback `pypdf`)
- KI: `anthropic` SDK (strukturierter Output via Tool-/JSON-Schema)
- Validierung: `pydantic`
- Tests: `pytest`

## Setup
```bash
# 1. Abhängigkeiten installieren (inkl. Dev-Tools)
uv sync

# 2. Umgebungsvariablen anlegen
cp .env.example .env   # dann ANTHROPIC_API_KEY eintragen

# 3. Pipeline auf ein PDF anwenden
uv run python -m src.main tests/fixtures/rechnung_01_buerobedarf.pdf
```

### Umgebungsvariablen (`.env`)
| Variable | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ja | – | API-Key für die Claude API |
| `ANTHROPIC_MODEL` | nein | `claude-haiku-4-5-20251001` | Modell für die Extraktion |
| `CONFIDENCE_THRESHOLD` | nein | `0.8` | Schwelle, unter der Felder `needs_review` auslösen |
| `DRAFT_INCLUDE_CONDITIONS` | nein | `false` | Konditionen-Block (Betrag/Frist) im Entwurf rendern |

## Ablauf
Die CLI verarbeitet ein PDF in fünf Schritten:

`extract` (Textebene auslesen) → `classify_extract` (strukturierte Felder via
Claude) → `validate` (Typen, Plausibilität, Confidence) → `store` (Duplikat-Check)
→ `draft` (Antwort-Entwurf).

Erzeugt werden dabei:
- `data/records.jsonl` — vollständiger Datensatz je Beleg (eine JSON-Zeile)
- `data/records.csv` — dieselben Daten flach, zum Öffnen in Excel (UTF-8 mit BOM, Semikolon-Trenner)
- `out/<Belegnummer>_<Lieferant>.md` — der Antwort-Entwurf
- eine Konsolen-Zusammenfassung mit Confidence und etwaigen Warnungen

## Beispiel
Aufruf:
```bash
uv run python -m src.main tests/fixtures/rechnung_01_buerobedarf.pdf
```
Konsolen-Ausgabe:
```
Beleg verarbeitet: tests/fixtures/rechnung_01_buerobedarf.pdf
  Typ:           Rechnung
  Lieferant:     Bürowelt Handels GmbH
  Belegnummer:   RE-2026-0042
  Bruttobetrag:  217.80 EUR
  Confidence:    1.00 (Durchschnitt)
  needs_review:  nein
  Gespeichert:   ja (neuer Datensatz)
  Entwurf:       out\RE-2026-0042_B_rowelt_Handels_GmbH.md
```
Erzeugter Entwurf (`out/...md`):
```markdown
# Antwort-Entwurf

Sehr geehrte Damen und Herren,

vielen Dank für Ihre Rechnung RE-2026-0042. Wir bestätigen den Eingang des
Belegs; er wird bei uns bearbeitet.

Mit freundlichen Grüßen

Platzhirsch Digital
```

## Nicht im Scope
Bewusste Grenzen des MVP (siehe `SPEC.md`):
- **Kein OCR** — gescannte PDFs ohne Textebene werden erkannt und sauber abgewiesen, nicht ausgelesen.
- **Keine externe Anbindung** — kein E-Mail-Abruf, keine Google-Sheets-/Notion-Integration, keine Web-UI. Die Pipeline bekommt lokale PDF-Pfade.

## Tests
```bash
uv run pytest
```
Die Tests laufen offline und deterministisch (der Claude-Call wird gemockt).

## Demo-GIF (optional)
Für eine kurze Demo den CLI-Aufruf mit einem Terminal-Recorder aufnehmen
(z.B. [`asciinema`](https://asciinema.org/) oder ein Bildschirm-Recorder):
PDF rein → Konsolen-Zusammenfassung + erzeugter Entwurf raus. Das Ergebnis als
`docs/demo.gif` ablegen und hier einbinden.

## Status
MVP fertig — alle Erfolgskriterien aus `SPEC.md` abgedeckt. Bauplan: `PLAN.md`,
Anforderungen: `SPEC.md`.

## Anpassung für dich
Dieses Projekt lässt sich auf deinen Anwendungsfall zuschneiden. Kontakt: admin@platzhirschdigital.at
