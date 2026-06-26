# Implementierungsplan — pd-doc-pipeline (Projekt 1)

> Dieser Plan wird **schrittweise mit Claude Code** umgesetzt. Jeder Schritt unten ist ein **eigener, fertiger Prompt** zum Kopieren. Reihenfolge einhalten — die Schritte bauen aufeinander auf. Nach jedem Schritt: Code prüfen, Tests laufen lassen, in `PLAN.md` abhaken, sauberer Commit.

## Eingearbeitete Entscheidungen (aus dem Sparring)
- **Modell:** konfigurierbar via `.env` (`ANTHROPIC_MODEL`), Default `claude-haiku-4-5-20251001`. Auf Sonnet umstellbar ohne Code-Änderung.
- **Antwort-Entwurf:** Default schlichte Eingangsbestätigung. Optionaler Konditionen-Block (Betrag/Frist) nur, wenn relevante Felder über der Confidence-Schwelle liegen und kein `needs_review` gesetzt ist. Schalter: `DRAFT_INCLUDE_CONDITIONS` (Default `false`).
- **Test-PDFs:** werden synthetisch generiert (deutsch, mit Textebene) — eigener Schritt.
- **Confidence-Schwelle:** 0.8 (aus SPEC), konfigurierbar via `.env` (`CONFIDENCE_THRESHOLD`).
- **CSV-Format:** UTF-8 mit BOM + Semikolon-Trenner (österreichisches Excel: Semikolon als Listentrenner, BOM für korrekte Umlaute).
- **Abhängigkeiten:** Runtime — pdfplumber, pypdf, anthropic, pydantic, python-dotenv. Dev — pytest, reportlab.

## Hinweis zu „Skills" in den Prompts
Jeder Prompt nennt am Anfang die relevanten installierten Skills. Wo kein Skill inhaltlich passt, steht das ausdrücklich da — dann gelten nur die Konventionen aus `CLAUDE.md`. Für dieses Python-Projekt ist v.a. der **`pdf`-Skill** relevant (PDF-Textebene erkennen, Text/Tabellen auslesen, PDFs erzeugen); der **`xlsx`-Skill** ist beim CSV-Output nützlich.

---

## Schritt 0 — SPEC/PLAN zusammenfassen + offene Fragen

**Relevante Skills:** keiner — reines Verständnis. Halte dich an `CLAUDE.md`.

```
Lies CLAUDE.md, SPEC.md und PLAN.md vollständig. Schreibe mir KEINEN Code.

1. Fasse in maximal 10 Sätzen zusammen, was die Pipeline tun soll (Input → Module → Output).
2. Liste alle offenen Punkte oder Widersprüche auf, die du vor dem Bauen geklärt haben willst.
3. Bestätige die Reihenfolge der Aufgaben aus PLAN.md.

Warte auf mein OK, bevor du mit Schritt 1 beginnst.
```

---

## Schritt 1 — Projektgerüst mit uv aufsetzen

**Relevante Skills:** keiner. Konventionen aus `CLAUDE.md` (Struktur: `src/`, `tests/`, `data/`, `out/`).

```
Setze das uv-Projekt auf. Frag nach, bevor du Pakete installierst (CLAUDE.md, Sicherheit).

- pyproject.toml mit Python 3.12. Runtime-Abhängigkeiten: pdfplumber, pypdf, anthropic, pydantic, python-dotenv. Dev-Abhängigkeiten: pytest, reportlab (Letzteres nur zum Erzeugen der Test-PDFs in Schritt 8).
- Ordner anlegen: src/, tests/, data/, out/ (data/ und out/ mit .gitkeep).
- .env.example um die nötigen Schlüssel-Namen ergänzen: ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CONFIDENCE_THRESHOLD, DRAFT_INCLUDE_CONDITIONS. Keine Werte committen.
- Sicherstellen, dass .env, data/ und out/ in .gitignore stehen (data/.gitkeep und out/.gitkeep ausnehmen).
- README.md kurz um Setup-Befehle (uv) ergänzen.

Danach: zeig mir die Ordnerstruktur und committe mit 'chore: uv-Projektgerüst aufsetzen'.
```

---

## Schritt 2 — Pydantic-Modelle (Datensatz + Feld-Confidence)

**Relevante Skills:** keiner. Felddefinition exakt nach `SPEC.md`.

```
Definiere die Pydantic-Modelle in src/models.py nach SPEC.md, Abschnitt "Zu extrahierende Felder".

- Ein generisches Confidence-Wrapper-Konzept: jedes extrahierte Feld hat value + confidence (0–1).
- Modelle: LineItem (Beschreibung, Menge, Einzelpreis), und das Hauptmodell Record mit: doc_type (rechnung/angebot als Enum), vendor_name, vendor_iban (optional), document_number, document_date, due_date (optional), currency, net_total, vat_total, gross_total, line_items (Liste).
- Zusätzliche Meta-Felder am Record: needs_review (bool), review_reasons (Liste von Strings), source_file (str).
- Sinnvolle Typen (Datumsfelder als date, Beträge als Decimal).

Schreibe einen kurzen pytest-Test, der ein Beispiel-Record gültig instanziiert und eine ungültige doc_type ablehnt.
Committe mit 'feat: Pydantic-Modelle für Datensatz und Confidence'.
```

---

## Schritt 3 — PDF-Text extrahieren (`extract`)

**Relevante Skills:** **`pdf`** — für das Erkennen der Textebene (Text vorhanden vs. gescannt) und das Auslesen von Text/Tabellen. Lies den `pdf`-Skill, bevor du startest.

```
Bevor du startest: nutze den pdf-Skill als Referenz für PDF-Textebenen.

Implementiere src/extract.py:
- Funktion extract_text(pdf_path) -> str: liest die Textebene mit pdfplumber aus (Fallback pypdf).
- Gescannte PDFs ohne nutzbare Textebene erkennen (z.B. Text leer/zu kurz nach Trim) und mit einer klaren, deutschen Fehlermeldung als eigener Exception-Typ (NoTextLayerError) abweisen — KEIN OCR (out of scope laut SPEC).
- Keine Netzwerk-Calls in diesem Modul.

Tests: ein PDF mit Textebene liefert Text; ein leeres/scan-artiges PDF wirft NoTextLayerError. (Fixtures kommen in Schritt 8 — hier vorerst mit einem minimalen Inline-PDF oder Mock testen.)
Committe mit 'feat: PDF-Textextraktion mit Erkennung gescannter PDFs'.
```

---

## Schritt 4 — Strukturierte Extraktion über Claude (`classify_extract`)

**Relevante Skills:** keiner direkt (eigener Claude-API-Call). `pdf`-Skill nur als Hintergrund zum Tabellenverständnis.

```
Implementiere src/classify_extract.py:
- Liest ANTHROPIC_API_KEY und ANTHROPIC_MODEL aus der Umgebung (.env via python-dotenv). Default-Modell: claude-haiku-4-5-20251001, wenn ANTHROPIC_MODEL fehlt.
- Funktion classify_extract(text) -> dict: schickt den PDF-Text an die Claude API und erzwingt strukturierten Output über ein festes JSON-Schema (Tool-Use / tools mit input_schema), passend zu den Pydantic-Modellen aus Schritt 2. Jedes Feld kommt mit value + confidence zurück.
- Prompt auf Deutsch, klar instruiert: nur extrahieren was im Text steht, nichts erfinden; doc_type als rechnung/angebot klassifizieren.
- Robustes Error-Handling (Timeout, fehlender Key → klare deutsche Meldung).

Frag mich um Bestätigung, bevor du echte API-Calls im Test ausführst. Schreibe die Logik so, dass der API-Call in Tests gemockt werden kann.
Committe mit 'feat: strukturierte Extraktion via Claude API mit JSON-Schema'.
```

---

## Schritt 5 — Validierung + `needs_review`-Flags (`validate`)

**Relevante Skills:** keiner. Plausibilitätsregeln aus `SPEC.md`.

```
Implementiere src/validate.py:
- Funktion validate(raw: dict) -> Record: mappt den Claude-Output auf das Pydantic-Record.
- Plausibilität: net_total + vat_total ≈ gross_total (kleine Rundungstoleranz, z.B. 0.02). Bei Abweichung: needs_review=True + Grund in review_reasons.
- Confidence-Schwelle aus .env (CONFIDENCE_THRESHOLD, Default 0.8): liegt ein Kernfeld darunter, needs_review=True + Grund.
- Typ-/Pflichtfeld-Verstöße führen ebenfalls zu needs_review statt zum Absturz.

Tests: gültiger Datensatz → needs_review=False; Summen-Abweichung → True; ein Feld unter Schwelle → True (mit passendem Grund).
Committe mit 'feat: Validierung mit Plausibilitaets- und Confidence-Pruefung'.
```

---

## Schritt 6 — Speichern mit Duplikat-Check (`store`)

**Relevante Skills:** **`xlsx`** — als Referenz für sauberen tabellarischen CSV-Output (Spalten, Encoding, Excel-Kompatibilität). Lies den `xlsx`-Skill kurz an.

```
Bevor du startest: nutze den xlsx-Skill als Referenz für sauberen, Excel-kompatiblen CSV-Output. Format ist entschieden: UTF-8 mit BOM + Semikolon-Trenner (österreichisches Excel). Kurz im README begründen.

Implementiere src/store.py:
- Append eines Records an data/records.jsonl (eine JSON-Zeile pro Datensatz).
- Dieselbe Zeile flach nach data/records.csv schreiben (Header beim ersten Mal anlegen). line_items sinnvoll serialisieren (z.B. als JSON-String in einer Spalte).
- Idempotenz: gleiche Kombination aus vendor_name + document_number wird NICHT doppelt gespeichert. Vor dem Schreiben prüfen; bei Duplikat klare Konsolen-Info, kein zweiter Eintrag.

Tests: zweimaliges Speichern desselben Records → nur ein Eintrag in jsonl und csv.
Committe mit 'feat: Speicherung in jsonl und csv mit Idempotenz-Check'.
```

---

## Schritt 7 — Antwort-Entwurf generieren (`draft`)

**Relevante Skills:** keiner direkt. Sprache Deutsch (österreichisch), Tonfall höflich-geschäftlich.

```
Implementiere src/draft.py:
- Funktion draft(record: Record) -> str: erzeugt einen deutschen Antwort-/Bestätigungstext und schreibt ihn als .md nach out/ (Dateiname aus document_number + vendor_name).
- Default: schlichte Eingangsbestätigung ("Beleg erhalten, wird bearbeitet"), KEINE Zahlen-Zusagen.
- Optionaler Konditionen-Block (Betrag, Zahlungsziel): NUR rendern, wenn DRAFT_INCLUDE_CONDITIONS=true UND die relevanten Felder (gross_total, due_date) über der Confidence-Schwelle liegen UND needs_review=False. Sonst weglassen.
- Bei needs_review immer einen sichtbaren Hinweis in den Entwurf setzen ("Bitte vor Versand prüfen").

Tests: ohne Flag → kein Konditionen-Block; mit Flag + hoher Confidence → Block vorhanden; mit Flag aber needs_review → kein Block, aber Prüf-Hinweis.
Committe mit 'feat: deutscher Antwort-Entwurf mit optionalem Konditionen-Block'.
```

---

## Schritt 8 — Test-PDFs generieren (synthetische Fixtures)

**Relevante Skills:** **`pdf`** — zum Erzeugen von PDFs mit echter Textebene. Lies den `pdf`-Skill, bevor du startest.

```
Bevor du startest: nutze den pdf-Skill zum Erzeugen von PDFs mit echter Textebene. Verwende reportlab (Dev-Abhängigkeit) zum Erzeugen der PDFs.

Erzeuge unter tests/fixtures/ synthetische, deutschsprachige Beispiel-PDFs mit Textebene:
- 5 realistische, korrekte Belege: Mischung aus Rechnungen und Angeboten, mit Briefkopf, Belegnummer, Datum, Positionen, Netto/USt/Brutto, einer mit IBAN.
- 1 absichtlich unklarer Beleg (z.B. fehlende/uneindeutige Summen), der needs_review auslösen soll.
- 1 "gescanntes" PDF ohne Textebene (reines Bild), das sauber abgewiesen werden soll.

Lege ein kleines Skript scripts/make_fixtures.py an, das diese PDFs reproduzierbar erzeugt, und dokumentiere kurz, was jede Datei testen soll.
Committe mit 'test: synthetische Beispiel-PDFs als Fixtures'.
```

---

## Schritt 9 — CLI verdrahten (`main`)

**Relevante Skills:** keiner.

```
Implementiere src/main.py als CLI-Einstieg (python -m src.main <pfad.pdf>):
- Ablauf: extract → classify_extract → validate → store → draft.
- Am Ende eine Konsolen-Zusammenfassung: doc_type, Vendor, Belegnummer, Bruttobetrag, Gesamt-Confidence, needs_review (ja/nein) inkl. Gründe, Pfad zum erzeugten Entwurf.
- Gescanntes PDF (NoTextLayerError) sauber abfangen und verständlich melden, Exit-Code != 0.
- Fehlender API-Key o.ä. → klare deutsche Meldung statt Stacktrace.

Test: CLI mit einem Fixture-PDF (Claude-Call gemockt) läuft durch und schreibt jsonl/csv/Entwurf.
Committe mit 'feat: CLI verdrahtet Extract-bis-Draft-Pipeline'.
```

---

## Schritt 10 — Test-Suite vervollständigen

**Relevante Skills:** keiner. Erfolgskriterien aus `SPEC.md` als Checkliste.

```
Vervollständige die Tests gegen die Erfolgskriterien aus SPEC.md:
- 5 Beispiel-PDFs werden korrekt ausgelesen, Kernfelder stimmen (Claude-Call wo nötig gemockt, damit Tests offline und deterministisch laufen).
- Das unklare PDF flaggt die richtigen Felder als needs_review.
- Dieselbe Rechnung zweimal eingespielt → nur ein Datensatz (Idempotenz).
- net + vat ≠ gross erzeugt eine Warnung/needs_review.
- Das gescannte PDF wird sauber abgewiesen.

Stelle sicher: `pytest` ist komplett grün. Zeig mir die Test-Ausgabe.

Zusätzlich (manuell, NICHT Teil der pytest-Suite): ein echter Smoke-Test — ein reales Fixture-PDF über die CLI mit echtem API-Call laufen lassen und prüfen, ob die Kernfelder stimmen. Vorher um Bestätigung fragen (echter Netzwerk-Call, Kosten < 1 Cent). Ergebnis kurz festhalten.
Committe mit 'test: Erfolgskriterien aus SPEC abgedeckt'.
```

---

## Schritt 11 — README finalisieren + (optional) Demo-GIF

**Relevante Skills:** keiner (`pdf`/`xlsx` nur als Verweis im README, falls relevant).

```
Aktualisiere README.md auf den aktuellen Stand (Definition of Done aus CLAUDE.md):
- Was das Tool tut, Setup mit uv, .env-Variablen erklärt (ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CONFIDENCE_THRESHOLD, DRAFT_INCLUDE_CONDITIONS).
- Beispiel-Aufruf (python -m src.main data/beispiel.pdf) mit Beispiel-Output.
- Hinweis auf Scope-Grenzen (kein OCR, keine externe Anbindung).

Optional, falls Zeit: kurze Anleitung für ein Demo-GIF (PDF rein → Datensatz + Entwurf raus).
Hake alle erledigten Punkte in PLAN.md ab.
Committe mit 'docs: README auf aktuellen Stand und PLAN abgehakt'.
```

---

## Definition of Done (gesamtes Projekt)
Alle Schritte umgesetzt, `pytest` grün, README aktuell, alle Punkte in `PLAN.md` abgehakt, sauber committet/gepusht — und die vier Erfolgskriterien aus `SPEC.md` erfüllt.
