---
cssclasses:
  - dashboard
---
status:: #index

---

# Home

> [!vault-stats]+ Vault Overview
> **`$= dv.pages('"Notes"').length`** notes | **`$= dv.pages('"Calendar/Daily"').length`** daily entries
>
> | Status | Count |
> |--------|------:|
> | Fleeting | `$= dv.pages('"Notes"').where(p => p.status == "#fleeting").length` |
> | Literature | `$= dv.pages('"Notes"').where(p => p.status == "#literature").length` |
> | Permanent | `$= dv.pages('"Notes"').where(p => p.status == "#permanent").length` |
> | Archived | `$= dv.pages('"Notes"').where(p => p.status == "#archived").length` |

## Dashboards

- **[[Inbox]]**
	- Fleeting notes to review
	- `$= dv.pages('"Notes"').where(p => p.status == "#fleeting").length` notes
- **[[Literature Dashboard|Literature]]**
	- Notes from external sources
	- `$= dv.pages('"Notes"').where(p => p.status == "#literature").length` notes
- **[[Permanent Dashboard|Permanent]]**
	- Developed knowledge
	- `$= dv.pages('"Notes"').where(p => p.status == "#permanent").length` notes
- **[[Archive Dashboard|Archive]]**
	- Inactive notes
	- `$= dv.pages('"Notes"').where(p => p.status == "#archived").length` notes
- **[[Calendar]]**
	- Daily journal
	- `$= dv.pages('"Calendar/Daily"').length` entries

## Pending Tasks

> [!todo]- Open Tasks
> ```dataview
> TASK
> FROM "Calendar/Daily"
> WHERE !completed
> GROUP BY file.link
> LIMIT 25
> ```

## System

- **[[Wiki]]**
	- How this vault works

> [!recent]- Recently Modified
> ```dataview
> TABLE file.mday AS "Modified", status AS "Status"
> FROM "Notes"
> SORT file.mday DESC
> LIMIT 5
> ```
