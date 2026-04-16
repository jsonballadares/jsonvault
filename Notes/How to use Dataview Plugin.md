25202507292203
up:: [[Wiki]]
status:: #permanent
tags:: #obsidian, #reference

---
# How to use Dataview Plugin

---
## Overview
Dataview is a powerful community plugin for Obsidian that treats your notes as a database. It lets you query, list, table, and visualize data from your vault using simple SQL-like syntax. Great for dynamic lists (e.g., all notes with a certain tag or status), task management, and dashboards. It works with Markdown, YAML frontmatter, inline fields, and tasks.
### [Dataview Documentation](https://blacksmithgu.github.io/obsidian-dataview/)

--- 
## Basic Usage
- **Query Types**: Use in code blocks like ````dataview` followed by the query type (LIST, TABLE, TASK, CALENDAR).
- **Syntax Basics**:
  - `FROM`: Source (e.g., "Folder", #tag, or "" for whole vault).
  - `WHERE`: Filter (e.g., noteStatus = "fleeting" or contains(tags, "#idea")).
  - `SORT`: Order results (e.g., file.mtime DESC).
  - `LIMIT`: Restrict number of results.
- **Inline Queries**: For dynamic text, use `$= query` (e.g., in a dashboard for counts).
- **Data Sources**: Pull from file.name, file.path, YAML properties (e.g., noteStatus), tasks (completed or not), links, etc.

Queries auto-update as notes change.

## Examples
### 1. List All Fleeting Notes

```dataview
LIST
FROM "Notes"
WHERE status = "#fleeting"
```

---
# References
- [[Dataview Plugin Guide - yt video]]