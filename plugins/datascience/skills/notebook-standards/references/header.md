# Header cell - fields and optional menu

Resource for the `notebook-standards` skill. Carries the per-field detail of the first markdown cell - the `<br>` stacking mechanics and why, the Purpose guidance, and the full optional menu (more provenance, mechanism overview, approach, outputs). SKILL.md keeps only that the Header doubles as the notebook's own overview, so it needs no separate one, and that title, author, date and purpose are mandatory. Mirrorable template: `../examples/header-cell.md` - do not restate it here.

## Mandatory fields - every notebook

- **Title** - `# <what the notebook does>`
- **Author + Date** - bold, each on its own `<br>`-terminated line so they stack: `**Author**: Name (initials) <br>` then `**Date**: YYYY-MM-DD <br>`
- **Why the `<br>`** - without it markdown soft-wraps Author and Date onto one line
- **Purpose** - one or two sentences: what the notebook produces and why it matters to the wider work
- **Purpose is prose** - not a task list

## Menu - add when the problem calls for it

- **More provenance** - further `<br>`-terminated lines after Date: `**Pipeline stage**`, `**Dataset**`, `**Model**`, `**Branch**`
- **Mechanism overview** - a short paragraph on HOW the approach works when the method is non-obvious: the key model / algorithm, what it computes, the operating regime a reader needs to trust the result
- **Approach** - `## Approach`, numbered verb-first steps, each naming its why
- **Outputs** - `## Outputs`, persisted artefacts plus what renders inline

## Math in the header

Math follows the Equations section of SKILL.md - unicode glyphs inline, each display equation a standalone `$$...$$` block. Forms and glyph set: `equations.md`.
