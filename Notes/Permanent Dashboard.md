---
cssclasses:
  - dashboard
---
up:: [[Home]]
status:: #index

---
# Permanent

> [!permanent] `$= dv.pages('"Notes"').where(p => p.status == "#permanent").length` permanent notes
> Your developed knowledge — polished notes, technical docs, how-to guides, project documentation.

## MOCs

> [!info]+ All MOCs
> Maps of Content — index notes that group related notes by topic. Create new MOCs as your vault grows.
>
> ```dataview
> TABLE length(file.outlinks) AS "Outlinks", file.mday AS "Modified"
> FROM "Notes"
> WHERE contains(file.name, "MOC") AND status = "#index"
> SORT file.name ASC
> ```

## All Permanent Notes

>[!info]
>Use this section to browse permanent notes

```dataview
TABLE tags AS "Tags", length(file.outlinks) AS "Outlinks", length(file.inlinks) AS "Inlinks", file.mday AS "Modified"
FROM "Notes"
WHERE status = "#permanent" and !contains(file.name, "MOC")
SORT length(file.outlinks) + length(file.inlinks) DESC
```

> [!recent]- Recently Modified
> ```dataview
> TABLE tags AS "Tags", file.mday AS "Modified"
> FROM "Notes"
> WHERE status = "#permanent"
> SORT file.mday DESC
> LIMIT 5
> ```
