# Projektanweisungen

<!-- skill-routing:start v1 – gepflegt mit ~/.claude/skill-routing/skill_routing.py; gemeinsame Regeln in AGENTS.md; CLAUDE.md bindet sie ein -->
## Skill-Zuordnung

Projektart: Python-Werkzeug.

| Wann | Skill |
| --- | --- |
| Nur auf ausdrücklichen Wunsch: fremde App analysieren oder nachbauen | `replica-*` (Start: `replica-recon`) |

Nicht zuständig: `apple-app-release-check`, `swiftui-expert-skill`, `swift-concurrency` (keine Apple-App); `playwright` (keine Weboberfläche).

Skills nur verwenden, wenn die Aufgabe dazu passt; die globale Regel gilt zusätzlich.
In Claude Code heißen die Plugin-Skills `swiftui-expert:swiftui-expert-skill` und `swift-concurrency:swift-concurrency`.
<!-- skill-routing:end -->
