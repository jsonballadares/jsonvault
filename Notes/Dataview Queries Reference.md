up:: [[Wiki]]
status:: #index

---
# Dataview Queries Reference

> Common Dataview queries used in this vault and how to write your own.

## Basics

Dataview queries are embedded in notes using code blocks with the `dataview` language tag. They dynamically display data from your vault.

## Common Queries

### List all notes with a specific status
```
TABLE tags, file.cday AS "Created", file.mday AS "Modified"
FROM "Notes"
WHERE status = "#fleeting"
SORT file.cday DESC
```

### Count notes by status
```
TABLE length(rows) AS "Count"
FROM "Notes"
WHERE status
GROUP BY status
SORT length(rows) DESC
```

### Find notes with a specific tag
```
TABLE status, file.cday AS "Created"
FROM "Notes"
WHERE contains(tags, "#data-engineering")
SORT file.mday DESC
```

### Recently modified notes
```
TABLE file.mday AS "Modified"
FROM "Notes"
SORT file.mday DESC
LIMIT 10
```

### Notes created this week
```
TABLE status, tags
FROM "Notes"
WHERE file.cday >= date(today) - dur(7 days)
SORT file.cday DESC
```

### Literature notes by author
```
TABLE author, source, tags
FROM "Notes"
WHERE status = "#literature"
SORT author ASC
```

### Most linked notes (knowledge hubs)
```
TABLE length(file.inlinks) AS "Incoming Links", length(file.outlinks) AS "Outgoing Links"
FROM "Notes"
WHERE length(file.inlinks) > 3
SORT length(file.inlinks) DESC
```

### Notes without tags (needs review)
```
TABLE status, file.cday
FROM "Notes"
WHERE !tags OR tags = ""
SORT file.cday DESC
```

## Understanding Inlinks vs Outlinks

In Dataview, `file.inlinks` and `file.outlinks` are always evaluated **from the perspective of the note being queried**, not from the note you're asking about.

### Example

Say **Topic MOC** contains `[[Note A]]` and `[[Note B]]` inside it, and separately **Note C** contains `[[Topic MOC]]`.

| From Note A's perspective | Field | Contains | Why |
|---|---|---|---|
| | `file.outlinks` | whatever Note A links to | links written inside Note A |
| | `file.inlinks` | Topic MOC | Topic MOC has `[[Note A]]` in it |

| From Note C's perspective | Field | Contains | Why |
|---|---|---|---|
| | `file.outlinks` | Topic MOC | Note C has `[[Topic MOC]]` in it |
| | `file.inlinks` | whatever links to Note C | other notes with `[[Note C]]` |

### Querying by link direction

| You want… | WHERE clause | Logic |
|---|---|---|
| Notes that Topic MOC links **to** | `contains(file.inlinks, [[Topic MOC]])` | "Is Topic MOC in **my** inlinks?" |
| Notes that link **to** Topic MOC | `contains(file.outlinks, [[Topic MOC]])` | "Is Topic MOC in **my** outlinks?" |

> It feels backwards because you think from Topic MOC's point of view, but the query evaluates from each note's own perspective.

## Tips

- Use `FROM "Notes"` to scope queries to the Notes folder (not Calendar, Templates, etc.)
- Use `WHERE status = "#fleeting"` with quotes around the hashtag value
- `file.cday` = creation date, `file.mday` = modification date, `file.mtime` = modification time
- `SORT ... DESC` for newest first, `ASC` for oldest first
- `LIMIT 10` to cap results
- `GROUP BY` to aggregate data
- `contains(tags, "#sometag")` to check if a tag is present in a multi-tag field

---
# References

- [[How to use Dataview Plugin]]
