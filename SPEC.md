# SPEC.md — Dokument-zu-Aktion-Pipeline

## Problem
Kleine Betriebe tippen eingehende Belege (Rechnungen, Angebote) manuell ab, um sie zu erfassen und zu beantworten. Das ist langsam, fehleranfällig und nervt. Die Pipeline liest ein PDF automatisch aus, prüft die Daten und erzeugt einen Antwort-Entwurf.

## Zielnutzer
Solo-/KMU-Inhaber:innen (kaufmännisch, nicht technisch). Sie werfen ein PDF rein und bekommen saubere, strukturierte Daten plus einen Antwort-Vorschlag — ohne selbst zu tippen.

## Input → Output
- **Input:** ein PDF mit Textebene (Rechnung oder Angebot). Pfad wird der CLI übergeben.
- **Output:**
  1. validierter Datensatz als JSON (angehängt an `data/records.jsonl`)
  2. dieselbe Zeile als CSV (`data/records.csv`) zum Öffnen in Excel
  3. ein Antwort-/Bestätigungs-Entwurf als `.md` in `out/`
  4. Konsolen-Zusammenfassung mit Confidence und etwaigen Warnungen

## Zu extrahierende Felder
`doc_type` (rechnung/angebot), `vendor_name`, `vendor_iban` (optional), `document_number`, `document_date`, `due_date` (optional), `currency`, `net_total`, `vat_total`, `gross_total`, `line_items` (Liste: Beschreibung, Menge, Einzelpreis). Jedes Feld bekommt ein `confidence` (0–1).

## Kernfunktionen (Scope)
1. PDF-Text extrahieren (Textebene; gescannte PDFs ohne Text werden erkannt und sauber abgewiesen).
2. Strukturierte Extraktion über die Claude API mit festem JSON-Schema.
3. Validierung mit `pydantic` (Typen, Plausibilität: `net + vat ≈ gross`).
4. **Human-in-the-Loop:** Felder mit Confidence unter Schwellwert (z.B. 0.8) oder fehlgeschlagener Plausibilität werden als `needs_review` geflaggt, nicht still übernommen.
5. **Idempotenz:** gleiche `vendor_name + document_number` wird nicht doppelt gespeichert.
6. Antwort-Entwurf generieren (höflicher Eingangs-/Bestätigungstext, deutsch).

## Ausdrücklich NICHT im Scope (spätere Schritte)
- OCR für gescannte PDFs
- Google Sheets / Notion-Anbindung (kommt als zweiter Schritt nach lokalem MVP)
- E-Mail-Abruf (Pipeline bekommt vorerst nur lokale PDF-Pfade)
- Web-UI

## Erfolgskriterien
- 5 reale Beispiel-PDFs werden korrekt ausgelesen; Kernfelder stimmen.
- Bei einem absichtlich unklaren PDF werden die richtigen Felder als `needs_review` geflaggt.
- Dieselbe Rechnung zweimal eingespielt → nur ein Datensatz (Idempotenz greift).
- `net + vat = gross` wird geprüft; Abweichung erzeugt Warnung.

## Tech-Entscheidungen
- **Sprache:** Python 3.12, Paketmanager `uv`
- **PDF:** `pdfplumber` (Fallback `pypdf`)
- **KI:** `anthropic` SDK, strukturierter Output via Tool/JSON-Schema
- **Validierung:** `pydantic`
- **Speicher:** lokal — `data/records.jsonl` + `data/records.csv`
- **Tests:** `pytest`

## Offene Fragen
- Soll der Antwort-Entwurf nur „Eingang bestätigt" sein oder gleich auf Zahlungsziel/Konditionen eingehen? (Default: schlichte Eingangsbestätigung.)
