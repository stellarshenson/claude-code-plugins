# research brief

Produces research file = best practices, paradigms, patterns the adversary reviews against. Nothing else: no product fact, API doc, bug lookup. Reader = frontier reviewer model, which already knows most of it: the file points, it does not teach. Not prose. Not for humans. Token budget first.

In: ADVERSARY. TOPICS = persona axes needing a sourced rule (author time) or adjudicator-approved questions (review time). OUT = plugin baseline `references/<adversary>/research.md` (author time) or project cache `.claude/review-research/<adversary>/research.md` (review time, append). NOTES = belief log: `tmp/research/<adversary>/beliefs.md` at author time (not shipped); `/tmp/review-research/<adversary>-beliefs.md` at review time, never inside the reviewed project.

## Per topic

1. Name 1-3 canonical sources: standards body, peer-reviewed, owner guideline page. Paraphrase blog, quote site = skip.
2. Belief test: before fetch, one line - what the source says on this axis.
3. Fetch: WebSearch locates, WebFetch reads. Not fetched = not written. No guessed URL, DOI. Paywall: resolving doi.org or abstract page, else drop.
4. Belief matches page → REFERENCE. Belief wrong on the point that matters, or none (published after model cutoff, niche study, number not recalled, correction of a widely repeated rule) → FULL.

One entry per topic; a second only when it corrects or bounds the first. Topic no fetchable source anchors → `Unsourced:` line. One pass rarely enough: next pass takes only the Unsourced topics; stop when a pass adds nothing.

## OUT

- Head: `# <adversary> research`, then `Fetched <date>. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.`
- `## <topic, 2-5 words>` per topic
- REFERENCE: `- [Short title year](url) - <rule, 12 words max>`
- FULL: `- [Short title year](url): "<one verbatim sentence>". Rule: <rule>. Tell: <what reviewer sees in the artefact>.`
- No intro, summary, transitions. Drop articles, copulas. Terse fine if unambiguous. Author-time file under 3 KB; over → drop references before full entries.

## NOTES

`- <url> | belief: <one line> | page: match | differs: <what> | no prior belief | dropped: <why>`

## Wire (author time)

- Path pattern lives once, in `agents/adversarial-reviewer.md`; persona names no path, keeps no copy. Mode 2 reads file; Mode 1: no file, claim = `unsourced`.
- Linkage test: every adversary has its file; every `- [` line has https link.

## Re-run

Author time: persona gains axis; source found wrong. Review time: approved request + cache miss + user permission + budget left; one question = one unit. Never inside a round.
