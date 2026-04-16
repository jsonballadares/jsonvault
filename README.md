# Vault Template

A starter Obsidian Zettelkasten vault with an AI OS layer — the system scaffolding for a knowledge base that humans and AI agents share. Based on a flat-folder Zettelkasten with metadata-driven organization, Dataview dashboards, and a Claude Code integration that loads vault context on session start.

The full design is documented inside the vault itself. Start with `Home.md` → `Notes/Wiki.md` → `Notes/Vault Schema Reference.md`.

## Prerequisites

- **Obsidian** (desktop)
- **Community plugins:** Dataview, Templater, Periodic Notes, Buttons, Calendar, Obsidian Git, Style Settings (enable via Settings → Community plugins)
- **Claude Code** (optional) — the `.claude/` config loads `AI OS/me.md` on session start so the agent inherits vault conventions

## Getting Started

1. Clone or copy this folder to wherever you want the vault to live.
2. Open it in Obsidian: Settings → "Open folder as vault."
3. Trust plugins when prompted. Enable the community plugins listed above.
4. Open `Home.md` to see the dashboards. Open `Notes/Wiki.md` for the system documentation.
5. Delete the `Sample *` notes in `Notes/` once you've seen how the status/tag/link system works.
6. Start capturing: `Cmd/Ctrl + N` → apply the Core Idea template → write.

## What's in the Box

| Path | Contents |
|---|---|
| `Notes/` | 17 wiki/guide/dashboard notes + 5 sample notes (delete after reviewing) |
| `Calendar/Daily/` | Empty — populated by Periodic Notes as daily notes are created |
| `Templates/` | 4 templates: Core Idea, Literature Note, Project Note, Daily Note |
| `AI OS/me.md` | Canonical agent configuration (golden rules, schema pointers, response style) |
| `AI OS/Skills/`, `AI OS/Codebase/` | Empty — add your own skills and tools here |
| `AI OS/Knowledge Base/` | Empty `Sources/` and `Entities/` scaffolding for agent-authored KB entries |
| `.claude/` | Thin Claude Code config — loads `AI OS/me.md` on session start |
| `.obsidian/` | Plugin settings, CSS snippets, and theme files |

## Customizing

- **Tags:** the default tag vocabulary in `Notes/Tagging Conventions.md` is a reasonable starting set. Adjust to your own topics.
- **me.md:** the canonical config at `AI OS/me.md` is where you teach the agent about your vault. Edit the response style and golden rules to taste.
- **Dashboards:** `Home.md`, `Permanent Dashboard.md`, etc. are driven by Dataview. Adjust the queries as your vault grows.
- **Skills:** `AI OS/Skills/` and `.claude/commands/` are intentionally empty. Add skills as you build them.

## License

Personal template — use freely.
