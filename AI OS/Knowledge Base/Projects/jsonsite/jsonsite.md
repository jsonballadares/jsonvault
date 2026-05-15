origin:: agent
type:: #project
tags:: #programming

---
# jsonsite

Personal resume and portfolio website. Tagline: *"a personal virtual playground for json"*.

**Local path:** `~/Repos/jsonsite`
**Remote:** `git@github.com:jsonballadares/jsonsite.git`
**Branch:** `main`

---

## Stack

Zero-dependency static site. No build tools, no package manager, no frameworks.

| Layer | Technology |
|---|---|
| Markup | HTML5 (semantic, no templating) |
| Styling | Pure CSS3 with custom properties |
| Behavior | Vanilla JS (ES6+) |
| Graphics | SVG (inline + external assets) |

## File Structure

```
jsonsite/
├── index.html      # Single-page resume
├── styles.css      # All styles
├── script.js       # Scroll animation
└── assets/         # Employer SVG/PNG logos
    ├── accelirate-logo.svg
    ├── centene-logo.svg
    ├── circulo-health-logo.svg
    └── mdc-kendall-logo.svg
```

## Content

Single-page resume covering four sections:

**Experience:**
- Centene Corporation (July 2022 – present) — high-throughput Go APIs, ETL pipelines, Kafka/MongoDB optimization, cloud migration
- Circulo Health (May 2021 – June 2022) — full-stack on AWS/Terraform/Go/React (SONAR platform), Vue.js refactor of Angular admin
- Accelirate (Oct 2019 – May 2021) — RPA team lead (10 engineers), ML/OCR document processing, UiPath/AWS/NoSQL
- Miami Dade College (June 2018 – Oct 2019) — frontend for chemistry mobile app (Unity + MERN)

**Projects:**
- MeetTwoEat — Android app for coordinating meetups via location APIs
- Memer — CLI using Google Cloud Voice Recognition + Imgur API for ASCII art generation

**Skills:**
- Languages: Go, JavaScript/TypeScript, Java, C# (working: Python, Bash)
- Technologies: AWS, Kafka, GitLab, MongoDB, Kubernetes, Unix (working: React, Angular, Vue, Django)

**Education:**
- BS Computer Science (Honors), Florida International University — GPA 3.42
- AA Computer Science, Miami Dade College — GPA 3.9

## Notable Implementation Details

**Scroll animation (`script.js`):** The "JSON" logo scales from 100% → 70% as the user scrolls past 250px. Uses `requestAnimationFrame` with a `ticking` flag to avoid frame thrashing. Passive scroll listener for scroll performance.

**CSS custom property:** `--json-scale` is updated via JS and consumed by a CSS `transform: scale()` on the logo.

**Print styles:** Dedicated `@media print` block strips padding and removes link styling — the page is designed to be printable as a resume.

**Responsive:** Single breakpoint at 600px. Max-width container at 900px.

**Logo:** Inline SVG with per-letter class hooks, letter-spacing −8px, white fill with 3px black stroke, subtle hover scale (1.02x).

---
# References

- [[Go]]
