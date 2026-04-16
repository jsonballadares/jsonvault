---
cssclasses:
  - dashboard
---
up:: [[Home]]
status:: #index

---

# Literature

> [!literature] `$= dv.pages('"Notes"').where(p => p.status == "#literature").length` literature notes
> Notes derived from external sources — books, articles, courses, videos. Summaries of other people's ideas.

## Books

> [!book]+ All Books
> ```dataview
> TABLE author AS "Author", status AS "Status", tags AS "Tags"
> FROM "Notes"
> WHERE type = "#book"
> SORT status, file.name
> ```

## All Literature Notes

> [!note]+ All Literature
> ```dataview
> TABLE author AS "Author", source AS "Source", tags AS "Tags", file.cday AS "Created"
> FROM "Notes"
> WHERE status = "#literature"
> SORT file.mday DESC
> ```

> [!recent]- Recently Modified
> ```dataview
> TABLE author AS "Author", source AS "Source", file.mday AS "Modified"
> FROM "Notes"
> WHERE status = "#literature"
> SORT file.mday DESC
> LIMIT 5
> ```
