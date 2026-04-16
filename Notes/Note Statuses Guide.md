up:: [[Wiki]]
status:: #index

---
# Note Statuses Guide

> Every note in `Notes/` must have exactly one status. The status determines which dashboard the note appears on and where it sits in the knowledge lifecycle.

## Status Hierarchy

```
#fleeting → #literature or #permanent or #archived
                                    ↑
                              #index (system notes)
```

## Statuses

### #fleeting
**Purpose:** Raw capture. Unprocessed thoughts, quick ideas, meeting jots.
**Shows up on:** Inbox Dashboard
**What to do:** Review periodically. Develop into #permanent, convert to #literature, or archive.
**Examples:** A quick idea jotted during a meeting, a random thought, a link to check out later.

### #literature
**Purpose:** Notes derived from external sources. Processed summaries of someone else's ideas.
**Shows up on:** Literature Dashboard
**What to do:** Summarize key ideas, connect to your own notes via links.
**Examples:** Book notes, article summaries, course notes, video takeaways.
**Extra fields:** `author::`, `source::`

### #permanent
**Purpose:** Your own developed knowledge and reference material. The "goal state" for most notes.
**Shows up on:** Permanent Dashboard
**What to do:** Keep refining. Link to related notes. This is your second brain.
**Examples:** Polished technical documentation, personal systems, project docs, how-to guides.

### #index
**Purpose:** Navigation hubs that link to other notes. System infrastructure.
**Shows up on:** Not on a specific dashboard — these ARE the dashboards and wiki pages.
**What to do:** Maintain as the vault grows. Add links to new relevant notes.
**Examples:** Home, Inbox, Dashboards, Wiki pages, Maps of Content (MOCs).

### #backlog
**Purpose:** Ticket/story that hasn't been started yet. Used for project task tracking.
**Shows up on:** Project note Dataview queries
**What to do:** Pick up when ready to work on it — move to #active.
**Examples:** "MLHUB - Define Data Model", planned feature work, scoped tasks.

### #active
**Purpose:** Ticket/story currently being worked on.
**Shows up on:** Project note Dataview queries
**What to do:** Complete the work, then move to #done.
**Examples:** A task you're actively implementing this week.

### #done
**Purpose:** Completed ticket/story.
**Shows up on:** Project note Dataview queries
**What to do:** Nothing — kept for history. Archive if no longer useful.
**Examples:** Finished implementation tasks, resolved decisions.

### #archived
**Purpose:** Inactive or outdated notes preserved for reference.
**Shows up on:** Archive Dashboard
**What to do:** Nothing — these are filed away. Search or browse the Archive Dashboard if needed.
**Examples:** Abandoned projects, old interview notes, superseded documentation.

## Lifecycle Flow

See [[Workflows Guide]] for detailed step-by-step procedures on capturing ideas, processing the inbox, and promoting notes through statuses.

---
# References

- [[Vault Structure Guide]]
- [[Tagging Conventions]]
- [[Workflows Guide]]
