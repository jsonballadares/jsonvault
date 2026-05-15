# Postgres Query

Read-only Postgres CLI used by the `/query-db` skill. Three flags: `--schema`, `--sql "..."`, `--csv`.

## Setup

From this directory:

```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your Postgres connection. A read-only role is recommended — the script also blocks any non-`SELECT` statement client-side and opens the connection with `readonly=True`, but defense in depth is cheap.

Verify:

```
venv/bin/python query.py --schema
```

## How `/query-db` uses this

The first time `/query-db` runs, the skill walks you through the schema (`--schema` output + a conversation about what's where) and writes its understanding to `schema_notes.md` in this folder. From then on, the skill reads `schema_notes.md` for orientation and writes SQL against it.

`schema_notes.md` is gitignored — it's machine-/database-specific. Delete it to re-init.

## Variables

See `.env.example`. `DB_SCHEMA` defaults to `public` if unset.
