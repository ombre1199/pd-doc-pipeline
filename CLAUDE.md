# CLAUDE.md — Projekt-Briefing

> Diese Datei liest Claude Code beim Start automatisch. Sie definiert, wie in diesem Repo gearbeitet wird. Pro Projekt nur die Abschnitte „Projekt" und „Stack" anpassen — der Rest bleibt.

## Projekt
- **Name:** <projektname>
- **Was es tut:** <ein Satz>
- **Owner:** Raphael, platzhirschdigital.at (Solo, Österreich)
- Vollständige Anforderungen stehen in `SPEC.md`, der Bauplan in `PLAN.md`. Lies beide, bevor du Code schreibst.

## Stack
- <Sprache/Framework hier eintragen, z.B. Node 20 + TypeScript, oder Python 3.12>
- Claude API für KI-Funktionen (Key liegt in `.env`, siehe `.env.example`)
- Paketmanager: pnpm (JS) bzw. uv (Python)

## Arbeitsweise
- Halte dich an den Ablauf: erst `SPEC.md` und `PLAN.md` verstehen, dann in kleinen Schritten umsetzen.
- Arbeite die Aufgaben aus `PLAN.md` der Reihe nach ab. Hak erledigte Punkte dort ab.
- Wenn etwas in der Spec unklar oder widersprüchlich ist: **nachfragen, nicht raten.**
- Bevorzuge einfache, lesbare Lösungen vor cleveren. Dieses Repo ist auch ein Showcase — Code muss vorzeigbar sein.

## Konventionen
- **Sprache:** Doku, README, Commit-Messages und User-sichtbare Texte auf Deutsch (österreichisch). Code, Variablennamen und technische Logs auf Englisch.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Klein und thematisch — nicht zehn Änderungen in einen Commit.
- **Tests:** Für jede nicht-triviale Logik einen Test. Vor „fertig" muss die Test-Suite grün sein.
- **Struktur:** Quellcode in `src/`, Tests in `tests/`, Doku in `docs/`.

## Sicherheit — nicht verhandelbar
- **Niemals** Secrets, API-Keys oder Zugangsdaten in den Code oder in Git schreiben. Alles über `.env` (steht in `.gitignore`).
- `.env.example` aktuell halten (nur Schlüssel-Namen, keine Werte), damit klar ist, welche Variablen nötig sind.
- **Frag um Bestätigung, bevor du:** Pakete installierst, externe Netzwerk-Calls einbaust, Daten löschst/überschreibst oder schreibende Aktionen gegen echte Dienste ausführst.
- Bei KI-Funktionen mit unsicherem Output: lieber ein „Human-in-the-Loop"-Flag setzen als blind weiterverarbeiten.

## Definition of Done
Ein Feature gilt erst als fertig, wenn: Code läuft, Tests grün sind, `README.md` den aktuellen Stand beschreibt und ein sauberer Commit gepusht ist.
