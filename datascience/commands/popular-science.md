---
description: Create or update an accessible, well-sourced popular-science article or explainer from technical work - hook, nut graf, ladder of abstraction, sourced-and-numbered claims, best-in-class figures, arc-back kicker with conclusions and next steps
allowed-tools: [Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Bash, Skill]
argument-hint: "what to write or update, e.g. 'an article from the E12 experiment results' or 'rewrite README.md as an explainer' or 'update article.md - the kicker does not land'"
---

# Popular science

Read the `datascience:popular-science` skill first - it is the single source of truth for the spine, the craft canon, the visual standard, the license-aware reference tool, and the workflow. Do NOT duplicate it here.

## What to do

1. Read the `datascience:popular-science` skill and the `references/craft-canon.md` it points to
2. Decide create vs update from the argument:
   - **Create** - no target file yet: frame the single reader and the one takeaway, then follow the skill's workflow (frame → source → outline to the spine → draft → figures → self-critique → revise)
   - **Update** - a target article exists: read it, apply the requested change (or, if none is named, run it through the `popular-science` adversary and fix what the review surfaces), and re-confirm the spine end to end - hook lands, every claim carries source + number, the ending arcs back with conclusions + next steps
3. Source every empirical claim via `datascience:papers`; commission every figure via `svg-infographics:svg-designer`; self-review via `datascience:adversarial-review` with the `popular-science` adversary - do not reinvent them here
4. No git commit / publish unless the user asks
