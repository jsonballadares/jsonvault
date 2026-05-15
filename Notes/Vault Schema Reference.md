up:: [[Wiki]]
status:: #index
tags:: #ai, #obsidian

---
# Vault Schema Reference

Source of truth for the vault's data structure. Every OS component — mining, KB ingestion, linting, retrieval — points here.

>[!warning] This is still in review and under development

## Folder Structure

```
vault/
├── Notes/  # Human-authored content (flat, no subfolders)
├── Calendar/
│   └── Daily/ # Daily journals (YYYY-MM-DD.md)
├── Templates/  # Note templates (4)
├── Images/     # Attachments (auto-managed)
├── Docs/       # PDF annotations
├── AI OS/      # System layer
│   ├── Codebase/  # Code projects (subfolders per project)
│   └── Knowledge Base/    # Agent-authored knowledge base
│       ├── Sources/
│       │   ├── Books/
│       │   ├── Chapters/
│       │   ├── Articles/
│       │   ├── Vault-Mining/
│       │   └── ...
│       ├── Entities/
│       │   ├── Concepts/
│       │   ├── People/
│       │   ├── Quotes/
│		│	└── ...
│       ├── Projects/
│       ├── index.md
│       └── log.md
├── Home.md.   # Entry point
└── .claude/   # Interface layer (thin pointers into AI OS/)
```

**Notes/** — all human-authored content notes. Flat, no subfolders. Organization through metadata and links.

**AI OS/** — the System layer. Instructions, tools, code, and the KB. Everything an agent needs to operate on the vault.

**AI OS/Knowledge Base/Sources/** — ingested material and subdivisions. Each source type gets its own subfolder. `Vault-Mining/` holds mining run outputs — what was analyzed, what patterns were found.

**AI OS/Knowledge Base/Entities/** — distilled knowledge. Includes both cross-source extractions (mined from formal source material) and concepts born from first-party reasoning (planning conversations, agent-human collaboration, working sessions). Each entity type gets its own subfolder. Entity notes link back to whatever seeded them via (sources) when applicable — either KB source notes or vault notes. Flat within each subfolder; `index.md` catalogs every KB page for agent navigation.

**AI OS/Knowledge Base/Projects/** — agent-authored project workspaces. One subfolder per project, each holding design docs, PRDs, proposals, or other project-scoped artifacts produced through agent sessions. Distinguished from main-vault project notes (`#project` tagged notes in `Notes/`) by scope: these are self-contained project workspaces, not nodes in the vault's idea graph.

## Statuses

**Content track:** `#fleeting` → `#literature` or `#permanent` or `#archived`
**Project track:** `#backlog` → `#active` → `#done`
**System:** `#index`
**KB notes** don't use status — they exist or they don't. No lifecycle track.

## Note Types

Type is inferred from status, tags, fields, and folder — no explicit (type) field in the main vault. KB notes use (type) for entity/source classification.

| Type            | Status                       | Key Fields                                         | Template        |
| --------------- | ---------------------------- | -------------------------------------------------- | --------------- |
| Content note    | `#fleeting` → `#permanent`   | (status), (tags)                               | Core Idea       |
| Literature note | `#literature`                | (status), (tags), (author), (source)           | Literature Note |
| Project note    | `#permanent`                 | (status), (tags) (includes `#project`)         | Project Note    |
| Ticket note     | `#backlog`/`#active`/`#done` | (status), (tags), (project)                    | —               |
| Index/wiki note | `#index`                     | (status), (up)                                 | —               |
| Daily note      | —                            | (up), (dates), (mood), (energy), (focus)       | Daily Note      |

**Literature notes vs. KB source notes:** Literature notes are human-authored — your reading, your emphasis, your connections. KB source notes are agent-authored structured extractions. Both can exist for the same source material.

## Inline Dataview Fields

### Main Vault

**Universal (all notes in Notes/):**
- (status) — lifecycle stage (required)
- (tags) — topic + type classification, comma-separated hashtags (required)

**Selective:**
- (up) — parent link (index/wiki and daily notes)
- (project) — links ticket to parent project note
- (author) — source author (literature notes)
- (source) — source URL/reference (literature notes)

**Daily-only:**
- (dates), (mood), (energy), (focus)

### KB

**All KB notes (required):**
- (origin) `agent` — authorship safety net (folder is the primary distinction)
- (type) — classification (e.g., `#book`, `#chapter`, `#concept`, `#person`, `#quote`)
- (tags) — semantic tags

**Source notes add:** (author), (year), (source), (chapters), (book), (chapter) as applicable.

**Entity notes add:** (sources) (optional — links to whatever seeded the concept: KB source notes, vault notes, or omitted entirely when the concept was distilled from direct reasoning with no cited material), (role) (on people).

## Entity Types

| Type | Folder | Purpose |
|---|---|---|
| Concept | `Entities/Concepts/` | Cross-source ideas, frameworks, mental models |
| Person | `Entities/People/` | Authors, historical figures, thinkers |
| Quote | `Entities/Quotes/` | Notable passages with source attribution |

Deferred candidates: Claims, Events, Places, Questions.

**Scaling:** New source type → subfolder under `Sources/`, define (type) value. New entity type → subfolder under `Entities/`, define (type) value. Ingestion pipelines are per-source-type; all output to the same `Entities/` structure.

## Tags

**Domain:** `#data-engineering`, `#homelab`, `#programming`, `#ai`, `#productivity`, `#health`, `#fitness`, `#career`, `#books`, `#music`, `#linux`, `#networking`, `#obsidian`

**Type:** `#project`, `#tutorial`, `#reference`, `#moc`, `#brainstorm`, `#to-explore`

Rules: lowercase with hyphens, comma-separated in (tags). Propose new tags before creating them.

## Naming Conventions

| Type | Pattern | Example |
|---|---|---|
| Content note | Descriptive Title Case | `Apache Spark Performance Tuning` |
| Daily note | `YYYY-MM-DD` | `2026-04-09` |
| MOC/Index | Topic + "MOC" | `HomeLab MOC` |
| Dashboard | Status + "Dashboard" | `Literature Dashboard` |
| Wiki | Descriptive guide name | `Note Statuses Guide` |
| Ticket | `PREFIX - Description` | `AIOS - Audit Vault Data Structure` |

No emoji, no special characters, no timestamp prefixes, under 200 chars.

## Cross-Space Rules

- **Linking:** Notes and KB notes can link to each other freely via `[[wiki-links]]`.
- **Authorship:** Absence of (origin) = human-authored. (origin) `agent` = agent-authored.
- **Linting (downstream):** A linting tool will handle broken cross-boundary links and entity resolution (deduplication, alias matching).

---
# References

- [[Vault Structure Guide]]
- [[Note Statuses Guide]]
- [[Tagging Conventions]]
- [[Naming Conventions]]
- [[Templates Guide]]
