---
name: footnotes
description: Markdown footnotes for Jupyter notebooks and markdown files using anchor links and span elements. Auto-triggered when adding references, citations, notes, or footnotes in any markdown context. Works in JupyterLab, GitHub, and standard markdown renderers.
---

# Footnotes in Markdown

Standard `[^1]` footnotes aren't supported in Jupyter or many markdown renderers. Use this HTML anchor pattern instead - proven to work in JupyterLab (including its id sanitizer), GitHub, and standard markdown.

## How it works in JupyterLab

1. Markdown writes `<span id="D005">`
2. JupyterLab sanitizer renames `id` to `data-jupyter-id="D005"` (does NOT delete it)
3. User clicks the blue superscript link `[<sup>D005</sup>](#D005)`
4. JupyterLab's internal click handler matches `#D005` against `data-jupyter-id="D005"`
5. Calls `scrollIntoView()` on the target element - page scrolls to the entry

## Pattern

**Inline reference** (clickable superscript in text):
```markdown
- dowód: [<sup>D005</sup>](#D005) dowody/03 komunikacja z matką/2023-09-06 pismo.pdf
```
Renders as: clickable blue superscript **D005** followed by the file path.

**Target anchor** (in footnotes/references section):
```markdown
- <span id="D005">D005 `dowody/03 komunikacja z matką/2023-09-06 pismo.pdf`</span>
```
Renders as: bullet point with D005 label and monospace file path.

## Requirements

- Target **MUST** use `<span id="...">` (not `<div>`, not heading - span works reliably with JupyterLab sanitizer)
- Inline link **MUST** use `(#DXXX)` hash format (not relative file path)
- No `<br>` needed between entries - bullet points handle spacing
- `<sup>` inside the link is optional (cosmetic superscript) but should **NOT** be inside the target span
- IDs must be unique across the entire document

## Numbering Schemes

Use a prefix that matches the content:

| Context | Pattern | Example |
|---------|---------|---------|
| Evidence/documents | `D001`, `D002` | `[<sup>D005</sup>](#D005)` |
| General footnotes | `fn1`, `fn2` | `[<sup>1</sup>](#fn1)` |
| Paper citations | `ref1`, `ref2` | `[<sup>ref3</sup>](#ref3)` |
| Named references | `fn_dataset`, `fn_paper` | `[<sup>*</sup>](#fn_dataset)` |

## Full Example

```markdown
## Timeline

- **2023-01-15 - Author submits proposal to committee**
  - source: email
  - evidence: [<sup>D001</sup>](#D001) documents/2023-01-15 proposal submission.pdf
  - category: Submissions

- **2023-02-20 - Committee responds with revision request**
  - source: letter
  - evidence: [<sup>D002</sup>](#D002) documents/2023-02-20 revision request.pdf
  - category: Responses

---

## References

- <span id="D001">D001 `documents/2023-01-15 proposal submission.pdf`</span>
- <span id="D002">D002 `documents/2023-02-20 revision request.pdf`</span>
```

## When to use

- Evidence references in legal/analytical documents
- Academic citations in analysis notebooks
- Method references (paper links, documentation)
- Data source attribution
- Any cross-referencing within a long markdown document

## Common mistakes (learned from production)

- Using `<div id="...">` instead of `<span id="...">` - JupyterLab sanitizer handles span reliably
- Putting `<sup>` inside the target span - makes the label superscript at the target too
- Using file paths as href instead of `#ID` hash links - won't scroll
- Forgetting the `#` prefix in the inline link - `(D005)` doesn't work, `(#D005)` does
- Using `<br>` between bullet-point entries - redundant, bullets already have spacing
