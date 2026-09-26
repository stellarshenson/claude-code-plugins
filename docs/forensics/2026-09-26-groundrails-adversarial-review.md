# Forensics - groundrails review turned accuracy misses into defects and overfitting rules

A four-lens adversarial review of the groundrails defect fixes (data-scientist, architect, bug-hunter, slop-hunter) ran 10 rounds on 2026-09-25 and 2026-09-26. It reported individual inputs that the deterministic regex tier misreads as MAJOR and CRITICAL findings, and proposed a special-case regex for each one. The adjudicator deferred the rest "until measured", the orchestrating session filed them as open defects, and fixing them produced rules tuned on the evaluation data. The author stopped it twice: "wait you are building overfititing into the library?" and "if 'defects' are related to failure modes - that result from data science, than we reject them; it is like saying that model failed because it scores 68%".

Evidence: session `4834cb1f-3a32-44e1-8b93-2d48ec0a36d2` of `groundrails`, workflow runs under its `subagents/workflows/`, `groundrails/.claude/JOURNAL.md` entries 144-146, `groundrails/docs/defects.md`.

## Timeline

| When (UTC) | Event |
|---|---|
| 09-25 02:46 | Review launched (shipped loop, 4 lenses). Bar purpose: "A false CONTRADICTED verdict, or a real claim silently skipped, is the worst error it can make"; inputs list every text shape |
| 09-25 02:46-05:00 | Rounds 1-7 (`wf_11646250-1f2` .. `wf_8a58ffa1-76e`); findings 16, 6, 2, 2, 4, 1, 1; SHIP. About 12 reproduced misreads deferred "until measured" |
| 09-25 05:12 | Session asks how to handle them; recommended option "File as open defects". Answered 09-26 13:58; filed as DEF-NUMBER-32..34, DEF-CLAIM-35..41 |
| 09-26 14:00-15:10 | Fixes written while reading RAGTruth and RAGBench samples, scored on the same samples (journal 145). The option text "measurements the adjudicator asked for (for example on RAGTruth)" is the session's own; the adjudicator named no corpus |
| 09-26 15:10 | Session asks how to handle "rules tuned on the evaluation data"; held-out rounds follow |
| 09-26 17:05 | Review of the held-out delta (`wf_c4e8ef92-f3b`): 23 findings, 10 MAJOR; every proposed fix is another special-case rule |
| 09-26 18:05 | Author: "wait you are building overfititing into the library?"; delta reduced to the validated core |
| 09-26 18:20 | Author's failure-mode ruling; 16 tracker items rejected, 8 of them `-1` regressions of closures the fixes had claimed |
| 09-26 18:24 | Bar rewritten: "Its deterministic tier catches obvious discrepancies cheaply"; out of scope: "heuristic accuracy on rare input shapes" |

## The review record, 10 runs

| Measure | Count |
|---|---:|
| Findings | 113 |
| Marked material | 56 |
| Remedies that edit a regex arm, lookahead or word list | 39 |
| Remedies flagged NEW MECHANISM by the reviewer | 13 |
| Remedies DEFER | 14 |
| Mentions of overfitting | 0 |
| Mentions of held-out, in-sample or pre-registration | 5 |

Typical data-scientist findings and remedies:

- "Whole-range comparison marks an abbreviated year span CONTRADICTED ('2019-2020 season' against '2019-20 season')" → "NEW MECHANISM: in `_year_span_key`, expand a two-digit right end"
- "Opening-parenthesis boundary drops or cuts a sentence after an abbreviation the shape regex misses (Ph.D., B.Sc., Mt., etc.)" → "add `etc|Mt` to its word list"
- "Kept '[A-Za-z])' arm still cuts hard-wrapped sentences at '(vitamin\nD)'" → "Narrow the kept arm to lowercase ... All four wrapped inputs stayed whole"
- Round 1 CRITICAL: "I ran this edit on a scratch copy: both repro cases clear" - each fix was verified on the counterexample that motivated it

The adjudicator judged rounds 3 and 5 "spiralling" and rounds 4 and 6 "converging", so the spiral stop, which needs two consecutive spiralling rounds, never fired.

## Root causes in this repository

1. **The bar has no notion of a statistical or heuristic component.** Materiality asks whether a user on the primary path, with an input inside the input universe, is harmed (`agents/adjudicator.md:19`, `references/loop-spec.md` invariant 8). The groundrails bar listed every input shape, so every counterexample was material. Nothing tells the reviewer that a heuristic's miss on one input is a sample of an error rate
2. **The data-scientist persona reviews experiments, not heuristic code.** Its leak axis (`adversaries/data-scientist.md:29`, "no learner scores its own fold") was never applied to hand-written rules: a rule fitted to a reviewer's counterexample and verified on it is a learner scoring its own fold
3. **The adjudicator turns deferrals into defects.** "Deferral with a written reason and a defect id is legitimate" (`agents/adjudicator.md:26`). Its new-mechanism list, "a pass, plugin, branch, helper, guard or data shape" (`agents/adjudicator.md:24`), omits a regex arm, a word-list entry and a threshold, so per-input tuning passed as `newMechanism=False`
4. **The spiral stop can be evaded by alternation.** Invariant 5 fires on two consecutive rounds judged spiralling (`references/loop-spec.md:21`); spiralling, converging, spiralling, converging never trips it
5. **The defects reference makes an accuracy miss a defect.** "A defect is one observed wrong behaviour" (`project-management/.../references/defects.md:3`); rejection covers only "never reproduced" and "functionality no longer exists" (`:46`). A failure mode of a statistical component fits the definition

## Proposed changes, for decision

- **Bar** - an optional field naming the statistical or heuristic components and their measured rate; a miss there is out of bar unless it is a crash, a regression against HEAD, or a breach of a stated guarantee
- **data-scientist persona** - an axis for heuristic and model code: a misread input is one sample of a rate; a remedy fitted to the counterexample in hand is overfitting and is reported as such; the only evidence for a rule change is a pre-registered held-out measurement with power
- **Adjudicator** - refute a heuristic's accuracy miss as a failure mode unless the bar guarantees it; a deferred failure mode gets no defect id; a new regex arm, word-list entry, threshold or special case counts as `newMechanism`
- **Spiral stop** - count spiralling rounds in a window (two of the last three), not only consecutive ones
- **Defects reference** - a failure mode of a statistical or heuristic component (a miss on an input, a score below target) is not a defect; it is measured as a rate, and a tracker entry for one is rejected with that reason
