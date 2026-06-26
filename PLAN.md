# PLAN.md — Dokument-zu-Aktion-Pipeline

## Architektur (kurz)
CLI bekommt einen PDF-Pfad → Modul `extract` liest den Text (Textebene; kein Text → sauber abbrechen) → Modul `classify_extract` schickt Text + JSON-Schema an die Claude API und bekommt strukturierte Felder mit Confidence zurück → Modul `validate` prüft Typen und Plausibilität (`net + vat ≈ gross`) und setzt `needs_review`-Flags → Modul `store` prüft auf Duplikat und hängt an `records.jsonl` + `records.csv` an → Modul `draft` erzeugt den Antwort-Entwurf. Alles wird in der Konsole zusammengefasst.

## Risiken & Annahmen
- **Gescanntes PDF ohne Textebene** → Gegenmaßnahme: erkennen und mit klarer Meldung abweisen (OCR ist out of scope).
- **Falsche Extraktion** → Gegenmaßnahme: Confidence-Schwelle + Plausibilitätsprüfung + `needs_review` statt blindem Speichern.
- **Doppelte Verarbeitung** → Gegenmaßnahme: Idempotenz über `vendor_name + document_number`.
- **Annahme:** Test-PDFs sind echte, deutschsprachige Rechnungen/Angebote mit Textebene.

## Aufgaben
- [x] uv-Projekt aufsetzen (`pyproject.toml`, `src/`, `tests/`, `data/`, `out/`)
- [x] Pydantic-Modelle für Datensatz + Feld-Confidence definieren
- [x] `extract`: PDF-Text auslesen, „kein Text"-Fall behandeln
- [x] `classify_extract`: Claude-Call mit JSON-Schema, strukturierter Output
- [x] `validate`: Typen + Plausibilität + `needs_review`-Flags
- [x] `store`: Duplikat-Check, Append in jsonl + csv
- [x] `draft`: Antwort-Entwurf generieren (deutsch)
- [x] CLI verdrahten (`python -m src.main <pfad.pdf>`)
- [x] Tests mit 5 Beispiel-PDFs + 1 unklarem + 1 gescannten
- [ ] README mit Setup + Beispiel aktualisieren
- [ ] Demo-GIF: PDF rein → Datensatz + Entwurf raus

## Definition of Done
Alle Aufgaben abgehakt, `pytest` grün, README aktuell, sauber gepusht. Erfolgskriterien aus der SPEC erfüllt.
