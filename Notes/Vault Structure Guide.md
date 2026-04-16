up:: [[Wiki]]
status:: #index

---
# Vault Structure Guide

> This guide explains how the vault is organized and where everything lives.

## Folder Layout

```
vault/
├── Home.md              # Entry point — links to all dashboards and Wiki
├── Notes/               # All human-authored notes (flat structure)
├── Calendar/
│   ├── Calendar.md      # Calendar dashboard
│   └── Daily/           # Daily journal notes (YYYY-MM-DD format)
├── AI OS/               # System layer — instructions, tools, code, KB
│   ├── Codebase/        # Code projects (subfolders per project)
│   └── Knowledge Base/  # Agent-authored KB (Sources/ and Entities/)
├── Docs/                # External document annotations (PDFs, etc.)
├── Templates/           # Note templates (4 total)
├── Images/              # Attachments and images
├── .claude/             # Interface layer (thin pointers into AI OS/)
└── .obsidian/           # Obsidian config and plugins
```

> For the full schema — including KB subfolder structure, field conventions, entity types, and authorship rules — see [[Vault Schema Reference]].

## Flat Folder Philosophy

All notes live in a single `Notes/` folder. There are no topic subfolders. Organization is handled entirely through **metadata** (status, tags) and **links** between notes.

**Why flat?**
- Avoids the overhead of maintaining folder hierarchies
- Lets you find notes through Dataview queries and dashboards instead of browsing folders
- Aligns with Zettelkasten principles — connections matter more than categories
- New notes always go to one place, no decision fatigue about "which folder"

## How to Find Things

- **Dashboards** — each status has a dedicated dashboard (Inbox, Literature, Permanent, Archive, Calendar) accessible from Home
- **Tags** — use the tag pane or search by tag to filter notes by topic
- **Links** — follow `[[wiki links]]` between related notes
- **Search** — Obsidian's full-text search works across all notes
- **Dataview** — custom queries can slice the vault any way you need

## What Goes Where

| Content | Location |
|---------|----------|
| Any new note | `Notes/` (use Core Idea template) |
| Daily journal | `Calendar/Daily/` (auto-created by Periodic Notes plugin) |
| Book/article notes | `Notes/` (use Literature Note template) |
| Project documentation | `Notes/` (use Project Note template) |
| Images and attachments | `Images/` (auto-handled by Obsidian) |
| PDF annotations | `Docs/` |
| Scripts and code | `AI OS/Codebase/` (subfolders per project) |
| Note templates | `Templates/` |

---
# References

- [[Vault Schema Reference]]
- [[Note Statuses Guide]]
- [[Tagging Conventions]]
- [[Templates Guide]]
