up:: [[Wiki]]
status:: #index

---
# Templates Guide

> The vault has 4 templates. Use them to create new notes with consistent structure.

## How to Use Templates

1. Create a new note (Ctrl/Cmd + N)
2. Open the command palette (Ctrl/Cmd + P)
3. Search for "Templater: Insert template" or "Templates: Insert template"
4. Select the appropriate template

## Available Templates

### Core Idea
**File:** `Templates/Core Idea.md`
**When to use:** Any new note — quick ideas, thoughts, anything that doesn't fit the other templates.
**Creates:** A fleeting note with auto-generated ID, ready for the Inbox.

```
{{date:YYYMMDD}}{{time:HHmm}}
status:: #fleeting
tags::

---
# {{title}}

---
# References
```

### Daily Note
**File:** `Templates/Template, Daily Note.md`
**When to use:** Automatically applied when you open today's daily note via the Calendar or Periodic Notes plugin.
**Creates:** A daily journal entry with Wind Up/Log/Scratchpad/Wind Down sections.

### Literature Note
**File:** `Templates/Literature Note.md`
**When to use:** Notes about books, articles, courses, videos, or any external source.
**Creates:** A literature note with author and source fields.

```
status:: #literature
tags::
author::
source::

---
# {{title}}

---
# References
```

### Project Note
**File:** `Templates/Project Note.md`
**When to use:** Project documentation — plans, specs, ongoing work.
**Creates:** A structured project note with goals, tasks, and log sections.

```
status:: #permanent
tags:: #project

---
# {{title}}

## Goal

## Tasks
- [ ]

## Log

---
# References
```

---
# References

- [[Vault Structure Guide]]
- [[Workflows Guide]]
