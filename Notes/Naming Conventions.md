up:: [[Wiki]]
status:: #index

---
# Naming Conventions

> How to name notes for consistency and discoverability.

## Rules

1. **Use Title Case** — capitalize the first letter of each major word
   - Good: `Apache Spark Performance Tuning`
   - Bad: `apache spark performance tuning`

2. **Be descriptive** — the name should tell you what the note is about at a glance
   - Good: `Setting up Docker on UGREEN NAS`
   - Bad: `Docker Setup`
   - Bad: `20260203 backup stuff`

3. **No timestamp prefixes** — don't start note names with dates or IDs
   - Good: `Backup Service Instructions`
   - Bad: `20260203 backup service instructions`
   - Exception: The auto-generated ID inside the note (first line) is fine, just don't use it as the filename

4. **No abbreviations unless widely known** — spell things out
   - Good: `Resilient Distributed Datasets`
   - OK: `ADHD` (widely known acronym)
   - Bad: `RDD` (not obvious to everyone)

5. **Fix typos** — if you notice a misspelled filename, rename it
   - Obsidian updates links automatically when you rename within the app

## Special Naming Patterns

| Note Type | Pattern | Example |
|-----------|---------|---------|
| Regular notes | Descriptive Title Case | `Apache Spark Performance Tuning` |
| Daily notes | YYYY-MM-DD (auto-generated) | `2025-02-10` |
| MOC/Index notes | Topic + "MOC" suffix | `HomeLab MOC` |
| Dashboard notes | Status + "Dashboard" | `Literature Dashboard` |
| Wiki pages | Descriptive guide name | `Note Statuses Guide` |

---
# References

- [[Vault Structure Guide]]
- [[Tagging Conventions]]
