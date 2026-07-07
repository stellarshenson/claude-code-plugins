---
name: papers
description: Paper reference workflow - download every cited paper and write a structured digest (opening with bold numbers, key mechanism, main findings, key takeaways, tags) into the project's references/papers/ library. Use whenever a research paper is cited in a design / experiment / hypothesis / research document, recommended by a research agent, or shared by the user - even without the word "paper". Triggers - "paper", "digest", "arxiv", "cite this paper", "reference this paper", any citation added to project docs.
allowed-tools: Read, Write, Edit, Glob, Grep, WebFetch, Bash
---

# Papers - reference and digest workflow

Every paper cited in a project document (design docs, experiment registrations, hypothesis groundings, research notes) gets TWO artifacts in the project's `references/papers/` directory. A cited paper that is not downloaded and digested is a defect - no citation without both.

- `[paper] <short name>, <year>.pdf` - the downloaded PDF
- `[paper digest] <short name>.md` - the structured digest

`<short name>` is a compact human-readable title (not the arXiv id), identical between the two files - e.g. `[paper] automem memory as cognitive skill, 2026.pdf` and `[paper digest] automem memory as cognitive skill.md`.

## Getting the paper
- Prefer arXiv - `https://arxiv.org/pdf/<id>` serves the PDF directly; for other venues use the open-access PDF (OpenReview, ACL Anthology, PMLR, publisher OA)
- Verify the download is a real PDF - check the `%PDF` magic header or `file` output, never trust the extension; an HTML error page saved as `.pdf` is a recurring failure
- Paywalled with no open version - write the digest anyway from the abstract / public material, link the DOI, mark `**PDF**: unavailable (paywalled)`; the digest is still mandatory
- A research agent recommending a paper returns a verified PDF URL plus digest-ready content in the format below, so the main session only downloads and saves

## Digest format
One markdown file per paper, sections in order:
1. `**<TITLE>: <full paper title> (<year>)**` - bold header line
2. **Opening** - 2-4 sentences: the problem, the conceptual shift the paper makes (what it treats differently from prior work), the headline result with **bold numbers**
3. `**Key mechanism**` - 3-6 bullets: how it works - the algorithm, loop structure, or mathematical object; enough to sketch a reimplementation
4. `**Main findings**` - bullets with numbers inline; sub-bullets for grouped results; every finding carries a figure where the paper gives one
5. `**Key takeaways**` - what to carry forward: the conceptual lessons, what generalizes beyond the benchmark, implications for system design
6. `**Relevance**` - optional, 1-3 bullets: honest project-specific relevance, including negative verdicts ("scale-inappropriate for our graph")
7. `**Tags**` - `#CamelCase` topic tags, 2-5
8. `**Source**` - the download link and the local PDF filename

## Style
- Numbers mandatory - a finding without a figure is marketing, not a finding
- Bold the headline numbers in the opening
- Honest limitations - if the result is narrow, fragile, or contradicted elsewhere, say so in Key takeaways or Relevance
- 250-600 words per digest; the AUTOMEM example below is the calibration point
- No emojis; tags use `#`

## Example digest (calibration reference)

Full calibration digest at target quality - `examples/digest-automem.md`. Match its density: a figure in every finding, bold headline numbers in the opening, honest limitations, 250-600 words.

## Batch workflow (research rounds)
When a round cites several papers (e.g. a hypothesis slate grounded in a literature sweep):
1. Collect all (title, year, PDF URL, digest content) tuples - from research agents or your own reading
2. Download all PDFs in one pass, verify each is a real PDF
3. Write all digests in one pass using the format above
4. Only then finalize the citing document - the citation and the library land together
