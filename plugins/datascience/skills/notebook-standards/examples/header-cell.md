# Header cell - canonical template

Mirror this for the first markdown cell (skill `notebook-standards`). Shows the four mandatory blocks (Title, Author, Date, Purpose) plus the optional menu - pipeline stage, mechanism overview, approach, outputs. Note the trailing `<br>` on every stacked provenance line; without it markdown soft-wraps them onto one line.

```markdown
# Document Segmentation with SaT

**Author**: Konrad Jelen (kj) <br>
**Date**: 2026-05-30 <br>
**Pipeline stage**: 1 - statement-level segmentation <br>

Splits a source document into atomic statements with the SaT `sat-3l-sm` segmenter - the first stage of the document-distance pipeline, so this split bounds the quality of every later measure.

Downstream each statement is embedded and two documents are compared by optimal transport over the pairwise-cost matrix C:

$$W(A, B) = \min_{T \in U(a, b)} \sum_{i, j} T_{ij}\, C_{ij}$$

## Approach
1. **Extract** raw text from the PDF - the corpus arrives as PDF, SaT needs plain text
2. **Segment** into sentence-level statements - the natural transport unit
3. **Persist** to parquet - a typed artefact the embedding stage consumes

## Outputs
- `data/interim/01-statements.parquet` - one row per statement (id, text, length)
- In-notebook: statement count, length stats, distribution histogram
```

Math in the header follows the same rule as any markdown cell - unicode glyphs inline, display equations as standalone `$$...$$` blocks; see `../references/equations.md`.
