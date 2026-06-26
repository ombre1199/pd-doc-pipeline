# Kontext: Showcase-Sprint — Setup & Arbeitsweise

> An den Anfang jeder neuen Cowork-/Desktop-Session einfügen, damit der Assistent sofort weiß, wo ich stehe.

## Wer / Was
- Raphael, platzhirschdigital.at — KI-Automatisierung, Solo, Österreich (nebenberuflich).
- Ziel des Sprints: 6 Showcase-Projekte bauen → Skills + verkaufbare Service-Beispiele.
- **Stack: Claude Desktop (planen/strukturieren) + Claude Code (umsetzen). Kein n8n.**
- Sprache: österreichisches Deutsch, direkt und pragmatisch. Schritt-für-Schritt erklären.

## Umgebung (steht bereits)
- Windows, VS Code, PowerShell.
- Installiert: Node, npm, git, Python 3.12, gh (GitHub CLI), vercel CLI.
- GitHub-Account verbunden (`gh auth login`). Git-Identität gesetzt. `core.autocrlf true`.
- Anthropic-API-Key vorhanden (Console, mit Guthaben). Liegt pro Projekt in `.env` (nie committen).

## GitHub-Aufbau
- Projekt-Heimat: `D:\PlatzhirschDigital\`
- **Template-Repo:** `pd-template` (public, als Template markiert). Enthält das Gerüst.
- **Neues Projekt anlegen** (aus `D:\PlatzhirschDigital`):
  ```powershell
  $me = gh api user --jq .login
  gh repo create pd-<projektname> --public --template "$me/pd-template" --clone
  ```

## Template-Dateien (in jedem Repo)
- `CLAUDE.md` — Briefing, das Claude Code automatisch liest: Konventionen, Sicherheit, Definition of Done. Pro Projekt nur „Projekt" + „Stack" anpassen.
- `SPEC.md` — was gebaut wird (in Desktop ausfüllen).
- `PLAN.md` — Bauplan/Aufgabenliste (Claude Code hakt ab).
- `.gitignore`, `.env.example`, `README.md`.

## Konventionen (aus CLAUDE.md)
- Doku/Commits/User-Texte: Deutsch. Code/Logs: Englisch.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:` …), klein und thematisch.
- Tests für nicht-triviale Logik; vor „fertig" grün.
- Secrets nur in `.env`. Vor Installs / externen Calls / schreibenden Aktionen nachfragen.

## Arbeitsablauf pro Projekt
1. **Spec sparren** (Desktop): Problem, Nutzer, Input/Output, Scope, Erfolgskriterien → `SPEC.md`.
2. **Plan** (Desktop): Architektur, Risiken, Aufgaben → `PLAN.md`. In kleine Einzel-Prompts herunterbrechen.
3. **Bauen** (Claude Code): erst SPEC/PLAN zusammenfassen lassen + offene Fragen, dann auf OK Aufgabe für Aufgabe.
4. **Härten:** Tests, Fehlerbehandlung, README.
5. **Verpacken:** Demo-GIF, Case Study (½ Seite), Eintrag im Portfolio.

## Die 6 Projekte (Reihenfolge)
1. **pd-doc-pipeline** — Dokument-zu-Aktion (PDF → strukturierte Daten → Antwort-Entwurf). *Python.* ← aktuell
2. **pd-knowledge-bot** — RAG-Wissens-Assistent mit Quellen + Evals.
3. **pd-dashboard** — Next.js Web-App + KI-Feature, auf Vercel; dient auch als Portfolio.
4. **pd-content-engine** — mehrstufige Content-Pipeline mit Brand-Voice-Check.
5. **pd-mcp-server** — eigener MCP-Server, in Claude Desktop nutzbar.
6. **pd-workflow-agent** — autonomer Agent (Capstone), bündelt P1–P5.

## Status
- Setup abgeschlossen. `pd-template` steht. `pd-doc-pipeline` geklont, SPEC + PLAN ausgefüllt.
- Nächster Schritt: Projekt 1 in Claude Code bauen (Aufgaben aus `PLAN.md`).

## So starte ich eine neue Session
„Hier ist mein Kontext (siehe oben). Ich arbeite an Projekt X. Lass uns die SPEC sparren und in einzelne, kleine Prompts für Claude Code herunterbrechen."
