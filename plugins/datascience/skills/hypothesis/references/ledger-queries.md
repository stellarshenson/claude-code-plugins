# Ledger queries - `hypothesis-tools`

Read-only CLI over a canonical experiments log, so an agent answers "what is taken, what won, what does H33 say" from a parse instead of re-reading the file. Ships with `stellars-claude-code-plugins`; the skill's toolchain gate installs and version-checks it. It never writes - appends stay Edit's job, because the log is append-only and a recorded verdict is immutable.

## Commands

- **`hypothesis-tools next-id <log> [--json]`** - the next free global `H<n>` and the next `E<batch>`, plus the current hypothesis and batch counts
- **`hypothesis-tools list <log> [--verdict V] [--batch E12] [--json]`** - one row per hypothesis (id, slug, shape, verdict) and a verdict tally; `--verdict` matches the label exactly, so `Refuted` does not return `Refuted (null)`; `--verdict none` returns the unverdicted
- **`hypothesis-tools show <log> <id> [--json]`** - the hypothesis's markdown verbatim (extent under *What counts as a declaration*); accepts `E12-H33` or the bare ordinal `33`, which is unambiguous because `<n>` is global
- **`hypothesis-tools check <log>`** - validate; exit 1 on any error, 0 with warnings

`list` and `show` take `--json` and emit structured records (`id`, `batch`, `ordinal`, `slug`, `shape`, `line`, `verdict`, `fields`); `next-id --json` emits `{next_h, next_batch, hypotheses, batches}`; `check` has no `--json`.

**`next-id` refuses rather than guesses.** An unclosed code fence, or any id-shaped token sitting in a declaration position that did not parse, exits 1 with the line - because a wrong answer here silently burns an ordinal twice, and the skill says that has to be undone later.

## What counts as a declaration

Both shapes in the wild parse, and a hypothesis's batch comes from its **id**, never from the section heading - real headings vary (`## E12 - slug` in one log, `## Contradiction features, bundle E1: slug` in another).

- **Full-block** - `### E12-H33 slug` followed by `- **Field** - value` bullets; fields, verdict and block all parse. The id comes first after the hashes, bolded or bare
- **Compact** - `- **E1-H1 slug** - prose`; id and slug parse, `verdict` is `null`. Any CommonMark bullet marker works (`-`, `*`, `+`), and the id opens the bold label
- **A block ends at the next declaration** - of any depth, so a nested hypothesis never donates its fields upward and `show` never bleeds into the next one
- **A full block outranks an earlier one-line mention** - a summary bullet above the rounds does not get to be the declaration; otherwise the tally reads the marketing line instead of the record
- **A bold label naming two ids declares neither** - `- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair` is a timing row. A parenthetical is exempt, because the skill mandates a supersede back-reference: `- **R30-H106 global-cut (supersedes R9-H21)**` still declares
- **Fenced code is skipped** - a documented example inside ``` never parses as a real hypothesis; a fence closes only on the same character at the same run length or longer
- **A field qualifier outside the bold span is kept** - `- **Result** (k=1) - DR 0.180` is a Result whose value opens with `(k=1)`; on `Verdict` the label is read after it
- **A near-miss declaration is reported, not dropped** - an id the parser could not read is an error with its line whenever it sits in a bullet's bold label, opens a bullet (bolded or not), or opens a heading or setext line, through any list marker, checkbox or blockquote prefix. An id anywhere else on the line - in a field value, in a round heading's prose - is a citation and stays clean, because the skill mandates a supersede back-reference

## Why compact hypotheses report no verdict

The verdict is narrative in that shape ("shipped", "**null**", "the features were initially killed"). Inferring one by regex returns a confident wrong label - that last phrase is a story about a fix that was then repaired, not a Killed verdict. Absent beats wrong: `check` reports it as a warning, and `show` returns the line so a reader decides.

Making a compact log fully machine-readable is a format change, not a tool change - it would mean ending each one-liner with a bold verdict token. Not required today.

## Check rules

Errors (exit 1) are unambiguous defects; warnings are shapes the skill permits but that cost a reader something. The template is a checklist to judge against, never a blank form, so a missing optional field is never an error.

| level | rule |
|---|---|
| error | an id-shaped token in a declaration position that did not parse - the silent-drop guard |
| error | a code fence that is never closed, hiding every hypothesis below it |
| error | the same id declared twice by a full block - the second is ignored |
| error | two hypotheses claim the same `H<n>` - the ordinal is global and never reset |
| error | a `Verdict` label outside the set in `per-hypothesis-template.md` |
| warning | no `**Canonical Experiments Document**` marker - this may not be the canonical log |
| warning | how many compact hypotheses there are, so their verdicts are known to be unread - one line, not one per hypothesis |
| warning | a full-block hypothesis missing Hypothesis, Lever, Mechanism, Prediction, Acceptance bar, Result or Verdict; an empty bullet counts as missing |

`Experiment` is not required - a one-toggle batch on a shared Setup carries reproducibility at the document level. `Pre-experiment` and `Log` are optional by the template.

## Worked calls

```bash
hypothesis-tools next-id docs/experiments/grounding-experiments.md
# next_h: H42
# next_batch: E14
# in ledger: 9 hypotheses across 2 batches

hypothesis-tools list docs/experiments/grounding-experiments.md --verdict Refuted
hypothesis-tools show docs/experiments/grounding-experiments.md E12-H33
hypothesis-tools check docs/experiments/grounding-experiments.md
# OK: 9 hypotheses, no errors, 0 warnings
```
