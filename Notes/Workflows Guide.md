up:: [[Wiki]]
status:: #index

---
# Workflows Guide

> Step-by-step workflows for common vault activities.

## Capturing a New Idea

1. Create a new note (Ctrl/Cmd + N)
2. Apply the **Core Idea** template
3. Give it a descriptive title (see [[Naming Conventions]])
4. Write your thought — even a single sentence is fine
5. Add relevant tags to `tags::` if obvious (skip if unsure)
6. The note starts as `status:: #fleeting` and will appear in the **Inbox Dashboard**

## When to Use the Daily Note Instead

Not every idea needs its own note. There is a trade-off between capture and clutter:

- **New note** — the idea is guaranteed to surface (Inbox review catches it), but adds vault noise if the thought is small or uncertain.
- **Daily note** — keeps the vault clean, but the idea may get buried since daily notes aren't processed the same way.
- **Rule of thumb** — if the idea is actionable or could develop into its own note, capture it as a new fleeting note. If it's a passing thought, observation, or context for the day, leave it in the daily note.

## Processing Fleeting Notes (Inbox Review)

Do this regularly — weekly at minimum.

1. Open the **Inbox Dashboard** from Home
2. For each fleeting note, decide:
   - **Develop it** — flesh out the content, change `status:: #permanent`, add tags
   - **It's from a source** — add author/source fields, change `status:: #literature`
   - **Not relevant anymore** — change `status:: #archived`
   - **Not ready yet** — leave as `#fleeting`, come back later
3. Add `[[links]]` to connect related notes

## Creating Literature Notes

When reading a book, article, or taking a course:

1. Create a new note and apply the **Literature Note** template
2. Fill in `author::` and `source::` fields
3. Add relevant tags (e.g., `#books, #data-engineering`)
4. Summarize key ideas in your own words
5. Link to related notes in your vault using `[[wiki links]]`
6. Add the source to the `# References` section

## Starting a New Project

1. Create a new note and apply the **Project Note** template
2. Add `#project` plus relevant domain tags (e.g., `tags:: #project, #homelab`)
3. Fill in the Goal section — what are you trying to accomplish?
4. Break down Tasks into checkboxes
5. Use the Log section to track progress over time
6. Link to related notes and resources

## Promoting a Note to Permanent

When a fleeting or literature note has been developed enough:

1. Review the content — is it well-written and useful?
2. Change `status:: #permanent`
3. Ensure `tags::` accurately reflect the topics
4. Add `[[links]]` to related permanent notes
5. The note will now appear on the **Permanent Dashboard**

## Prompting a Note for Development

When you want guided prompts to help develop a note:

1. Ask Claude to "prompt [note name]" or "scaffold [note name]"
2. Claude analyzes the note and suggests writing prompts, structure tips, and action items
3. Prompts are inserted as callouts: `[!question]` for writing prompts, `[!tip]` for structure, `[!todo]` for actions
4. Work through the callouts at your own pace, deleting each as you address it
5. When done, ask Claude to "clean up [note name]" to remove any remaining callouts

## Archiving a Note

When a note is no longer active or relevant:

1. Change `status:: #archived`
2. The note moves from its current dashboard to the **Archive Dashboard**
3. It's still searchable and browsable, just out of the active workflow

## Using Handwritten Notes

The Apple Pencil is useful for visual thinking but not for text-based capture.

- **Use handwriting for:** diagrams, flowcharts, and mind maps
- **Workflow:** Sketch on the iPad, then embed the image into the relevant note in `Images/`
- **Don't use handwriting for text notes** — handwritten content is unsearchable, can't contain `[[wiki-links]]` or inline metadata (`status::`, `tags::`), and won't appear in Dataview queries. Type directly into Obsidian instead.

---
# References

- [[Note Statuses Guide]]
- [[Templates Guide]]
- [[Naming Conventions]]
