# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A personal Obsidian Zettelkasten vault. Not a code repo — there are no build/test/lint commands. Your job is vault management and thinking partnership: reading, searching, creating, and editing Markdown notes; researching topics (in the vault or on the web); and helping draft or develop written content.

## Golden Rules

1. **Read freely, write with transparency.** Search and explore the vault without asking. Before creating or modifying any file, describe what you're about to do — then proceed.
2. **Inline Dataview fields only.** Use `status:: #fleeting` — never YAML frontmatter for status/tags.
3. **All content notes go in `Notes/` (flat).** No subfolders. Daily notes go in `Calendar/Daily/`.
4. **Title Case filenames.** No emoji, no special characters (`\ / : * ? " < > |`), no timestamp prefixes, under 200 chars.
5. **`status::` required on every note.** `tags::` required on content notes.
6. **Use existing tags.** Don't invent new tags without proposing them to the user first.
7. **Use `[[wiki-links]]`** to connect notes. Prefer linking to existing notes.
8. **Preserve note structure.** Keep heading hierarchy and the `# References` section at the bottom.
9. **Research in collapsible callouts.** See the Research section below for full guidance.
10. **Don't write for the user.** When creating notes, describe what occurred factually. Don't add the user's voice, opinions, or reflective commentary — let them add that themselves.

## Vault Architecture

### Folder Layout

| Folder | Purpose |
|---|---|
| `Notes/` | All content notes (flat, no subfolders) |
| `Calendar/Daily/` | Daily journal notes (`YYYY-MM-DD.md`) |
| `Templates/` | 4 templates: Core Idea, Literature Note, Project Note, Daily Note |
| `Images/` | Attachments (auto-managed by Obsidian) |
| `AI OS/Codebase/` | Code projects used by skills |
| `AI OS/Knowledge Base/` | Agent-authored KB (Sources/ and Entities/) — see [[Vault Schema Reference]] |
| `Home.md` | Entry point with Dataview-powered dashboards |

### How Organization Works

There are no topic folders. Notes are organized entirely through **metadata** and **links**:

- **`status::`** — lifecycle stage: `#fleeting` → `#literature` or `#permanent` → `#archived` (plus `#index` for system notes, and `#backlog` → `#active` → `#done` for project tickets)
- **`tags::`** — topic classification (e.g., `#data-engineering, #project`). Comma-separated hashtags.
- **`[[wiki-links]]`** — connections between notes
- **Dashboards** — `Home.md` links to Inbox, Literature, Permanent, Archive, and Calendar dashboards, each powered by Dataview queries

### Note Anatomy

Content notes follow this structure:
```
status:: #fleeting
tags:: #data-engineering, #tutorial

---
# Note Title

Body content here...

---
# References

- [[Related Note]]
```

Index/wiki notes add `up:: [[Parent]]` as the first line. Literature notes add `author::` and `source::` fields.

## AI OS Workflow

The vault's AI OS layer follows the six-stage pattern from [Andrej Karpathy's LLM Knowledge Bases gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Each stage maps onto a folder; stages are optional and can be adopted incrementally.

| Stage | Where It Lives | Status |
|---|---|---|
| **Data ingest** — external sources compiled into structured notes | `AI OS/Knowledge Base/Sources/` | Empty scaffolding |
| **IDE** — Obsidian as the frontend for raw, compiled, and derived content | Vault root, viewed in Obsidian | Active |
| **Q&A** — agent answers questions by reading across the vault and KB | Invoked via Claude Code or other agent | Active |
| **Output** — answers rendered as new notes, slides, or images and filed back | `Notes/` or `AI OS/Knowledge Base/` | Active (manual) |
| **Linting** — agent-run health checks: inconsistencies, missing connections, stale notes | `AI OS/Skills/` (e.g., a mining skill) | Empty scaffolding |
| **Extra tools** — CLIs that extend what the agent can do against the vault | `AI OS/Codebase/` | Empty scaffolding |

Human-authored notes (in `Notes/`) and agent-authored KB notes (in `AI OS/Knowledge Base/`) coexist — see [[Vault Schema Reference]] for authorship rules.

## Vault Reference

Read these wiki notes when you need specifics on conventions:

| Topic | File |
|---|---|
| Vault schema (source of truth) | `Notes/Vault Schema Reference.md` |
| Folder layout | `Notes/Vault Structure Guide.md` |
| Status system (5 statuses) | `Notes/Note Statuses Guide.md` |
| Tag vocabulary & rules | `Notes/Tagging Conventions.md` |
| Filename rules | `Notes/Naming Conventions.md` |
| Templates (4 types) | `Notes/Templates Guide.md` |
| Human workflows | `Notes/Workflows Guide.md` |
| Dataview query patterns | `Notes/Dataview Queries Reference.md` |

## Common Operations

Search for notes by status:
```
grep -r 'status:: #fleeting' Notes/
```

Search for notes by tag:
```
grep -r '#data-engineering' Notes/
```

Find notes linking to a specific note:
```
grep -rl '[[Some Note Title]]' Notes/
```

List all unique tags used in the vault:
```
grep -roh '#[a-z][a-z0-9-]*' Notes/ | sort -u
```

## Response Style

- Be concise. Don't explain vault conventions back to the user — they know their system.
- Use tables or bullet lists for scannability when presenting recommendations.
- If unsure about a tag, status, or approach — ask rather than guess.

## Context Gathering

Proactively build context whenever working in the vault. Don't operate on notes in isolation — explore their neighborhood to understand how they fit into the broader web of ideas.

**How it works:**
1. When you read any note, extract its `[[wiki-links]]` and consider reading the most relevant linked notes.
2. Search for inbound links (`grep -rl '[[Note Title]]' Notes/`) to see what references it.
3. Use judgment about depth — a quick question needs less exploration than an enhance workflow.
4. Cap at ~8 linked notes per gathering pass to avoid reading the whole vault. If more exist, prioritize by relevance and mention what was skipped.

**Re-reading notes:**
- Notes already read in the session can be cached for background context.
- **Re-read a note before acting on it** (editing, making recommendations, or when it's central to the current discussion) — the user may be updating notes in Obsidian in real time, so the cached version could be stale.
