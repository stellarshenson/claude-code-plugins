# Adjudicator replay - old against new adjudicator text (DEF-ADVR-71)

Run 2026-09-26, workflow `wf_aa37307f-f3c`, Opus 5.5, 3 runs per arm on groundrails review round `wf_c4e8ef92-f3b`. Design and outcomes in `PREREGISTRATION.md`, rulings in `results.raw`, scorer `score.py`.

## Result

The new text changes how the adjudicator rates a heuristic's miss that the change did not cause. Three runs per arm show no detectable difference in which regressions are planned.

| Outcome | Old text | New text |
|---|---:|---:|
| F11 and F17 (pre-existing misses of the abbreviation heuristic) sent to be filed as defects | 6 of 6 | 0 of 6 |
| F11 and F17 refuted as a failure mode measured as a rate | 0 of 6 | 6 of 6 |
| Refuted entries citing a rate or failure mode (pre-registered secondary) | 0 of 33 | 6 of 30 |
| Deferred entries asking to file a defect (pre-registered secondary) | 15 | 11 |
| Planned changes | 9 | 9 |
| Planned changes that add or refine a rule (hand-coded) | 1 of 9 | 1 of 9 |
| Planned changes matching the pre-registered regex | 8 | 6 |

- **Per run** - all three old runs file F11 or F17 as a defect and all three new runs refute both; Fisher exact test p = 0.10 on 3 against 3 runs, p = 0.002 on the 6 against 6 findings, which are not independent
- **Old arm** - all three runs record the word-list remedy for F11 ("move the 16 title tokens"); old-2 also rates F11 and F17 MAJOR and asks to reopen DEF-CLAIM-40 and file the title shape
- **New arm** - new-1 declines the same word-list remedy as "an unmeasured word-list change"; all three state that HEAD gives the identical output, so the miss neither regresses, crashes nor breaks a guarantee
- **Planned changes** - the old arm reverts the delta's three new rules in 8 of 9 changes, the new arm in 7 of 9: new-1 reverts the signed range end (`-?` in `_VALUE`) in place of the outline arms and defers F4. One run per arm adds a two-digit year expansion instead of removing the whole-range comparison. The original ruling refined 2 of its 3 rules; neither arm reproduced that

## Limits

- **The pre-registered primary outcome is invalid.** Its regex counts a change that names a regex arm, and a revert that removes an arm names it too; 12 of the 14 matches are reverts, and the other 2 are the year expansions. The hand-coded row replaces it; that coding was done after the results were read
- **Three runs per arm, one round, one model.** The per-run contrast is not significant at 0.05
- **The replay agents had tools** and rebuilt the reviewed tree, as the original adjudicator did; the prompts differ only in the adjudicator text and one bar line naming the heuristic components
