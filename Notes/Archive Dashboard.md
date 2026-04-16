---
cssclasses:
  - dashboard
---
up:: [[Home]]
status:: #index

---

# Archive

> [!archive] `$= dv.pages('"Notes"').where(p => p.status == "#archived").length` archived notes
> Inactive or outdated notes preserved for reference. Browse here if you need something from the past.

## All Archived Notes

```dataview
TABLE tags AS "Tags", file.cday AS "Created", file.mday AS "Modified"
FROM "Notes"
WHERE status = "#archived"
SORT file.mday DESC
```
