# Case Study: Dokument-zu-Aktion-Pipeline (pd-doc-pipeline)

**Projekt 1 von 6 · platzhirschdigital.at · KI-Automatisierung**

## Das Problem
Kleine Betriebe tippen eingehende Belege — Rechnungen, Angebote — manuell ab, um sie zu erfassen und zu beantworten. Das ist langsam, fehleranfällig und bindet Zeit, die im Tagesgeschäft fehlt. Pro Beleg gehen schnell ein paar Minuten drauf; bei Dutzenden pro Woche summiert sich das.

## Die Lösung
Eine Pipeline, die ein PDF automatisch ausliest, die Daten validiert und einen fertigen Antwort-Entwurf erzeugt. Ablauf: **PDF rein → Text extrahieren → strukturierte Felder mit Confidence (via Claude) → Validierung → speichern → deutscher Antwort-Entwurf raus.**

Zwei Design-Entscheidungen machen das Tool praxistauglich statt nur „nett":

- **Human-in-the-Loop statt blindem Vertrauen.** Felder unter einer Confidence-Schwelle (0,8) oder mit unplausiblen Summen (`Netto + USt ≠ Brutto`) werden als `needs_review` geflaggt — nicht still übernommen. Der Mensch prüft nur die unsicheren Fälle, nicht jeden Beleg.
- **Keine falschen Zusagen.** Der Antwort-Entwurf ist standardmäßig eine schlichte Eingangsbestätigung. Konkrete Beträge/Fristen erscheinen nur, wenn die Extraktion sicher genug war — per Schalter aktivierbar.

## Tech-Stack
Python 3.12 (uv) · pdfplumber/pypdf · Claude API mit erzwungenem JSON-Schema (Tool-Use) · pydantic-Validierung · pytest. Modell konfigurierbar via `.env` (Default: günstiges Haiku, ~1 Cent pro Beleg).

## Das Ergebnis
- **Alle vier Erfolgskriterien erfüllt:** Beispiel-Belege korrekt ausgelesen, unklare Belege korrekt als `needs_review` geflaggt, Duplikate werden nicht doppelt gespeichert (Idempotenz über Lieferant + Belegnummer), Summen-Plausibilität geprüft.
- **41 automatisierte Tests, alle grün.**
- **An einem echten Beleg validiert:** eine reale Vereinsrechnung wurde mit 0,99 durchschnittlicher Confidence korrekt erfasst, Summen plausibel, kein Review nötig — strukturierte Daten in CSV/JSON plus fertiger Antwort-Entwurf in unter einer Sekunde.
- **Sauber abgegrenzt:** Gescannte PDFs ohne Textebene werden erkannt und mit klarer Meldung abgewiesen statt falsch verarbeitet.

## Übertragbarkeit
Der Kern — PDF auslesen, mit Confidence validieren, Aktion entwerfen — lässt sich auf jeden belegbasierten Prozess übertragen: Bestellungen, Lieferscheine, Anträge. Die nächsten Ausbaustufen (E-Mail-Eingang, Ablage in Google Sheets/Notion, OCR für Scans) sind bereits als Roadmap definiert.

---
*Repository: vollständige Spec, Implementierungsplan und Tests öffentlich einsehbar.*
