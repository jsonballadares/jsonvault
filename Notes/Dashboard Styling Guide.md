---
cssclasses:
  - dashboard
---
up:: [[Wiki]]
status:: #index

---

# Dashboard Styling Guide

> How the vault's index notes are styled. Covers the CSS snippets, custom callout types, and the Dashboard++ layout pattern.

## Architecture

The styling system has two layers:

1. **`dashboard.css`** — Layout snippet inspired by Dashboard++. Converts markdown lists into a responsive flexbox grid. Scoped to notes with `cssclasses: dashboard`.
2. **`custom-callouts.css`** — Nine custom callout types using the Catppuccin Frappe color palette. Each dashboard has its own color and icon.

Both live in `.obsidian/snippets/` and are enabled via Settings > Appearance > CSS Snippets.

## How It Works

### cssclasses Frontmatter

Every dashboard note has a YAML frontmatter block at the top:

```yaml
---
cssclasses:
  - dashboard
---
```

This tells Obsidian to add the `dashboard` class to the note's container, which activates the layout CSS. Notes without this class are unaffected.

The YAML block sits above the inline Dataview fields:

```markdown
---
cssclasses:
  - dashboard
---
up:: [[Home]]
status:: #index
```

### Dashboard++ Layout

The `dashboard.css` snippet turns top-level list items into card-like columns:

```markdown
## Section Heading

- **[[Link One]]**
	- Description text
- **[[Link Two]]**
	- Description text
```

On desktop, these render side-by-side as flex items with a background card, rounded corners, and a hover accent border. On phones (`.is-phone`), they stack into a single column automatically.

### Custom Callout Types

Each dashboard uses a themed callout for its stats header. The syntax:

```markdown
> [!callout-type] Title text
> Body content
```

Add `+` or `-` after the type for fold behavior:
- `> [!type]+ Title` — expanded by default, collapsible
- `> [!type]- Title` — collapsed by default, expandable

## Callout Reference

| Type | Color | Icon | Used On |
|------|-------|------|---------|
| `[!vault-stats]` | Lavender | bar-chart-3 | Home |
| `[!inbox]` | Yellow | inbox | Inbox |
| `[!literature]` | Sapphire | book-open | Literature Dashboard |
| `[!permanent]` | Green | gem | Permanent Dashboard |
| `[!archive]` | Mauve | archive | Archive Dashboard |
| `[!calendar-stats]` | Peach | calendar-days | Calendar |
| `[!wiki-nav]` | Teal | book-marked | Wiki |
| `[!nav]` | Pink | compass | General navigation |
| `[!recent]` | Blue | clock | Recently modified sections |

All colors are from the Catppuccin Frappe palette to complement the AnuPpuccin theme.

## Inline Dataview Stats

Dashboard callouts use inline DataviewJS to show live counts:

```markdown
> [!inbox] `$= dv.pages('"Notes"').where(p => p.status == "#fleeting").length` fleeting notes
```

This renders the callout title with a dynamic number that updates as notes are added or change status.

## Dashboard Structure Pattern

Every status dashboard follows the same structure:

```markdown
---
cssclasses:
  - dashboard
---
up:: [[Home]]
status:: #index

---

# Dashboard Name

> [!themed-callout] Live count + description

## All Notes

(Dataview TABLE query)

> [!recent]- Recently Modified
> (Dataview TABLE, LIMIT 5, collapsed by default)
```

## Mobile Behavior

The layout is fully responsive:

- **Desktop / tablet** — List items display as side-by-side cards in a flex row
- **Phone** — Cards stack vertically into a single column
- **Callouts** — Work identically on all platforms, including fold/unfold
- **Inline Dataview** — Renders on mobile if the Dataview plugin is installed

Obsidian exposes CSS classes on `body` for platform targeting: `.is-mobile`, `.is-phone`, `.is-tablet`, `.is-ios`, `.is-android`.

## Adding a New Dashboard

To create a new styled dashboard:

1. Add the YAML frontmatter with `cssclasses: dashboard`
2. Use an appropriate callout type for the stats header (or `[!nav]` as a generic option)
3. Add a Dataview TABLE for the main content
4. Optionally add a `[!recent]-` collapsed section for recently modified notes

## Troubleshooting

### Obsidianite Theme — Invisible Card Titles

**Problem:** When using the Obsidianite theme, bold wiki-link titles inside dashboard cards (e.g., `**[[Inbox]]**`) become invisible — the text color matches the card background.

**Cause:** Obsidianite applies a gradient-text effect to `<strong>` elements using `-webkit-text-fill-color: transparent` paired with a `background-image` gradient. When a `<strong>` wraps an `<a class="internal-link">`, the transparent fill color is inherited by the child link, hiding the text. The gradient only renders on the `<strong>` background, not through the nested `<a>`.

**Fix:** The following rule was added to `dashboard.css` to reset the fill color and remove the conflicting gradient for links inside bold card titles:

```css
.dashboard div > ul > li > strong .internal-link,
.dashboard div > ul > li > strong .external-link,
.dashboard div > ul > li > strong a {
  -webkit-text-fill-color: var(--text-accent);
  background-image: none !important;
}
```

This restores link visibility using the theme's accent color while keeping the gradient effect intact everywhere else.

## Files

| File | Purpose |
|------|---------|
| `.obsidian/snippets/dashboard.css` | Flexbox layout, card styling, mobile overrides |
| `.obsidian/snippets/custom-callouts.css` | Custom callout type definitions |
| `.obsidian/appearance.json` | Snippet enable/disable config |
