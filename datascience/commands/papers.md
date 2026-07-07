---
description: Download every cited paper and write a structured digest into references/papers/ - the paper reference library for a project's design / experiment / hypothesis docs
allowed-tools: [Read, Write, Edit, Glob, Grep, WebFetch, Bash]
argument-hint: "the paper(s) to reference, e.g. 'arxiv 2401.12345' or 'the EAGLE-3 speculative decoding paper cited in R7'"
---

# Papers

Read the `datascience:papers` skill first - it is the single source of truth for the artifact naming, the digest format, and the download / verify rules. Do NOT duplicate it here.

## What to do

1. Read the `datascience:papers` skill
2. Resolve each paper to a verified open-access PDF URL (prefer arXiv `https://arxiv.org/pdf/<id>`)
3. Download into `references/papers/[paper] <short name>, <year>.pdf`; verify the `%PDF` magic header - never trust the extension
4. Write `references/papers/[paper digest] <short name>.md` in the skill's digest format (bold-header title, opening with bold numbers, key mechanism, main findings, key takeaways, tags, source)
5. Cite the digest from the calling document by its local filename; a citation without both artifacts is a defect
6. Several papers in one round - batch: download all, verify all, digest all, then finalize the citing doc
