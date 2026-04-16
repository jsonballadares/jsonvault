---
cssclasses:
  - dashboard
---
up:: [[Home]]
status:: #index 

---
# Inbox

> [!inbox] `$= dv.pages('"Notes"').where(p => p.status == "#fleeting").length` fleeting notes
> Unprocessed thoughts waiting to be reviewed. Process these into permanent or literature notes, or archive them.

## All Fleeting Notes

```dataview
TABLE tags AS "Tags", file.ctime AS "Created", file.mtime AS "Modified"
FROM "Notes"
WHERE status = "#fleeting"
SORT file.mtime DESC
```

> [!recent]- Recently Modified
> ```dataview
> TABLE tags AS "Tags", file.mtime AS "Modified"
> FROM "Notes"
> WHERE status = "#fleeting"
> SORT file.mtime DESC
> LIMIT 5
> ```
