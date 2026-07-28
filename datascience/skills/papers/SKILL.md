---
name: papers
description: Paper reference workflow - download every cited paper, article, report or book and write a structured digest (overview, main findings, key takeaways, tags) carrying a resolvable online provenance link into the project's references/papers/ library. Use whenever a source is cited in a design / experiment / hypothesis / research document, recommended by a research agent, or handed over by the user - even without the word "paper". Triggers - "paper", "digest", "arxiv", "cite this paper", "reference this paper", "summarize this article", "digest this book", any citation added to project docs.
allowed-tools: Read, Write, Edit, Glob, Grep, WebFetch, Bash
---

# Papers - reference and digest workflow

Every source cited in a project document (design docs, experiment registrations, hypothesis groundings, research notes) gets TWO artifacts in the project's `references/papers/` directory. A cited source that is not downloaded and digested is a defect - no citation without both.

- `[paper] <short name>, <year>.pdf` - the downloaded PDF
- `[paper digest] <short name>.md` - the structured digest

`<short name>` is a compact human-readable title (not the arXiv id), identical between the two files - e.g. `[paper] automem memory as cognitive skill, 2026.pdf` and `[paper digest] automem memory as cognitive skill.md`.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Provenance link - hard requirement

The digest's `**Source**` section carries the online provenance link: the actual downloadable or access URL for the original. Never a local filename, never a path.

- A digest outlives its PDF - it is read, quoted, and grounded against on other machines, in other repos, after the local file has moved or gone. A local path resolves for exactly one reader; a URL resolves for every reader
- Durability order: DOI URL (`https://doi.org/<doi>`) > arXiv abs page > publisher OA / PMC / OpenReview / ACL Anthology landing page > direct PDF URL. Prefer the landing page over a CDN link that rots
- Verify the URL resolves before writing it - a fabricated or dead DOI is worse than no link
- Paywalled - link the DOI anyway and add one line: `- Access: paywalled; digest written from abstract and published summaries`
- Books - link the publisher page, DOI, or a stable catalogue record (worldcat, openlibrary); an ISBN alone is not a link
- The PDF is still downloaded under the naming rule above; it simply never appears inside the digest

## Getting the source
- Prefer arXiv - `https://arxiv.org/pdf/<id>` serves the PDF directly; for other venues use the open-access PDF (OpenReview, ACL Anthology, PMLR, PMC, publisher OA)
- Verify the download is a real PDF - check the `%PDF` magic header or `file` output, never trust the extension; an HTML error page saved as `.pdf` is a recurring failure
- Paywalled with no open version - write the digest anyway from the abstract / public material and mark the access caveat; the digest is still mandatory
- A research agent recommending a source returns a verified PDF URL plus digest-ready content in the format below, so the main session only downloads and saves

## Digest prompt - the authoring contract

Apply this verbatim to produce the body of every `[paper digest] <short name>.md`. It governs papers, articles, reports, and books alike. Plain markdown with ASCII bullets, so the digest survives being quoted, diffed, and grounded against by tooling that does not render tables or Unicode decoration.

---

You are preparing a professional research digest for a technical team.

Read the attached paper, article, report, or book carefully and produce a concise but informative summary.

Formatting rules:
- Use standard ASCII hyphens "-" for every bullet point
- Do not use numbered lists
- Do not use Unicode bullets, em dashes, icons, emojis, tables, dividers, or decorative formatting
- Do not place full stops at the end of bullet points
- Keep the title and section headers in bold Markdown
- Use 1-3 tags at the end, each beginning with #
- Keep the total length around 500-900 words across all sections, but extend it if the source warrants more detail
- Keep the tone factual, professional, technically precise, and free of hype or FOMO
- Do not include a separate "Direct assessment" section

Required structure:

**[Full title of source] ([year])**

Overview paragraph of no more than 200 words explaining:
- what the work studies
- the main problem it addresses
- the proposed method or framework
- why the result matters

**Key mechanism**
- Provide 3-6 bullets on how it actually works: the algorithm, the loop structure, the training
  signal, or the mathematical object
- Enough detail to sketch a reimplementation, not a restatement of the abstract
- Name the components and how they interact, including what is held fixed and what is learned
- For a non-technical source, use the causal mechanism the work argues for and how it was measured

**Main findings**
- Provide 5-10 substantive findings
- Include concrete numbers, benchmarks, model names, datasets, costs, latency, token counts, accuracy, confidence intervals, or effect sizes when available
- Explain important mechanisms, not only headline results
- Distinguish measured results from modeled estimates, hypotheses, qualitative claims, or vendor assertions
- Mention meaningful limitations, caveats, conflicts of interest, or sample-size weaknesses when relevant
- Preserve critical methodological details needed to interpret the results
- Use nested hyphen points only when necessary for numerical breakdowns

**Key takeaways**
- Provide 5-10 actionable conclusions for an engineering or data science team
- Translate the findings into architecture, experimentation, deployment, governance, evaluation, security, or cost implications
- State what the team should consider adopting, testing, measuring, avoiding, or validating
- Separate generalizable lessons from claims that depend on a specific benchmark or architecture
- Highlight the strongest practical insight from the source
- Avoid repeating the Main findings verbatim

**Relevance**
- Provide 1-3 bullets on honest relevance to THIS project, or omit the section entirely when the
  source was not read against a specific project
- Negative verdicts are the point - "scale-inappropriate for our graph", "baseline too weak to
  transfer", "supersedes the approach in <doc>" - a digest that only ever says yes is not a filter
- Name the project artifact the source bears on (design doc, experiment, hypothesis) where one exists

**Tags**
- #tag
- #tag
- #tag

**Source**
- The online provenance link, per the provenance rule above

Analysis requirements:
- Base the summary strictly on the supplied source
- Read tables, charts, diagrams, appendices, and footnotes where relevant
- Do not infer unsupported facts
- Do not exaggerate conclusions
- If the source is promotional, vendor-authored, a preprint, or not peer-reviewed, state this briefly and explain how it affects confidence
- If results are based on a small sample, observational data, modeled estimates, synthetic tasks, or a narrow domain, state that clearly
- When the work compares methods, identify whether the baseline is strong, weak, naive, or incomplete
- When a metric is relative, preserve the original baseline and absolute values
- Prefer exact figures over vague phrases such as "significantly better"
- Preserve technical terminology where useful, but explain uncommon concepts briefly
- Avoid marketing phrases such as "game-changing", "revolutionary", "must-read", or "paradigm shift" unless directly quoting and critically qualifying the source

---

Calibration reference at target quality - `examples/digest-automem.md`.

## Batch workflow (research rounds)
When a round cites several sources (e.g. a hypothesis slate grounded in a literature sweep):
1. Collect all (title, year, provenance URL, PDF URL, digest content) tuples - from research agents or your own reading
2. Download all PDFs in one pass, verify each is a real PDF
3. Write all digests in one pass using the prompt above
4. Only then finalize the citing document - the citation and the library land together
