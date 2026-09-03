# Ledger queries and appends - `hypothesis-tools`

CLI over a canonical experiments log, so an agent answers "what is taken, what won, what does H33 say, what did DR read across the rounds" from a parse instead of re-reading the file - a real ledger runs to 6,400 lines. Ships with `stellars-claude-code-plugins`; the skill's toolchain gate installs and version-checks it. Writes are append-only, mirroring the ledger's own discipline: nothing rewrites recorded text, a recorded Result and Verdict are immutable.

## Read commands

- **`hypothesis-tools next-id <log> [--json]`** - the next free global `H<n>` and the next `E<batch>`, plus the current hypothesis and batch counts
- **`hypothesis-tools list <log> [--verdict V] [--batch E12] [--author @xx] [--locked] [--locked-by @xx] [--json]`** - one row per hypothesis (id, slug, shape, verdict) and a verdict tally; `--verdict` matches one label case-insensitively (`Refuted` does not return `Refuted (null)`), takes the ledger's own grown labels, and `none` returns the unverdicted; `--author` matches the handle that registered it; `--locked` keeps the hypotheses carrying an active lock, `--locked-by` narrows to one holder
- **`hypothesis-tools show <log> <id> [--json]`** - the hypothesis's markdown verbatim (extent under *What counts as a declaration*); accepts `E12-H33` or the bare ordinal `33`, which is unambiguous because `<n>` is global
- **`hypothesis-tools report <log> [--json]`** - one paste-ready table, batches down and verdict labels across, canonical labels first then the ledger's own by frequency (capped at 8 columns, the tail folds into `other`), `unverdicted` last, with a Total row
- **`hypothesis-tools values <log> <quantity> [--batch B] [--id ID] [--json]`** - every reading of one measured quantity (`DR`, `gold_full`, `theta`, `pop residual`) across the declared blocks: id, value, line, context. Reads `` `DR` 0.2286 ``, `theta(0.08) = 0.7644`, `pop residual < 0.58%`, backticked or bolded names and values alike. The match is textual on purpose - the context column makes a false hit visible instead of silently averaged into an answer
- **`hypothesis-tools check <log>`** - validate; exit 1 on any error, 0 with warnings

`list`, `show`, `report` and `values` take `--json` and emit structured records; `next-id --json` emits `{next_h, next_batch, hypotheses, batches}`; `check` has no `--json`.

**`list`, `show` and `report` name the hypotheses in flight first.** Whenever a hypothesis they are about to show carries an active lock, one stderr line precedes the table: `N hypothesis(es) currently worked on: E14-H42 by @kj until 2026-09-03T10:11:29Z, ...` - ten ids at most, then `+M more`. The choice of what to pick up happens while reading, so the signal goes there; stderr keeps a piped table clean and `--json` prints no notice, carrying `lock` as `{by, until, note}` or `null` on each record instead.

**`next-id` refuses rather than guesses.** An unclosed code fence, or any id-shaped token sitting in a declaration position that did not parse, exits 1 with the line - because a wrong answer here silently burns an ordinal twice, and the skill says that has to be undone later. `register` refuses on the same grounds, because it is the write that allocates an ordinal; the other writes name a hypothesis that already exists and do not.

## Write commands

Every write but `author` takes `--author @xx` and refuses without one. The handle must already be on the `## Authors` roster, and each such write appends its own dated `log:` line naming it - who recorded a result, a verdict or a field is not recoverable after the fact from anything else.

- **`hypothesis-tools author <log> --handle @xx --name "Full Name"`** - add or update one roster entry, creating the `## Authors` section under the overview and above the first round. The handle is the `project-management` toolkit's: `@` plus 2-4 lowercase characters, so one handle is one person across a project's ledgers, criteria and defects
- **`hypothesis-tools register <log> --slug S [--field NAME=VALUE ...] [--batch E13 | --new-batch [--batch-slug S]] --author @xx [--json]`** - append a pre-registered hypothesis at the next free ordinal. Fields are free-form; Hypothesis / Lever / Mechanism / Prediction / Acceptance bar / Pre-experiment / Experiment render in canonical order, any other name follows as given. `Result`, `Verdict` and `Log` are refused - a registration precedes its outcome. Default batch is the ledger's latest; `--new-batch` opens the next token and writes its `##` heading. The block is verified to parse back before the file is touched
- **`hypothesis-tools result <log> <id> --text T [--qualifier Q] --author @xx`** - append the Result bullet, placed before Verdict/Log. A recorded Result is immutable: a second reading (re-run, another phase) needs `--qualifier`, which renders as `- **Result (Q)** - ...`, the shape long ledgers already use
- **`hypothesis-tools verdict <log> <id> --text "Label; number" --author @xx`** - record the one verdict. A second is refused: a flip is a new round with a back-reference. The label must open the text; a non-canonical label records with a note
- **`hypothesis-tools field <log> <id> --name N --text V [--update] --author @xx`** - add one field, placed before Result/Verdict/Log so the block reads declaration, measurement, judgment. Any name the research needs: the five real ledgers carry hundreds of their own (`Grounding`, `Persona`, `Status`, `Vet`). A name already recorded needs `--update`, which replaces the value and keeps the label and its qualifier untouched. `Result`, `Verdict` and `Log` are refused - each has its own command and its own immutability rule
- **`hypothesis-tools log-event <log> <id> --event E [--date YYYY-MM-DD] --author @xx`** - append one dated `log:` line under the hypothesis's Log, creating the `- **Log**` bullet at block end when absent; newest lands last
- **`hypothesis-tools lock <log> <id> --author @xx [--hours N | --until STAMP] [--note TEXT]`** - write `- lock: <ISO 8601 UTC stamp> @xx [note]` as the block's first bullet: @xx is likely working on this until the stamp, 24 hours from now by default. Locking again as the same author extends it (the line is replaced); refused on a hypothesis that carries a Verdict, because a verdict closes it and a flip is a new round
- **`hypothesis-tools unlock <log> [<id> | --all | --expired] --author @xx`** - remove lock lines: one hypothesis, every one in the ledger, or only those whose stamp is past; exactly one selector

Writes land only on a full-block hypothesis - a table row or compact bullet cannot take appended fields; give it a `### id slug` block first (the tool says so). `register` therefore always writes a full block.

**A lock is a courtesy signal, never a gate** - the `project-management` toolkit's discipline, unchanged. Lock a hypothesis when you pick it up, before its first write, and unlock when you stop; ask the holder before working on one somebody else holds. What the tool does with it:

- **A write by another author warns once and lands** - `result`, `field` and `log-event` on a hypothesis locked by a different handle print `<log>:<line>: E14-H42 locked by @yy until <stamp> - someone is likely working on it; ask before continuing` on stderr and proceed; exit code and file result are those of the unlocked case
- **Expired locks clear themselves** - every write first removes the lock lines whose stamp is past, silently and unlogged; `verdict` removes the hypothesis's lock whatever its expiry, since the verdict closes it
- **Taking or clearing someone else's active lock is a transfer** - `lock` and `unlock` print `TRANSFER: E14-H42 was locked by @yy until <stamp> - you are taking it over; ask @yy` (or `you are clearing it`) and proceed; a takeover with no `--note` records `taken over from @yy` on the new line, so the previous holder stays visible on the block
- **Locking is never logged** - the lock line carries its own stamp and author, and it is meant to disappear; a `log:` line would outlive the lock it records
- **The note is one line** - `lock` verifies the line reads back as written before touching the file and refuses a note that breaks the shape

## What counts as a declaration

Three shapes in the wild parse, and a hypothesis's batch comes from its **id**, never from the section heading - real headings vary (`## E12 - slug` in one log, `## Contradiction features, bundle E1: slug` in another).

- **Full-block** - `### E12-H33 slug` followed by `- **Field** - value` bullets; fields, verdict and block all parse. The id comes first after the hashes, bolded or bare
- **Compact** - `- **E1-H1 slug** - prose`; id and slug parse, `verdict` is `null`. Any CommonMark bullet marker works (`-`, `*`, `+`), and the id opens the bold label
- **Table row** - a row whose first cell is exactly one id, in a table whose header names hypothesis columns (claim / hypothesis / verdict / status / evidence / result / prediction); those columns map to fields, so `| E14-H46 | no single lever reverses | -50% | SUPPORTED |` declares with its verdict. A timing or benchmarks table (`| id | ms/pair |`) maps to nothing and its rows stay citations - it can never mint a phantom. `\|` inside a cell is an escaped pipe, not a delimiter, so a formula cell does not shift the verdict column
- **A block ends at the next declaration** - of any depth, so a nested hypothesis never donates its fields upward and `show` never bleeds into the next one
- **A full block outranks a table row or one-line mention** - a summary above the rounds does not get to be the declaration; otherwise the tally reads the marketing line instead of the record
- **A bold label naming two ids declares neither** - `- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair` is a timing row. A parenthetical is exempt, because the skill mandates a supersede back-reference: `- **R30-H106 global-cut (supersedes R9-H21)**` still declares
- **Fenced code is skipped** - a documented example inside ``` never parses as a real hypothesis; a fence closes only on the same character at the same run length or longer
- **A field qualifier is kept** - `- **Result** (k=1) - DR 0.180` and `- **Result (engine replay, 2026-07-11)** - ...` are both Results; the parenthetical belongs to the value or the label, never changes the field's identity
- **A near-miss declaration is reported, not dropped** - an id the parser could not read is an error with its line whenever it sits in a bullet's bold label, opens a bullet (bolded or not), or opens a heading, setext line or hypothesis-table row. An id anywhere else on the line - in a field value, in a round heading's prose - is a citation and stays clean

## How verdicts are read

The Verdict bullet is `<label>; <justifying number>` - and real ledgers write the label bolded (`**PARTIAL**`), uppercase (`REFUTED`), behind a dated qualifier (`(2026-07-12) Confirmed; ...`), or with hyphen and space swapped (`Killed at gate`). All of those read.

- **Canonical labels normalize** - `REFUTED`, `**Refuted**` and `Refuted (killed at gate)` all report `Refuted`; the canonical set and its spelling live in `per-hypothesis-template.md`
- **The vocabulary is open** - a short word-like head (`SUPPORTED`, `PARTIAL`, `Inconclusive`) is a label as written; `check` warns once, aggregated, so a ledger-grown vocabulary is visible without burying real errors
- **A canonical label followed by scoping prose is that label** - `Refuted on the replacement bar;` and `**Refuted** as an order measure (applicability: Low) - ...` read as Refuted, exactly as `Refuted (killed at gate)` does; a next clause opening with another label (`Refuted for k=1, Confirmed for k=3`, `Refuted for bf16, kept for the recipe`) makes it a regime, and a regime reads as no label
- **No label is still no label** - a narrative verdict (`Refuted for k=1, Confirmed for k=3`, `pending final ... but leaning REFUTED`) reads as none and `check` errors: reading it would be guessing, and a mixed regime has no single label
- **Compact hypotheses report no verdict** - the verdict is narrative in that shape ("the features were initially killed" is a story about a fix, not a Killed verdict). Absent beats wrong: `check` counts them in one warning, `show` returns the line so a reader decides

## Check rules

Errors (exit 1) are unambiguous defects; warnings are shapes the skill permits but that cost a reader something. The template is a checklist to judge against, never a blank form, so a missing optional field is never an error.

| level | rule |
|---|---|
| error | an id-shaped token in a declaration position that did not parse - the silent-drop guard |
| error | a code fence that is never closed, hiding every hypothesis below it |
| error | the same id declared twice by a full block - the second is ignored |
| error | two hypotheses claim the same `H<n>` - the ordinal is global and never reset |
| error | a `Verdict` bullet carrying no readable label at all |
| error | a `log:` line naming a handle that is not on the `## Authors` roster, aggregated per handle - a handle nobody is rostered for is a typo, and a typo credits a researcher who does not exist |
| error | a `lock:` line that does not read as `- lock: <ISO 8601 UTC stamp> @xx [note]`, or a second lock line on one hypothesis - the holder or the expiry is unreadable |
| warning | non-canonical verdict labels, aggregated with counts - a grown vocabulary is legitimate but drifts |
| warning | an expired lock (`check` is read-only; the next write clears it), or a lock on a hypothesis that carries a Verdict - a verdict closes the hypothesis, so unlock it |
| warning | `log:` lines carrying no `@handle`, in one aggregated count - the ledgers predate the roster and their history is legitimate; every CLI write records its author |
| warning | no `**Canonical Experiments Document**` marker - this may not be the canonical log |
| warning | how many compact and table-declared hypotheses there are - readable, but not the full field set |
| warning | full-block hypotheses missing Hypothesis, Lever, Mechanism, Prediction, Acceptance bar, Result or Verdict - one line per field naming the ids, never one per hypothesis; an empty bullet counts as missing |
| count | unrun - a full block with neither Result nor Verdict; the summary line carries the count (`11 unrun`) and no warning fires, because register, sign off, then execute is the designed order |

`Experiment` is not required - a one-toggle batch on a shared Setup carries reproducibility at the document level. `Pre-experiment` and `Log` are optional by the template. A field name the template does not list is never flagged at all: the four real ledgers carry hundreds of them, and a warning per unknown name would bury every real finding.

## Worked calls

```bash
hypothesis-tools author docs/experiments/grounding-experiments.md --handle @kj --name "Konrad Jelen"
# @kj roster created; roster: @kj      (once per ledger, before the first write)

hypothesis-tools next-id docs/experiments/grounding-experiments.md
# next_h: H42 / next_batch: E14 / in ledger: 9 hypotheses across 2 batches

hypothesis-tools register docs/experiments/grounding-experiments.md --author @kj \
    --new-batch --batch-slug "gate levers" --slug gate-cheap-kill \
    --field "Hypothesis=because the gate is cheap, killing early saves the run" \
    --field "Lever=gate threshold" \
    --field "Mechanism=a cheap gate rejects early, before the expensive stage runs" \
    --field "Prediction=kill rate >= 30%" \
    --field "Acceptance bar=kill rate >= 30% AND zero false kills on the control" \
    --field "Persona=contrarian"
# registered E14-H42 at line 312 by @kj

hypothesis-tools lock    docs/experiments/grounding-experiments.md E14-H42 --author @kj --note "running the sweep"
# docs/experiments/grounding-experiments.md:313: E14-H42 locked by @kj until 2026-09-03T10:11:29Z   (24 hours; --hours 4 or --until STAMP for another span)

hypothesis-tools result  docs/experiments/grounding-experiments.md E14-H42 --author @kj --text "kill rate 41%, control clean"
hypothesis-tools verdict docs/experiments/grounding-experiments.md E14-H42 --author @kj --text "Confirmed; 41% >= 30%, control clean"
hypothesis-tools field   docs/experiments/grounding-experiments.md E14-H42 --author @kj --name Grounding --text "SOTA: the cheap-gate line"
hypothesis-tools log-event docs/experiments/grounding-experiments.md E14-H42 --author @kj --event "re-ran at n=2x, holds"
# verdict cleared the lock; a hypothesis put down before its verdict is released by hand:
hypothesis-tools unlock  docs/experiments/grounding-experiments.md E14-H42 --author @kj

hypothesis-tools report docs/experiments/grounding-experiments.md
hypothesis-tools values docs/experiments/grounding-experiments.md "kill rate"
hypothesis-tools check  docs/experiments/grounding-experiments.md
# OK: 10 hypotheses, no errors, 0 warnings
```
