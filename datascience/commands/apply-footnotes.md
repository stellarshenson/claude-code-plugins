---
description: Add or fix footnotes in a notebook or markdown file using Jupyter-compatible anchor pattern
allowed-tools: [Read, Write, Edit, Glob, Grep, Skill]
argument-hint: "path to file and what to footnote, e.g. 'notebooks/01-kj-analysis.ipynb add citations for papers mentioned'"
---

# Apply Footnotes

Read the `datascience:footnotes` skill first - it is the single source of truth for the footnote pattern. Do NOT duplicate its content here.

Add Jupyter-compatible footnotes to a notebook or markdown file. Converts inline references to superscript anchor links with a footnote section.

## What to do

1. Read the target file
2. Identify what needs footnotes based on user's request:
   - Paper references mentioned in prose
   - Technical claims that need sources
   - Acronyms or terms that need definition
   - Data sources that need attribution
   - User-specified items

3. For each footnote:
   - Insert `[<sup>N</sup>](#fnN)` at the reference point in text
   - Add `<span id="fnN"><sup>N</sup> Footnote content.</span><br>` to footnote section

4. If no footnote section exists, create one:
   - In notebooks: add `## Footnotes` markdown cell at the end, or `---` separator in the same cell
   - In markdown: add `---` separator + footnotes at the bottom

5. Number footnotes sequentially: fn1, fn2, fn3...
   - If file already has footnotes, continue from the highest existing number

## Fixing existing footnotes

If the file has broken footnotes:
- Missing `id` on spans -> add them
- Mismatched numbers (sup says 3 but id says fn5) -> renumber
- Plain `[1]` references -> convert to `[<sup>1</sup>](#fn1)` pattern
- Footnotes without `<br>` between them -> add breaks
- Standard markdown `[^1]` syntax (not supported in Jupyter) -> convert to anchor pattern
