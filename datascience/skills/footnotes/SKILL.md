---
name: footnotes
description: Markdown footnotes for Jupyter notebooks using anchor links and span elements. Auto-triggered when adding references, citations, notes, or footnotes in notebook markdown cells. Works in both JupyterLab and GitHub rendering.
---

# Footnotes in Jupyter Markdown

Jupyter markdown doesn't support standard `[^1]` footnotes. Use this HTML-compatible pattern instead.

## Pattern

**In-text reference** (superscript link):
```markdown
Some claim[<sup>1</sup>](#fn1) and another point[<sup>2</sup>](#fn2).
```

**Footnote section** (at bottom of cell or notebook):
```markdown
---

<span id="fn1"><sup>1</sup> Full footnote text with source or explanation.</span><br>
<span id="fn2"><sup>2</sup> Another footnote with reference URL or detail.</span>
```

## Rules

- **IDs must be unique** across the entire notebook: `fn1`, `fn2`, `fn3`... or use descriptive names: `fn_dataset`, `fn_paper`
- **Superscript numbers** in the reference match the footnote: `<sup>1</sup>` -> `id="fn1"`
- **Footnote section**: place after a horizontal rule (`---`) either at the bottom of the markdown cell containing the references, or in a dedicated `## Footnotes` cell at the end of the notebook
- **Line breaks**: use `<br>` between footnotes for vertical spacing
- **Keep footnotes short** - one or two sentences. For longer references, link to the source

## Example

```markdown
The model uses cosine similarity[<sup>1</sup>](#fn1) for nearest-neighbor lookup.
Training follows the SimCSE approach[<sup>2</sup>](#fn2) with dropout-based augmentation.

---

<span id="fn1"><sup>1</sup> Cosine similarity measures the angle between vectors, ranging from -1 (opposite) to 1 (identical).</span><br>
<span id="fn2"><sup>2</sup> Gao et al. 2021 - "SimCSE: Simple Contrastive Learning of Sentence Embeddings" https://arxiv.org/abs/2104.08821</span>
```

## When to use

- Academic citations in analysis notebooks
- Method references (paper links, documentation)
- Clarifying assumptions or caveats without cluttering the main text
- Data source attribution
