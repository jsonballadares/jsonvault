---
description: Query a connected PostgreSQL database read-only. First-run init learns the schema; subsequent runs use cached schema notes to write SQL.
---

You are running the `/query-db` skill. This is a read-only Postgres assistant. You answer the user's question by inspecting the schema (once), then writing SQL against it.

The script lives at `AI OS/Codebase/Postgres Query/query.py` and reads connection details from a `.env` file in the same folder. See `.env.example` there for the variables.

All invocations use the project's venv:

```
source "AI OS/Codebase/Postgres Query/venv/bin/activate" && python "AI OS/Codebase/Postgres Query/query.py" <flag> ...
```

Three flags: `--schema` (print every table + column), `--sql "..."` (run a SELECT), `--csv` (with `--sql`, output CSV instead of an aligned table).

## Step 0 — First-run init

Before answering any question, check whether `AI OS/Codebase/Postgres Query/schema_notes.md` exists.

**If it does not exist**, the database has never been introspected. Run the init flow:

1. Run `--schema`. Capture the full output.
2. Render the table list to the user (table name + column count per table is enough — don't dump every column).
3. Ask the user to walk you through the database in plain language: what each table represents, the natural-key joins between them, anything counterintuitive (snapshot tables, JSON columns, conventions like `dim_` / `fact_` prefixes, soft-deletes, units), and which question patterns they care about. Capture verbatim what they say.
4. Write `AI OS/Codebase/Postgres Query/schema_notes.md` with this shape:

   ```markdown
   # Schema Notes

   _Generated <YYYY-MM-DD> from `query.py --schema`. Edit freely._

   ## What this database is
   <one-paragraph from the user's explanation>

   ## Tables
   <grouped by domain, with the user's framing — not a raw column dump. Example:
   ### Music
   - `dim_tracks` — one row per track. Joins to `fact_music_library` via `track_id`.
   - ...
   >

   ## Join keys
   <the join patterns the user described>

   ## Gotchas
   <anything counterintuitive the user flagged — NULLability, snapshot semantics, etc.>

   ## Example queries
   <2-3 templates the user said they'd actually want>
   ```

5. Show the user the file and ask "anything to add or correct before I save?" Apply edits, then continue to Step 1 with the question they originally asked (if any).

**If it exists**, skip init. Read it for orientation and continue to Step 1.

The schema_notes.md file is gitignored — it's machine-/database-specific. The user can re-init anytime by deleting it.

## Step 1 — Write and run the query

1. Read `schema_notes.md` for the relevant tables and join keys.
2. Construct a SQL query that answers the user's question.
3. Run it:

   ```
   source "AI OS/Codebase/Postgres Query/venv/bin/activate" && python "AI OS/Codebase/Postgres Query/query.py" --sql "SELECT ..."
   ```

4. For large result sets, add `--csv` or use `LIMIT`.

If the query fails or returns nothing useful, refine and try again. If a needed table or column isn't documented in `schema_notes.md`, run `--schema` to verify and update `schema_notes.md` with the gap-filling detail before continuing.

## Step 2 — Present results

Render results in a clean, scannable shape (table or bullets). Don't dump raw CSV unless the user asked.

## Guidelines

- **Read-only.** The script blocks anything that doesn't start with `SELECT`. Don't try to work around it.
- **Use `ILIKE`** for case-insensitive text searches.
- **Qualify table names** with their schema if `DB_SCHEMA` is set in `.env` (e.g., `analytics.dim_tracks`).
- **Cache schema knowledge in `schema_notes.md`**, not in your head. The next session won't remember.
- **Update `schema_notes.md`** when you discover something the file doesn't mention — joins, units, NULL semantics, useful patterns. The file is the long-term memory of this skill.

$ARGUMENTS
