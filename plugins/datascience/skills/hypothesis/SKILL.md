---
name: hypothesis
description: Structure and maintain hypothesis-driven research documentation - a canonical append-only experiments log (each hypothesis with a self-contained, independently reproducible experiment setup, prediction, result, verdict) and a SOTA design doc distilling the winners. Use when the user is writing up an experiment, recording a hypothesis and its result, comparing approaches to decide which wins, defining a naive baseline, running an experiment's hypotheses as agents, fanning out the next round of hypotheses, ablating survivors into a final design, drafting a research report with a problem overview and executive summary, or concluding a state-of-the-art / final-design doc - even without the word "hypothesis". Triggers - "document this experiment", "write up the hypothesis", "experiments doc", "sota doc", "research writeup", "which approach won", "record this round", "run this experiment", "fan out hypotheses", "propose the next round", "ablation study", "update the experiments log", "structure my results".
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch
---

# Hypothesis

Maintain two research docs: a canonical **experiments log** (every hypothesis with setup, prediction, result, verdict) and a **SOTA document** (survivors distilled into a final design). Log is append-only and grows across runs; SOTA is rewritten when the arc converges.

> **Style** - terse technical-documentation: 1-2 overview sentences then factual bullets; one fact per bullet; numbers inline; no full stop ending a bullet; no em-dashes (use ` - `), unicode arrows (→), escape `\$`. Prose only where an argument needs it. Full reference: the `technical-documentation` skill.

**Mirror the closest `examples/` doc before writing** - its section order wins over this skill's guidance on any conflict. Do not invent structure. See Examples for which to pick.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Ledger queries - `hypothesis-tools`

Read the ledger's state through the CLI, never by re-reading the file. A twelve-round log is 300+ lines to re-read for one ordinal, and the cost grows every round. Read-only - it never writes; use Edit for that. Full command reference and the parse contract in `references/ledger-queries.md`.

| command | answers |
|---|---|
| `hypothesis-tools next-id <log>` | next free global `H<n>` + next `E<batch>` - the fanout dedupe number |
| `hypothesis-tools list <log> [--verdict V] [--batch E12] [--json]` | every id, slug, verdict + the tally; `--verdict none` for unverdicted |
| `hypothesis-tools show <log> E12-H33` | one hypothesis verbatim, instead of the whole log |
| `hypothesis-tools check <log>` | validates the ledger; exit 1 on any error - rules in `references/ledger-queries.md` |

- **Never guess the next ordinal** - `next-id` reads it; a reset or reused `<n>` makes one number name several hypotheses and has to be undone later
- **`next-id` refuses rather than guesses (exit 1)** - an unclosed code fence or an id it could not parse means the highest ordinal may not be the highest; fix what it names, never work around it
- **A compact-shape hypothesis reports `verdict: null`** - its verdict is narrative, and the tool refuses to infer one from prose rather than return a confident wrong label; read the line with `show` when the verdict matters

## Workflow
- Pick the doc - experiments log (recording work) or SOTA doc (concluding once the arc converges)
- Open the canonical doc before writing - `hypothesis-tools list` for the round state, `next-id` for the next ordinal, append after the last round
- Generating hypotheses (single or fanout batch) - ask scale + persona, pre-register before anything lands or runs; see Fanout
- Updating an existing hypothesis (re-run, fix, changed threshold) - append a `log:` line to its Log; original Result and Verdict stay as recorded, a verdict flip becomes a new round
- Before concluding a SOTA - suggest an ablative study of the strongest hypothesis or all survivors, to measure each component's marginal worth; see `references/execution-and-ablation.md`
- Draft, then re-read; cut any sentence a table or number carries faster

## Model roles - theorise strong, execute deliberately
Plan is only as good as the model that wrote it, result only as trustworthy as the model that ran it.
- **Theorise + plan on the strongest model** - hypothesis, mechanism and Experiment test-plan must carry enough context for the executor; a thin plan wastes the run
- **Execute on opus by default** - offer the choice (opus / sonnet / haiku) before a costly sweep; record the execution model in the Experiment block; execution is agent-based (spawned agent primed with the full Experiment block + return schema), never inline - protocol in `references/execution-and-ablation.md`

## Canonical documents across runs
One durable file many runs append to - the system of record, not a fresh writeup each session.
- **Repeatable layout** - one home per kind so experiment work is never scattered:
  - `docs/experiments/<project>-experiments.md`, `docs/<project>-sota.md` - canonical log + SOTA, one per track, named for the track not the date
  - `src/experiments/` - durable experiment code + the notebook that runs a hypothesis; the Experiment block's execution-artefact points here; plain `scripts/` only for one-offs that do not belong in `src/`
  - `reports/experiments/` - written-up experiment reports
  - `tmp/<kind>/` - transient only (temp models, temp data, scratch notebooks); nothing durable lands here
- **Experiment code naming** - name each code file for the id it serves so it maps back to the log: `E<batch>|R<round>-H<n>` when specific to one hypothesis, `E<batch>|R<round>` when it covers the whole batch (`R30-H106_throughput.ipynb`, `R30_setup.py`). Pick one token per project and keep it
- **Secondary-title marker** - under the H1, every canonical doc carries `**Canonical Experiments Document**` (log) or `**Canonical SOTA Document**` (design); marks the system of record beyond the filename
- **Find it first** - `Glob docs/**/*experiments*.md` and `*sota*.md`, confirm by the marker (a marked doc is canonical even if the filename misses the glob); append to it, never start a parallel doc for the track
- **Append-only** - each run adds its round at the end (`E<batch>` / `R<round>`), monotonic numbering; a recorded verdict is immutable - later evidence is a new round superseding it with a one-line back-reference; never renumber or rewrite an old round; a verdict flip spawns a new round
- **SOTA on convergence** - rewrite only when the winning design changes; carries surviving components only
- **Cross-link the pair** - SOTA states the design, log proves it; each names the other by path
- **Sanitise every run** - no client/customer name (use "private dataset"); private data paths stay git-ignored

## User-facing summary tables
Two tables in the conversation - pre-registration (planned hypotheses, signed off before any run) and finding (same rows plus a Verdict column with its number). Distinct from the in-doc research-at-a-glance table. Column spec, jargon-with-a-gloss rule, column→template mapping in `references/summary-tables.md`; tables to mirror in `examples/summary-table.md`.
- **Always show both** - before table = what the user signs off, after table = what was learned; surface in the reply, not only in the doc
- **Render 2+ hypotheses as a markdown pipe table** - one row per hypothesis, never `label: value` stanzas or `────` blocks; adapt only when the render genuinely needs otherwise (single hypothesis, one-number answer)

## Experiments log
Section order and each section's must-have in `references/experiments-log-structure.md` - read it before writing, do not invent the order. Define the naive baseline in Methodology.

## Per-hypothesis template
Each hypothesis: one-paragraph overview, optional unlabelled lever-detail paragraph (the setup story, only when the regime has one), then the fixed bullet set. Overview, lever-detail and Experiment block together must let a reader reproduce and independently test it from the doc alone. Field spec, naming/ordinal scheme, Log rendered example, and Experiment-block-vs-shared-Setup in `references/per-hypothesis-template.md`.
- **Fields** - Hypothesis, Lever, Mechanism, Prediction, Acceptance bar, Pre-experiment probe (optional), Experiment, Result, Verdict, Log (optional)
- **Hypothesis form** - `because <mechanism>, <intervention> will <outcome ≥ threshold> while <guardrail>`
- **Verdicts** - the closed set enumerated once in `references/per-hypothesis-template.md`, each with the number that justifies it; `hypothesis-tools check` rejects anything outside it
- **Id** - `E<batch>|R<round>-H<n>`, one global ascending `<n>` never reset; a 2-3 part slug aids memory but the numeric id is the identity; the batch/round token groups 2-5 hypotheses. Resetting `<n>` per round makes one number name many hypotheses - it has to be undone later
- **Experiment block vs shared Setup** - carry the block when a hypothesis owns its regime (own artefact / procedure / data); omit when a shared Setup already covers a one-toggle batch

## Writing a good hypothesis
- **Predict the result** - state outcome and direction before running; no stated expectation = cannot confirm or refute; a wrong prediction that misses still teaches
- **Pre-register the bar** - the pass/fail gate deciding ship vs drop, before building
- **Diagnostic kill-gate** - measure the precondition before any build; absent precondition → kill cheaply (errors must concentrate ≥30%, ratio >1.5 → measured 0.93 → killed pre-build)
- **Probe first** - measure firing rate / density on a sample before wiring
- **Two-sided acceptance** - improve the target AND hold the control; no silent regression
- **Mechanism, not data** - gate the feature inert where the mechanism is absent; test the mechanism, not memorised text
- **Falsifiable probe** - measurement-only; never trains, never enters cross-validation
- **Honest splits** - leave-one-X-out; no learner touches the fold it scores; name the headline split and why
- **Size-dependent** - re-run as data grows; never trust a single snapshot - record each re-run as a `log:` line so the trajectory stays visible, not overwritten
- **Reproducible plan** - re-runs from its own text; name the provenance of any artefact so the claim is never thin (bare "trained draft head" → "EAGLE-3 head obtained `<id>`"); full spec in the Reproducibility rule

## Fanout - generating the next round
Generate hypotheses from the campaign's kernel instead of waiting for them; pre-registration gates everything. Mechanics, kernel definition, perturbation operators, portfolio rule in `references/fanout.md`.
- **Two scales** - a single specific hypothesis on request, or a persona-driven batch; ask the user for scale (probe 3-5 / round 8-12 / batch 15-25) and persona, recommending both from the log state
- **User's framework is the generative seed** - a user-dictated framework (hypothesis, mechanism, lever, area, hunch) is what the fanout generates FROM - perturbed by the operators, extrapolated, explored around; never filed as just one more candidate
- **Personas** - pluggable hypothesisers in `generators/` (follower, contrarian, heretical, hybridizer, mechanist, deflationist, scout); each an exploration policy with an expected verdict signature that self-tests the round - read the chosen file before generating
- **Kernel first** - fanout requires the log's typed interface: channel vocabulary, lever record (forcing + decay + cost), metric panel + naive baseline, verdict protocol; elicit into Methodology on the first fanout - ask the author, never invent channels
- **Pre-registration is the prerequisite** - every generated hypothesis is proposed via the pre-registration table and signed off BEFORE it is appended or executed; dedupe against the global H-ordinal registry (`hypothesis-tools next-id`), run a cheap kill-gate pass before proposing

## SOTA document
Conclusion doc; carries surviving components only, cross-links the log as evidence. Section order and each section's must-have in `references/sota-document.md` - read it before writing. Drop a section only when the design has nothing for it.

## Examples
Read the closest match first, mirror its section order.
- `quantized-inference-experiments.md` - **primary reference**; per-hypothesis-regime shape, each hypothesis owning its models / harness: overview → lever-detail → Lever → `<br>`-labelled Experiment → Result
- `wmd-docdistance-experiments.md` - compact / shared-Setup variety; one batch, five one-toggle levers
- `wmd-docdistance-sota.md` - canonical SOTA, maths-heavy Mechanism (LaTeX, why-not-cosine)
- `lexical-grounding-experiments.md` - long multi-round arc, 12 rounds across data growth and ship decisions
- `lexical-grounding-sota.md` - deterministic-track SOTA, no maths-heavy mechanism

## Rules
- **Reasonable, not rigid** - fit the structure to the problem the document solves; record what a reader needs to reproduce and understand, skip what does not apply; templates are a checklist to judge against, never a blank form to fill
- **Tables for sweeps** - hypothesis × lever × result; never prose where a table scans faster
- **Numbers inline** on every claim; a verdict label on every hypothesis
- **Naive baseline mandatory** - defined and described in Methodology with its numbers on every metric; every result is a delta against it; beating it is the minimum bar for a Kept / Ships verdict
- **Reproducibility** - any hypothesis owning its regime records enough to re-run FROM THE DOC ALONE, without the transcript or the code: the notebook / script / protocol that tests it (exact command / entry point and parameters), data location, operating point, the source / prior work it derives from, and provenance of any artefact used (produced here + how, or obtained externally + exact identity); a shared Setup covers only a batch where every hypothesis shares one regime
- **Source paper → invoke `datascience:papers`** - when a hypothesis derives from a paper (arXiv, DOI), download the PDF and write its structured digest into `references/papers/` (`[paper] <name>, <year>.pdf` + `[paper digest] <name>.md`); point the Experiment `source:` line at BOTH the local digest and the original URL; a cited-but-undigested paper is a defect - the digest is what a reader consults without re-fetching
- **Ask the author, don't guess their regime** - when the hypothesis is the user's and they hold the knowledge of how they mean to test it, ask for the Experiment detail you cannot verify from the repo (exact identities, parameters, materials, environment, intended notebook, prior work) rather than filling it with a plausible guess - a fabricated regime reads as recorded fact. Where the agent proposes the hypothesis or the setup is standard, fill it reasonably and move on
- **Maths** - equations liberally, never prose where a formula is exact; unicode glyphs inline for copy-paste (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`, `√(2 − 2cos)`); every full/display equation as a separated `$$…$$` block on its own line (blank line above/below) in Mechanism - these are rasterised to images for surfaces without MathJax (Medium, DOCX); never `$…$` inline in a sentence, never a standalone maths section

<!-- improved 2026-08-05 | body 2522→2059w / 97→98L | quality structure-parity vs pre-edit arm (7/7 required elements, identical section order), n=1/cell, no blinded graders, uncalibrated | trigger 4/8 held-out (description unchanged this pass; optimizer beat it in 0 of 3 iterations) | via improve-skill -->
