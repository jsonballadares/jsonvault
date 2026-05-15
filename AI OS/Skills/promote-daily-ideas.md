---
description: Scan recent daily notes for standalone-idea candidates, curate them, and promote chosen ones into Notes/ — moving text word-for-word and replacing the original with a wiki-link.
---

You are running the `/promote-daily-ideas` skill. This is a vault curation workflow that surfaces ideas buried in daily notes and lifts them into their own notes without rewriting the user's voice.

The user invokes `/promote-daily-ideas [scope]`. `$ARGUMENTS` is free text describing the date range. Default if empty: current week (Monday → today).

Accepted scope forms:
- `today` — single day
- `week` — current week (default)
- `month` — current month
- `YYYY-MM-DD` — single day
- `YYYY-MM-DD..YYYY-MM-DD` — range

## Step 1 — Resolve scope and read daily notes

Compute the date range from `$ARGUMENTS`. List `Calendar/Daily/` for files matching the range. Read each file end-to-end. Cap at 14 days per invocation — if the range exceeds that, ask the user to narrow it.

## Step 2 — Classify every line

For each bullet/line in the body, classify into exactly one bucket:

| Class | Treatment |
|---|---|
| Standalone idea (concept, project seed, observation, hypothesis) | Candidate |
| Already a wiki-link to an existing note | Skip — already promoted |
| Task/reminder (deadline, follow-up, errand) | Skip |
| Status update on an ongoing project | Skip |
| Pure journaling (mood, energy, social, body, anxiety, day recap) | Skip |

Before classifying as a candidate, run `ls Notes/ | grep -iE '<keywords>'` to detect overlap with existing notes.

## Step 3 — Curate and present

Render the curated list in this exact shape:

```
**Daily-note idea harvest — `<scope>`**

## Strong candidates

| Idea | Source | Why standalone |
|---|---|---|
| **<short title>** — <one-line framing> | YYYY-MM-DD, line N | <reason> |

## Worth promoting

| Idea | Source | Notes |
|---|---|---|
| ... | ... | ... |

## Borderline — recommend appending instead

| Idea | Source | Append to |
|---|---|---|
| ... | ... | `[[Existing Note]]` |

## Skipping

- <reason — one line per category, not per item>
```

**Before listing append targets**, check the target's `status::`. If it is `#archived` or tagged `#legacy-idea`, flag this in the Notes column (e.g., `(archived — revive or new note?)`) so the user can decide whether to revive (bump to `#permanent`, retag) or promote as a new note. Never silently propose appending to archived notes.

Then prompt:

> Which should I promote? Reply with names, or `all strong`, or ask for revisions.

Wait for explicit selection. Do not move anything without it.

## Step 4 — Move each chosen idea

For every named idea, do this in order:

**a. Determine extraction boundary and bridge mid-thought openers.** Read the full bullet plus any sub-bullets. If the candidate's opening relies on context from the surrounding brain dump (`this`, `that`, `it`, openers like "a few things are in the way"), write a one-sentence bridge that names the source daily note — e.g. "In a brain dump on [[YYYY-MM-DD]] I was thinking about X, ..." — and keep the rest word-for-word. **Always show the proposed bridge wording to the user before writing the file.** Confirm boundary with the user only if ambiguous.

**b. Pick title.** Title Case, no special characters (`\ / : * ? " < > |`), under 200 chars. Reuse the user's own phrasing where possible.

**c. Pick tags from existing vocabulary.** Run:

```
grep -roh '#[a-z][a-z0-9-]*' Notes/ | sort -u
```

Pick 2–4 existing tags. If none fit, propose a new tag to the user before writing — do not invent silently.

**d. Check for overlap one more time.** `ls Notes/` for the proposed filename. If a similar note exists, ask whether to extend that note or create new.

**e. Write the new note.** Structure:

```
status:: #fleeting
tags:: <comma-separated existing tags>

---
# <Title>

<body — word-for-word from daily note, no rewriting>

---
# References

- [[YYYY-MM-DD]]
```

**f. Replace the original lines** in the daily note with `- [[<Title>]]`. Use Edit, not Write. When a parent bullet and its sub-bullets were merged into one note (per the merge-close-ideas rule), the single wiki-link replaces the parent *and* all merged sub-bullets — no orphan sub-bullets remain.

**g. Append integration (when not creating a new note).** When integrating into an existing note instead of creating one:

- Insert a `## Revisited YYYY-MM-DD` heading after the original body, before the `---` separator above `# References`.
- Multiple revisit sections sort chronologically (oldest first).
- Apply the bridging rule from step 4a if the appended text relies on surrounding brain-dump context.
- Add `[[YYYY-MM-DD]]` to the `# References` list.
- **Daily-note replacement uses a context breadcrumb, not a bare link.** Replace the original daily-note line with `- Added to [[Target Note]]: <brief context about what was added>.` — never just `- [[Target Note]]`. A bare wiki-link in an append case loses the breadcrumb of *why* this idea showed up that day; the context line keeps the daily note readable as a journal. (New-note promotions in step 4f still use `- [[New Note Title]]` since the title itself carries the context.)
- If the user asks to revive an archived target, also update `status::` and `tags::` per their direction in the same edit pass.

## Step 5 — Confirm

Render:

```
**Promoted N ideas:**
- [[<Title>]] ← YYYY-MM-DD
- ...
```

Offer a second pass only if (a) the first pass left obviously high-signal candidates unselected, or (b) the user asks. Default closing is just the promoted list — not a second-pass prompt. Second passes on already-curated daily notes usually surface journaling, not ideas.

If the user requests a second pass, return to Step 2 over the same scope, excluding lines now replaced with wiki-links.

## Rules

- **Word-for-word.** Never paraphrase, summarize, or "improve" the user's text. The note body is exactly what they wrote.
- **Don't write for the user.** No reflection, no opinion, no framing prose. Just title + their words + structure.
- **Existing tags only.** Grep before tagging. Propose new tags rather than invent them.
- **Bridge mid-thought openers.** If the candidate starts with a pronoun (`this`, `that`, `it`) or an unresolved reference, write a one-sentence bridge naming the source daily note (e.g. "In a brain dump on [[YYYY-MM-DD]] I was thinking about X, ...") and keep the rest word-for-word. Show the bridge wording before writing.
- **Merge close ideas into one note.** Adjacent bullets that are sub-thoughts of one idea become one note, not two.
- **Always backlink.** Every promoted note's `# References` includes `[[<Daily Note>]]`.
- **Never touch scratchpad without asking.** If a scratchpad item becomes redundant after promotion, flag it as cleanup — do not auto-delete.
- **No moves without explicit selection.** Step 3's wait is non-negotiable.
- **Skip lines already promoted in this session** when offering second-pass candidates.

$ARGUMENTS
