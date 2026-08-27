# Regression log - svg_tools CSS cascade consolidation

Raw record of every regression introduced while consolidating four partial CSS resolvers into one, across eight adversarial-review rounds. Kept for classification: each row carries the fix that caused it, the round that caught it, the lens, the pattern shape, and its measured reach.

The general lessons distilled from this log live in `plugins/devils-advocate/skills/adversarial-review/references/regression-patterns.md`. This file is the evidence; that file is the conclusion. Update both together or neither. A machine-readable mirror of the table lives in `docs/svg-cascade-regression-log.csv` - update it in the same commit as the table.

## Reading the columns

- **Caused by** - the change that introduced it, not the change that revealed it
- **Shape** - the pattern from `regression-patterns.md`: partial-conversion, half-converted-record, borrowed-default, sibling-left-behind, nth-weaker-copy, no-consumer
- **Reach** - measured, on the 71-file `plugins/svg-infographics/examples/` corpus at the time it was found. `latent` means the mechanism is real and no current file triggers it
- **Caught by** - which lens, and whether a repo test would have caught it independently

## The log

| # | Regression | Caused by | Shape | Reach | Caught by | Status |
|---|---|---|---|---|---|---|
| R1 | Unresolvable text fill scored as `#000000` | pre-existing | no-consumer | 16 texts / 2 files | round 1, all three | fixed |
| R2 | UNMEASURABLE hints emitted into a channel the gate discards | R1's fix | no-consumer | 63 real findings → 0 on one file | round 2, all three | fixed |
| R3 | Background fill still read off the attribute after text fill was converted | R1's fix | partial-conversion | 10.64:1 reported vs 1.08:1 real | round 2 architect | fixed |
| R4 | `fill` not inherited from an ancestor `<g fill=…>` | pre-existing, exposed by R3's fix | sibling-left-behind | 15 of 48 texts on one file | round 2 bug-hunter | fixed |
| R5 | Dark row scored against the *light* plate | R3's fix | half-converted-record | universal once backgrounds resolved | round 2 self-caught | fixed |
| R6 | `fill-opacity` read off the attribute while `fill` went through the cascade | R3's fix | sibling-left-behind | +230 corpus findings, all false | round 2 self-caught | fixed |
| R7 | 4-digit hex `#3a4c` crashed the layer through newly-reachable paths | R1's fix widening the cascade | nth-weaker-copy | latent | round 2 bug-hunter | fixed |
| R8 | `is_displaced` discarded, decorations elected at raw coordinates | R3's fix | partial-conversion | 17 false HARD / 6 files | round 3 bug-hunter | fixed |
| R9 | `stroke-opacity` defaulting to the fill's, `stroke-width` to `0.0` | R6's fix, adjacent lines | borrowed-default | 149 + 226 shapes | round 3 bug-hunter | fixed |
| R10 | `_cascade_opacity` re-implementing `_resolved_opacity` more weakly | R6's fix | nth-weaker-copy | false PASS in HARD tier | round 3 architect | fixed |
| R11 | `merged_rules` clobbering the `@seq` source-order map | R2-era `merged_rules` | half-converted-record | 128 offsets / 447 selectors, latent | round 3 architect | fixed |
| R12 | `_resolved_opacity` ignoring ancestor opacity while `find_backplate` folded it in | R10's fix | partial-conversion | 11.53:1 reported vs 1.05:1 real | round 3 architect | fixed |
| R13 | Displaced text scored against a fabricated document ground | R8's fix | borrowed-default | 15 false HARD / 1 file | round 3 bug-hunter | fixed |
| R14 | Phantom dark stroke on strokeless shapes | R9's fix removing the guard that hid it | borrowed-default | 2 dark rows, latent | round 3 bug-hunter | fixed |
| R15 | Connector tri-state firing only at zero parsed | R13-era tri-state | partial-conversion | 8 green rows on 1 of 10 arrows | round 3 UX | fixed |
| R16 | Tri-state probe ignoring `<path>`, the house connector format | R15's fix | sibling-left-behind | latent | round 3 UX + round 4 architect | fixed |
| R17 | Tri-state keyed on any transformed ancestor, firing on icon glyphs | R15's fix | partial-conversion | false SKIP on 3 of 4 files | round 3 UX | fixed |
| R18 | `_font_size` compounding `em`/`%` once per generation | R-font fix (round 3) | partial-conversion | 26 texts / 2 files, inverted a HARD verdict | round 4, all three | fixed |
| R19 | `!important` ranking unreachable behind the inline-style early return | R-important fix (round 3) | no-consumer | latent, plus a comment asserting it worked | round 4 architect | fixed (2nd attempt) |
| R20 | `_resolved_opacity` rebuilding the parent map per call | R12's fix | nth-weaker-copy | 1.17 ms/shape; two 70k files never completed | round 4 architect | fixed, 29x |
| R21 | Text branch never given the guards its three siblings got | R8's fix | partial-conversion | latent | round 4, all three | fixed |
| R22 | `_merge_paired_shapes` dropping `dark_fill`/`dark_stroke` | R5's fix | half-converted-record | 223 dark rows | round 4 architect | fixed |
| R23 | Tri-state comparing a *named* count against a *total parsed* count | R15's fix | partial-conversion | latent, cheap to trigger | round 4 UX + bug-hunter | fixed |
| R24 | `displaced` shapes exempted from SIZE filters to fix a POSITION problem | R8's fix | partial-conversion | 829 decorative shapes as failures | round 4 bug-hunter | fixed |
| R25 | Large-text threshold in px (18/14) where WCAG specifies pt (24/18.66) | pre-existing, exposed by R18's fix | borrowed-default | 31 rows / 3 files pass at 3.0, fail at 4.5 | round 5 UX | fixed |
| R26 | `find_backplate` still rebuilding the parent map per rect - R20's fix stopped one caller short | R20's fix | partial-conversion | 66x on 10k elements; runs twice per gate | round 5 architect + bug-hunter | fixed |
| R27 | `Shape` resolved for dark colour but not dark alpha; `Background` got both | dark-field lineage (R5/R22 fixes) | half-converted-record | 265/4256 pairs differ, 0 flips today; probe shows false HARD | round 5 architect | fixed |
| R28 | `theme_paint` ranks declarations from different elements; second dark model beside `merged_rules` | theme_paint introduction | nth-weaker-copy | 16 elements / 2 files, right answer only by parser accident | round 5 architect + bug-hunter | fixed |
| R29 | Unreadable dark text paint yields no row - doctrine applied to background, not text | dark-unreadable work | partial-conversion | reproduced on probes; corpus reach unmeasured | round 5 bug-hunter | fixed |
| R30 | Dark `fill:none` reported as "a value this checker cannot read" - false HARD | dark-unreadable work | borrowed-default | 0 corpus | round 5 bug-hunter | fixed |
| R31 | `_ancestor_opacity` reads the attribute only; class-declared group opacity invisible | R12's fix | sibling-left-behind | 95 class-opacity containers, 0 elections flip | round 5 bug-hunter | fixed |
| R32 | `!important` branch breaks ties by attribute order, not source order | R19's fix | nth-weaker-copy | 0 corpus | round 5 architect + bug-hunter | fixed |
| R33 | Two comments assert the reverted R24 exemption; `Shape.displaced` written, never read | R24's fix | half-converted-record | comments, not code | round 5 bug-hunter | fixed |
| R34 | `_SEQ` offsets in two coordinate spaces (light spliced, dark original); first dark rule demoted to offset 0 | R28's fix making cross-map comparison live | borrowed-default | 0/71 corpus; wrong tie-break in the HARD-tier resolver | round 6 architect + bug-hunter | fixed |
| R35 | Arrowhead rows can never SKIP: only `connectors` got the tri-state, `arrowheads` stayed boolean | R-polygon fix (round 6) | partial-conversion | `head points into the card` PASS over 9 unjudged heads | round 6 UX | fixed |
| R36 | Findings branch (acked SOFT, no HARD) exits 0 over unasked SKIPs; only the zero-findings branch consults the roster | clean-branch verdict fix (round 6) | partial-conversion | `shippable` + exit 0 over 9 unjudged aspects | round 6 UX | fixed |
| R37 | Dark parse runs a quadratic regex over the full-length blanked string, unconditionally | dark-sheet one-pass parse (campaign) | nth-weaker-copy | 3s on a 20KB single-theme deck; 0/71 today | round 6 bug-hunter | fixed |
| R38 | `display:none` compared case-sensitively in the new style-spelling branch | R-display fix (round 6) | borrowed-default | 0 corpus; inconsistent with check_connectors | round 6 bug-hunter | fixed |
| R39 | `display:none !important` hid from connectors, rendered in check_css - invisible glyphs fired HARD contrast and forbidden-color | R38's fix, one spelling further down the same axis | partial-conversion | 0/71 corpus; reproduced through the finalize gate (2 HARD) | round 7 bug-hunter + architect | fixed |
| R40 | `merged_rules` same-selector dark landing never consulted the `_SEQ` offsets R34 repaired; a later light redeclaration lost the tie it wins in a browser | R34's fix, applied to cross-selector ties only | partial-conversion | 0/71 corpus; wrong dark answer in the HARD-tier resolver | round 7 architect | fixed |
| R41 | JSON `skipped` key emitted `{}` on the HARD path - "not consulted" indistinguishable from "nothing unjudged" | R36's fix building the map only on the SOFT path | half-converted-record | every HARD-path `--json` run | round 7 UX | fixed |
| R42 | Clean-branch `--json` omitted `totals`; a consumer's `data["totals"]` KeyErrors on exactly the green path | clean-branch verdict fix (round 6) | sibling-left-behind | every clean `--json` run | round 7 UX | fixed |
| R43 | Mixed multi-file findings branch printed no verdict line for the healthy file - silence read as also-unverified | R36's fix (round 6) | sibling-left-behind | every mixed acked run | round 7 UX | fixed |
| R44 | `_UNKNOWN_NOTE["labels"]`/`["cards"]` unreachable - those inventory keys are never `None` | `_UNKNOWN_NOTE` introduction (round 6) | no-consumer | dead weight; the message text was wrong for those keys | round 7 architect | fixed |
| R45 | `merged_rules` landing guard compared source order without the importance precondition - an early dark `!important` lost to a later light normal | R40's fix (round 7) | borrowed-default | 0/71 corpus (needs a post-media redeclaration AND an importance asymmetry) | self-audit before the round-8 freeze | fixed |
| R46 | `check_overlaps` hidden-subtree predicate still on the substring semantics after R39 converted the other two - a `*-display:none` custom property silently dropped visible subtrees from the HARD-tier overlaps model | R39's fix (round 7); the census missed the third consumer | partial-conversion | 0/71 corpus; silent false negatives in the HARD tier | round 8 architect | fixed |
| R47 | HARD path withheld the unjudged aspects from the human surface - the JSON gained the `skipped` map, stderr kept `N hard, M soft`; the operator met the skips one gate cycle after the re-run-ONCE promise | R41's fix (round 7) | sibling-left-behind | every HARD run with parser skips | round 8 UX | fixed |
| R48 | OK verdict line added to the mixed branch only - the uniform acked run (the commonest acked state) got the next: guidance and no verdict | the C5 fix (round 7) | partial-conversion | every uniform acked run | round 8 UX | fixed |

## The freeze mechanism (md5 pinning)

Rounds 2 and 3 were partly invalidated by edits landing while a lens was still reading the tree - the reviewer and the author were never looking at the same bytes, so a finding could name a defect that had already moved and a closure could be claimed against a diff the reviewer never saw. From round 4 the files under review are frozen for the duration of a round: their `md5sum` hashes are written into each reviewer prompt with the instruction to re-hash before starting and again before returning, and to report both pairs.

- **Cost** - one `md5sum` line per round, pasted into the prompt
- **Effect** - every lens in rounds 4 and 5 verified unchanged hashes at both ends; closures are by reproduction against a known state, and a DO-NOT-SHIP verdict names a defect that still exists
- **Adopted as standard** for any multi-lens round; the prompting recipe lives in `regression-patterns.md` under "Prompting a confirming round"

## What the log says

- **42 of 48 were introduced by a fix**, not by the original code. Six were pre-existing and merely exposed - the sixth (R25) surfaced when a correct font-size resolver removed the wrong value that had been keeping a misread WCAG threshold dormant.
- **partial-conversion is the dominant shape** - 17 of 48. One caller of a shared mechanism converted, its siblings left reading the same document differently. It recurred in the same file, one branch at a time, eight rounds running - round 5 produced its purest form (R26 is R20's own fix, applied at six of seven call sites), round 7 produced two more inside round-6 fixes, and round 8 found the census itself incomplete: R39 converted two hidden-subtree predicates while a third sat one module over (R46), and the OK verdict line landed in the mixed branch but not the uniform one (R48).
- **Each round's findings land in the previous round's new surface.** Deduped counts: 17 (round 5) → 5 (round 6) → 6 (round 7) → 3 (round 8), every one tracing to a recent fix. Severity decays with the count (CRITICALs with corpus reach → MINORs and latent machinery). The loop was capped after round 8 by the Star Colonel under the doctrine that the gate is a sanity validator, not the quality bar - the cap is recorded here because it, not a clean round, ended the loop.
- **Regressions in comments survive longer than regressions in code.** R19 shipped a constant that never fired beside a comment describing the scenario it fixed; one fix carried `# HARD via the caller` where no such caller existed; R24's fix reverted the code but left two comments asserting the reverted behaviour (R33). Reviewers read a false comment as specification.
- **Latent is not harmless.** 22 of 48 had zero live reach when found. They were still fixed, because "no current file triggers it" is a property of the corpus, not the code.
- **The freeze mattered.** Rounds 2 and 3 were partly invalidated by edits landing mid-review; from round 4 the md5 mechanism above pinned the reviewed state and every lens verified it at both ends. It is the one process change that measurably improved signal.
- **The graph makes "is anything left unconverted?" a deterministic question.** Round 8 primed each lens with the code graph (`tmp/graphify-out`, refreshed against the frozen bytes); the R46 census - three hidden-subtree predicates, two converted - was cross-checked against it, and grep alone answers that question only when the search spelling is exact.
- **Cross-lens agreement is the strongest confirmation signal the loop has produced.** Round 5: architect and bug-hunter independently returned R26, R28 and R32 with the same remedy, from different lenses, on the frozen tree. Round 7 repeated it: bug-hunter and architect landed on the same `display:none` divergence from different spellings. A finding one lens makes could be taste; the same finding from two lenses is a defect.
- **The log predicted its own rows, five times now.** R26 is partial-conversion recurring inside the fix for R20; R39 and R40 recurred inside the round-6 fixes for R38 and R34; R46 and R48 recurred inside round-7 fixes. Once a shape is named, the next fix in the same file should be audited against it before the review round finds it - R45 shows the audit working: the one round-8-campaign defect caught BEFORE the lenses ran.
- **Self-caught is rare** - 3 of 48 (R5, R6, R45). The rest needed an independent lens, which is the argument for the review loop existing at all.

## Classification hooks for later

Rows are ready to group by: shape; caused-by-fix vs pre-existing; latent vs live; caught-by-lens; and rounds-to-detection (R11 and R21 each survived two rounds). The CSV mirror (`docs/svg-cascade-regression-log.csv`) exists for exactly this pivoting. The one dimension not captured here is time-to-fix, which was not measured.
