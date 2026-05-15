# Vault Template

A starter Obsidian Zettelkasten vault with an AI OS layer — the system scaffolding for a knowledge base that humans and AI agents share. Based on a flat-folder Zettelkasten with metadata-driven organization, Dataview dashboards, and a Claude Code integration that loads vault context on session start.

The full design is documented inside the vault itself. Start with `Home.md` → `Notes/Wiki.md` → `Notes/Vault Schema Reference.md`.

## Prerequisites

- **Obsidian** (desktop)
- **Community plugins:** Dataview, Templater, Periodic Notes, Buttons, Calendar, Obsidian Git, Style Settings (enable via Settings → Community plugins)
- **Claude Code** (optional) — the `.claude/` config loads `AI OS/me.md` on session start so the agent inherits vault conventions
- **Python 3.10+** (only if you want to use the bundled skills — `mine` and `query-db`)

## Getting Started

1. Clone or copy this folder to wherever you want the vault to live.
2. Open it in Obsidian: Settings → "Open folder as vault."
3. Trust plugins when prompted. Enable the community plugins listed above.
4. Open `Home.md` to see the dashboards. Open `Notes/Wiki.md` for the system documentation.
5. Delete the `Sample *` notes in `Notes/` once you've seen how the status/tag/link system works.
6. Start capturing: `Cmd/Ctrl + N` → apply the Core Idea template → write.
7. (Optional) Set up the bundled skills — see "Skills" below.

## What's in the Box

| Path | Contents |
|---|---|
| `Notes/` | 17 wiki/guide/dashboard notes + 5 sample notes (delete after reviewing) |
| `Calendar/Daily/` | Empty — populated by Periodic Notes as daily notes are created |
| `Templates/` | 4 templates: Core Idea, Literature Note, Project Note, Daily Note |
| `AI OS/me.md` | Canonical agent configuration (golden rules, schema pointers, response style) |
| `AI OS/Skills/` | 3 starter skills: `mine`, `promote-daily-ideas`, `query-db` |
| `AI OS/Codebase/obsidian-mine/` | Python runtime for the `/mine` skill (pure stdlib + Claude Code CLI) |
| `AI OS/Codebase/Postgres Query/` | Generic env-driven Postgres CLI for the `/query-db` skill |
| `AI OS/Knowledge Base/` | Empty `Sources/`, `Entities/`, `Projects/` scaffolding for agent-authored KB entries |
| `.claude/` | Thin Claude Code config — loads `AI OS/me.md` on session start, auto-allows the bundled scripts |
| `.obsidian/` | Plugin settings, CSS snippets, and theme files |

## Skills

The template ships with three skills under `AI OS/Skills/`. Each is also exposed as a slash command in `.claude/commands/` so you can invoke it as `/mine`, `/promote-daily-ideas`, or `/query-db` inside Claude Code.

| Skill | What it does | Setup |
|---|---|---|
| `promote-daily-ideas` | Scans your recent daily notes, surfaces standalone-idea candidates, and (after you approve) lifts each chosen idea into its own note in `Notes/` — moving text word-for-word and replacing the original with a wiki-link. | None. Pure vault workflow. |
| `mine` | Runs an Explorer subagent to draft a Recipe for a free-text "direction," then — after Recipe approval — runs Miners + a Writer to produce a single Knowledge Base artifact. | Requires `obsidian-mine` venv (see below). |
| `query-db` | Read-only Postgres assistant. First-run init walks you through your database schema and writes `schema_notes.md`; subsequent runs use that as cached schema knowledge to write SQL. | Requires `Postgres Query` venv + `.env` (see below). |

### Setting up `obsidian-mine`

```
cd "AI OS/Codebase/obsidian-mine"
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Also requires the **[Claude Code CLI](https://docs.claude.com/claude-code)** on your `PATH` — the runtime shells out to `claude -p` for every subagent invocation.

### Setting up `Postgres Query`

```
cd "AI OS/Codebase/Postgres Query"
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
# edit .env with your Postgres connection (use a read-only role)
```

The first time you run `/query-db`, the skill walks you through the database schema and persists what it learns to `schema_notes.md` (gitignored — machine-/database-specific).

## AI OS / Codebase convention

`AI OS/Codebase/` is for code projects the agent uses directly. One subfolder per project. Each project has its own `venv/` (gitignored) and its own `.env` (gitignored). Add new projects here and grant them in `.claude/settings.json` via a `Bash(...)` permission entry plus an optional PreToolUse auto-allow hook so they don't prompt every invocation.

## Customizing

- **Tags:** the default tag vocabulary in `Notes/Tagging Conventions.md` is a reasonable starting set. Adjust to your own topics.
- **me.md:** the canonical config at `AI OS/me.md` is where you teach the agent about your vault. Edit the response style, golden rules, and the `Local Repositories` section to taste.
- **Dashboards:** `Home.md`, `Permanent Dashboard.md`, etc. are driven by Dataview. Adjust the queries as your vault grows.
- **Skills:** the three bundled skills are starting points. Edit them, swap them out, or add your own under `AI OS/Skills/` with matching pointer stubs in `.claude/commands/`.

## License

Personal template — use freely.
