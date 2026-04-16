---
cssclasses:
  - dashboard
---
up:: [[Home]]
status:: #index

---

# Calendar

> [!calendar-stats] `$= dv.pages('"Calendar/Daily"').length` daily entries
> **With content:** `$= dv.pages('"Calendar/Daily"').where(p => p.file.size > 324).length` entries

```button
name Open Today's Daily Note
type command
action Periodic Notes: Open daily note
```

## Recent Entries

```dataview
TABLE dateformat(dates, "DDDD") AS "Date", mood AS "Mood", energy AS "Energy", focus AS "Focus"
FROM "Calendar/Daily"
WHERE file.name != "Calendar"
SORT dates DESC
LIMIT 30
```
