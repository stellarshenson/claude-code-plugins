---
name: popular-science
description: Write an accessible, well-sourced popular-science article or explainer from technical work - an experiment result, a research finding, a design, a README - for a curious non-specialist. Applies industry best practices: a hook and an early nut graf, the ladder of abstraction (show and tell), every empirical claim paired with its named source and a hard number, figures matched to their message and built to best-in-class standard, and an ending that arcs back to the opening and closes with conclusions and next steps. Use when writing or rewriting an article, blog post, explainer, story, or public-facing writeup of technical or scientific work. Triggers - "write an article", "write this up as an article", "popular-science writeup", "explainer", "blog post about", "make this readable for a general audience", "turn this experiment into an article".
allowed-tools: Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Bash, Skill
---

# Popular science - write an accessible technical article

Turn technical work into an article a curious, busy non-specialist reads to the end and is glad they did. This skill is the writer; its critic is the `popular-science` adversary in `datascience:adversarial-review` - draft here, review there, revise.

- **Register** - a smart reader in another field: respect their intelligence, never their prior knowledge
- **The bar** - the best of the field (Quanta, Scientific American, NYT/FT visual journalism, Our World in Data); write to it, do not settle below it
- **The spine** - hook → nut graf → ladder of abstraction → sourced claims → arc-back kicker; every section below is one vertebra
- **Full craft canon** - best practices, anti-patterns, visual standards and named reference sources live in `references/craft-canon.md` (the single source of truth, shared with the `popular-science` adversary); read it before drafting
- **Structure templates** - pick one before drafting: `references/structures.md` (WSJ formula, inverted pyramid, ladder/narrative arc, braided, martini glass)
- **Exemplar teardowns** - five best-in-class articles torn down on the spine: `examples/teardowns.md`

## When to use
- Writing up an experiment, result, finding, design or README for a non-specialist or a public audience
- Rewriting a dense internal doc into a readable article, blog post, explainer or story
- Not for: an internal spec or reference doc (that is Modus Secundis / technical-documentation), a journal entry (the journal plugin), or the SOTA conclusions doc (the `hypothesis` skill)

## The spine - structure every article on this
- **Hook** - the opening earns the second sentence: a scene, a number, a paradox, a person. A reader decides in two sentences
- **Nut graf** - early, not always right after the lede: the story in a nutshell - what it is, and why it matters to the reader
- **Ladder of abstraction** - climb both ways: scenic detail (show - zoom in on the concrete thing) and summary meaning (tell - zoom out to what it means). Good writing constantly ascends and descends it
- **Sourced claims** - a bare claim is weak; the named research team and the hard figure sell it. Pair every empirical assertion with `(Author, year)` or an honest "our model finds", and with the demonstrated number, never an adjective ("2.0% vs 6.2% across 476 couples", not "about a third")
- **Concreteness** - every abstraction gets one anchor: an image, a number the reader can see, a person making a choice
- **One idea per sentence; short paragraphs** - one beat each; break the wall of text (white space is oxygen on a screen)
- **Visuals** - see below; a figure earns its space or it is chartjunk
- **The kicker** - end on a line that lands: arc back to the opening image or question (callback / bookend, full circle with a twist), then conclusions, then next steps where the work continues. The best endings echo the beginning in an essential but surprising way

## Visuals
- **Match the chart to the message** - deviation, correlation, ranking, distribution, change-over-time, part-to-whole, magnitude, spatial, flow (FT Visual Vocabulary)
- **Build to the bar** - one message per figure, direct labels over legends, honest axes, colourblind- and greyscale-safe, maximise data-ink and erase chartjunk (no 3-D, no truncated axis, no rainbow colourmap)
- **Generate figures via `svg-infographics:svg-designer`** - hand it the one message and the data; do not hand-roll a messy chart
- **A missing figure is a defect too** - if the prose strains to describe a relationship, name the one diagram that would carry it

## Workflow
1. **Frame** - name the single reader (which non-specialist) and the one thing they should carry away. Everything serves that
2. **Source** - for every empirical claim, get its `(Author, year)` and its number. When a paper is cited, follow the `datascience:papers` skill: download the PDF and write its digest into `references/papers/` - a cited-but-undigested paper is a defect
3. **Outline to the spine** - hook, nut graf, the two or three beats, the arc-back kicker; decide the one or two figures and their single message each
4. **Draft** - climb the ladder both ways; one idea per sentence; short paragraphs; claim + provenance + number every time
5. **Figures** - commission each via `svg-infographics:svg-designer`, matched to its message, compared against best-in-class
6. **Self-critique** - run the draft through `datascience:adversarial-review` with the `popular-science` adversary (Mode 2 if it must render and judge the figures). Fix every BLOCKER/MAJOR; weigh the JUDGEMENTs
7. **Revise and confirm** - the hook lands, every claim is sourced and numbered, the ending arcs back and closes with conclusions + next steps

## Bringing in reference articles (license-aware, token-cheap)
Do not fetch and read exemplar articles into context by hand - run the tool. It downloads and extracts out-of-context (saving tokens) and enforces licensing so you do not have to judge it.

- **Run it** - `python3 scripts/fetch_article.py URL --license <spdx> --name "<short>" --author "<a>" --outlet "<o>"`
- **Run from a temp dir** - so no `uv.lock` / `__pycache__` lands in the repo; output still goes to `examples/downloaded/` (the script uses an absolute path):
  ```bash
  W="$(mktemp -d)/run"; mkdir -p "$W"; cd "$W"
  python3 <skill>/scripts/fetch_article.py URL --license CC-BY-4.0 --name "…" --author "…" --outlet "…"
  ```
- **License policy the tool enforces** - a verbatim-redistributable license (CC-BY, CC-BY-SA, CC-BY-ND, CC0, public-domain) → full text saved with an attribution + license header; proprietary / unknown / NonCommercial → a link + attribution stub ONLY, no body. Every run appends to `examples/downloaded/ATTRIBUTION.md`
- **Proprietary sources** - never bundle the body; keep your own teardown + short fair-use excerpts + the link in `examples/teardowns.md`
- Bundled exemplars live in `examples/downloaded/`; the ledger is `examples/downloaded/ATTRIBUTION.md`

## Calibration
The target register - myth stated, broken with a NAMED source and a HARD number, closed on a witty turn - is in `examples/myths-calibration.md`. Match its density: a claim alone is weak; the research team and the numbers sell the story.

## Rules
- Never dumb down the substance - make it readable, not shallow; the idea stays, the fog goes
- Every empirical claim carries its source and its number, or it is cut
- One default register (curious educated generalist), not a menu; explain the why, do not lecture
- Figures go through `svg-infographics:svg-designer`; prose sourcing goes through `datascience:papers`; self-review goes through the `popular-science` adversary - do not reinvent them here
- No git commit / publish unless the user asks
