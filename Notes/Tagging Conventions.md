up:: [[Wiki]]
status:: #index

---
# Tagging Conventions

> Tags categorize notes by topic and type. They complement the status system — status says *where a note is in its lifecycle*, tags say *what it's about*.

## Rules

- Tags always use hashtag format: `#data-engineering`, not `[[Data Engineering]]`
- Tags go in the `tags::` field in frontmatter
- Multiple tags are comma-separated: `tags:: #data-engineering, #project`
- The `tags::` field is required on every note (can be empty: `tags::`)
- Tags are flexible — create new ones freely as needed
- Use lowercase with hyphens for multi-word tags: `#data-engineering`, not `#DataEngineering`

## Tag Categories

### Domain Tags (what the note is about)

| Tag | Domain |
|-----|--------|
| `#data-engineering` | Data pipelines, ETL, Spark, Hadoop, databases |
| `#homelab` | Home server, self-hosting, Docker, networking |
| `#programming` | General software development, coding |
| `#algorithms` | Algorithm design, data structures, LeetCode, problem solving |
| `#ai` | Artificial intelligence, machine learning, LLMs |
| `#productivity` | Personal systems, workflows, time management |
| `#health` | Physical health, mental health, wellness |
| `#fitness` | Exercise, training, BJJ, powerlifting |
| `#career` | Job search, interviews, professional development |
| `#books` | Reading, book notes, literature |
| `#music` | Music interests, playlists |
| `#linux` | Linux administration, Bazzite, command line |
| `#networking` | Computer networking, home network setup |
| `#obsidian` | Vault management, Obsidian tips and tricks |

### Type Tags (what kind of note it is)

| Tag | Type |
|-----|------|
| `#project` | Project documentation, plans, specs |
| `#tutorial` | How-to guides, instructional content |
| `#reference` | Lookup material, cheat sheets, quick reference |
| `#moc` | Map of Content — a topic navigation hub |
| `#brainstorm` | Ideas that were brainstormed (migrated from legacy system) |
| `#to-explore` | Topics flagged for deeper exploration |

## Examples

- Docker homelab setup: `tags:: #homelab, #tutorial`
- Brainstormed project idea: `tags:: #data-engineering, #project, #brainstorm`
- Book summary: `tags:: #books, #productivity`

See [[Templates Guide]] for full frontmatter examples including status and other fields.

---
# References

- [[Note Statuses Guide]]
- [[Naming Conventions]]
