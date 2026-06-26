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
cp .env.example .env   # dann Werte eintragen

# 3. Pipeline auf ein PDF anwenden (kommt in späteren Schritten)
uv run python -m src.main data/samples/beispiel.pdf
```

### Umgebungsvariablen (`.env`)
| Variable | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ja | – | API-Key für die Claude API |
| `ANTHROPIC_MODEL` | nein | `claude-haiku-4-5-20251001` | Modell für die Extraktion |
| `CONFIDENCE_THRESHOLD` | nein | `0.8` | Schwelle, unter der Felder `needs_review` auslösen |
| `DRAFT_INCLUDE_CONDITIONS` | nein | `false` | Konditionen-Block (Betrag/Frist) im Entwurf rendern |

## Status
In Entwicklung — Teil des Showcase-Sprints. Bauplan: `PLAN.md`, Anforderungen: `SPEC.md`.

## Anpassung für dich
Dieses Projekt lässt sich auf deinen Anwendungsfall zuschneiden. Kontakt: admin@platzhirschdigital.at
