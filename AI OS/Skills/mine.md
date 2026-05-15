---
description: Mine the vault — extract structured data, analyze notes for patterns, and surface actionable insights.
---

You are running the `/mine` skill. Mining is a vault-level analysis operation that produces one Knowledge Base artifact per query, anchored to source notes via wiki-links.

The skill is glue between three Python helpers in `AI OS/Codebase/obsidian-mine/`:

1. `cli.py explore "<direction>"` — runs the Explorer subagent. Persists `recipe.json` describing the work to do. Cheap (~$1–2).
2. `cli.py mine <run_dir>` — runs the Miner subagents in parallel and the Writer subagent in sequence. Persists the artifact and Mining Summary in the KB tree. Bigger spend (~$2–3 in typical runs); ~10–15 min wall-clock.

The user reviews the Recipe between those two calls. Nothing past the review runs without confirmation.

All Python invocations use the shared venv:

```
cd "AI OS/Codebase/obsidian-mine" && venv/bin/python cli.py <subcommand> ...
```

## Step 1 — Validate the direction

The user invokes `/mine <direction>`. The direction is free text — what they want mined. Examples:

- `/mine HomeLab vs Data Engineering: contrast the two approaches`
- `/mine recurring tensions across my project notes`
- `/mine inventory of everything tagged #self`

If `$ARGUMENTS` is empty or whitespace-only, reply with exactly one line and stop:

> Give me a direction — e.g. `/mine HomeLab vs Data Engineering: contrast the two approaches`

## Step 2 — Run Explorer

Invoke the explore subcommand with the user's direction passed verbatim:

```
cd "AI OS/Codebase/obsidian-mine" && venv/bin/python cli.py explore "<DIRECTION>"
```

stdout is line-oriented `KEY=value`. Capture:

- `RUN_DIR=<path>` — keep this for Step 4. The run folder under `obsidian-mine/runs/<stamp>/` is where every subsequent stage reads/writes.
- `KIND=recipe` or `KIND=denial`

If stderr emits `ERROR explore: <msg>` and exit code is non-zero, surface the error and stop:

> Explorer failed: `<msg>`. Run folder: `<RUN_DIR>`.

The user can re-run `/mine` with the same or different direction.

### If KIND=denial

Read `<RUN_DIR>/recipe.json` and pull the `reason` field. Render exactly:

> **Explorer declined.**
>
> `<reason verbatim>`

Stop. No further steps. The recipe.json stays on disk for inspection.

### If KIND=recipe

Continue to Step 3.

## Step 3 — Recipe review

Read `<RUN_DIR>/recipe.json`. The shape is:

```json
{
  "kind": "recipe",
  "artifact_name": "...",
  "notes_needed": { "<bundle_label>": { "paths": [...], "description": "...", "expected_output": "..." }, ... },
  "miner_objective": "...",
  "output_schema": "...",
  "artifact_description": "..."
}
```

Render the **compact Recipe** to the user (Q3 — hide path lists, miner_objective, output_schema by default):

```
**Recipe**

- **Artifact:** `<artifact_name>`
- **Bundles:** N (P paths total)

| Bundle | Paths | Description |
|---|---|---|
| `<label>` | <count> | <description> |
| ... | ... | ... |

**Artifact description:**

<artifact_description prose, verbatim — do not summarize>

**Run folder:** `<RUN_DIR>`
```

Then prompt:

> Approve this Recipe? Reply `yes` to dispatch the Miners, `no` to abort, or ask to see paths / miner_objective / output_schema for any bundle.

Wait for the user. Do not proceed without explicit approval.

### Drill-in requests

If the user asks for hidden detail before approving (e.g. "show paths for `homelab-philosophy`", "what's the miner_objective?", "show output_schema"), read `recipe.json` again and render only what they asked for. Then re-ask whether to approve.

### On rejection

If the user says no / abort / similar, render:

> Aborted. Run folder preserved at `<RUN_DIR>`. No Miner cost incurred.

Stop.

### On approval

Continue to Step 4.

## Step 4 — Mine + Assemble

Invoke the mine subcommand with the run_dir:

```
cd "AI OS/Codebase/obsidian-mine" && venv/bin/python cli.py mine "<RUN_DIR>"
```

This call is long-running (10–15 minutes typical). It runs Miners in parallel then the Writer, writes the artifact and Mining Summary, and prints a structured outcome envelope to stdout.

Parse stdout. Expected lines:

- `ARTIFACT_NAME=<name>`
- `ARTIFACT_PATH=<filesystem path>`
- `SUMMARY_PATH=<filesystem path>`
- `TOPLINE=<duration · tokens · tool uses · cost>`
- `SUCCEEDED=<comma-separated bundle labels>` (may be empty)
- `SKIPPED=<comma-separated bundle labels>` (may be empty)
- `ERROR <label>: <message>` — zero or more lines, one per skipped bundle

If stderr emits `ERROR mine: <msg>` or `ERROR assemble: <msg>` and exit code is non-zero, surface the error and stop:

> Run failed during `<mine|assemble>` stage: `<msg>`. Run folder: `<RUN_DIR>`. Partial state preserved.

## Step 5 — End-of-run message

Render compact (Q5 — paths + topline + bundle outcome line + filesystem paths):

```
**Mine complete.**

<TOPLINE>

Bundles: N OK[, M skipped: <label> (<one-line reason>); ...]

- Artifact: <ARTIFACT_PATH>
- Summary: <SUMMARY_PATH>
```

If any `ERROR <label>: ...` lines appeared in stdout, append:

```
Errors:
- `<label>`: <message>
```

The artifact and Mining Summary are now reviewable in Obsidian. The user opens them to read.

## Rules

- **Never run `mine` without Recipe approval.** Step 3's wait is non-negotiable — Recipe quality varies and Miner+Writer cost is real (~$2–3/run).
- **Filesystem paths in the chat, not wiki-links.** Render `Sources/Vault-Mining/<date> - <name>/<name>.md` rather than `[[<name>]]` for the artifact and summary pointers.
- **Pass the direction to `cli.py explore` verbatim.** Do not paraphrase, expand, or strip quotes from the user's text — the Explorer prompt is tuned for natural-language directions.
- **The run folder is the source of truth between stages.** The skill never re-passes Recipe contents between `cli.py explore` and `cli.py mine` — both stages read from the run folder on disk.
- **Drill-ins do not consume LLM cost.** "Show paths for X" reads recipe.json — no subagent runs. Free.
- **Partial failures continue to assembly.** Step 4 only aborts if `run_recipe` or `run_assembly` itself raises. If Miners skip individual bundles, the Writer composes from what landed and the skipped bundles surface in Step 5's outcome line.
- **One run per `/mine` invocation.** No multi-direction batching. Re-invoke for each direction.

$ARGUMENTS
