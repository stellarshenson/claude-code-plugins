# Defects

A defect is one observed wrong behaviour plus the trail of what has been tried against it. The store is `docs/defects-<project>.md`, ids are `DEF-<CAT>-<N>`. Shared format, ids, relations and tooling live in `SKILL.md`; this file carries only what is specific to defects.

## Writing a defect

The body is one dense line: symptom, then cause, then fix, then the file.

```
- [ ] `DEF-<CAT>-<N>` **<title>** - <SEVERITY>; <symptom>; cause <...>; fix <...>; `<file>`
```

- **Symptom first, in the reporter's terms** - what was seen, not what was theorised
- **`cause under investigation`** is a legitimate value until it is not
- **Severity is the first word of the body** and it is never omitted - `CRITICAL` / `MAJOR` / `MEDIUM` / `MINOR`, see Triage below
- **No investigation dumps in the line** - depth goes to a details doc, see below
- **An area is a category, not a file** - components and symptom classes are `##` sections inside the one master list

## Triage

Every defect carries a severity. There is no unset: `add` refuses a defect without one and `check` errors on any that lacks it.

**You assign it, at the moment you file the defect.** Read it off the symptom, on the worst plausible reading a reporter would recognise. Never ask the user for the level and never leave it for later - a wrong level costs one `edit --severity`, an absent one blocks the gate.

If the symptom itself is unclear - you cannot tell what breaks, or for whom - that is not a triage question but a defect question, and you ask it.

- **CRITICAL** - data loss, a security hole, or the product unusable with no workaround
- **MAJOR** - a core path broken; a workaround exists but costs the user real effort
- **MEDIUM** - a non-core path wrong, or a core path wrong only in an edge case
- **MINOR** - cosmetic, or noticed only by someone looking for it

The level is the first word of the body - `MAJOR; <symptom>...`. `report` reads it back and spreads it across the SUMMARY columns, so it must be one of those four words and nothing else.

## The log is the point

Every event gets a dated line and nothing is ever rewritten or deleted.

- `reported` - what was seen, quoted from the reporter where possible
- `attempted` - **including the attempts that failed, and why they failed**. The record of what has already been ruled out is the reason the file exists
- `reopened` - with the trigger that brought it back
- `fixed` or `resolved` - what actually landed, plus the evidence (test counts, review verdict)

`wontfix` on a real, reproducible defect is a **close** with the reason - it was a defect, and the decision is not to fix it.

A defect that turned out not to be a defect is **rejected**, not closed: `reject` marks it `[-]` and records why. The two cases: it never reproduced, or the functionality it broke no longer exists. Rejecting keeps the trail, so the same report does not come back next quarter as news. Criteria reject for their own reason, in `acceptance-criteria.md`.

## Categories

One `##` per component, subsystem or symptom class, code declared on the heading. Never a heading per defect - ids are inline references, never anchors.

```markdown
## Launch `LNCH`

Cold start, splash screen and the first turn after a fork

- [x] `DEF-LNCH-1` **branch name not applied at launch, false "use /rename" warning** - MEDIUM; panel warned `name "..." could not be applied` yet a manual `/rename` worked; cause: the obsolete `sessions/set-title` poll 404'd for 30s on the not-yet-written fork file and fired a false failure; fix: removed the set-title path; `src/widget.ts`
  - repro: fork a session, watch the panel for 30s
  - test-tags: unit, e2e
  - evidence: jest 43 + pytest 79 green on 2026-06-21, panel clean over 30 forks
  - log: 2026-06-21T16:52:10Z @kj reported: "name could not be applied - use /rename, and the rename was actually successful"
  - log: 2026-06-21T08:41:03Z @kj fixed: name owned solely by `claude -n`; jest 43 + pytest 79 green
- [ ] `DEF-LNCH-3` **token race on relaunch** - MAJOR; auth token occasionally empty on the first turn after a fork; cause under investigation; `src/session.ts`
  - repro: fork under load, send a turn inside 2s
  - test-tags: integration
  - related: ACC-LNCH-8 - the criterion this violates
  - log: 2026-06-22T09:14:27Z @kj reported: intermittent 401 on the first turn of a branched session
  - log: 2026-06-22T11:02:55Z @kj attempted: 200ms pre-turn delay - did NOT work, the race still fires under load
  - log: 2026-06-23T13:38:19Z @kj details: repro study in [DEF-LNCH-3 details](defects/DEF-LNCH-3-token-race.md)
- [-] `DEF-LNCH-7` **splash hang on a cold cache** - MAJOR; splash never dismissed on first run
  - repro: wipe the profile, launch offline
  - test-tags: manual
  - log: 2026-07-02T15:07:44Z @ac reported by QA
  - log: 2026-07-09T16:52:10Z @ac rejected: not reproduced on 3 devices over 40 cold starts
```

## Repro line, tags and evidence

Three more sub-lines, one line each. The `repro:` line is the one another person acts on, so it is written for them, not for the record.

- **`- repro:`** - shortest sequence that shows the defect: state, action, what appears. `airplane mode on, cold boot the app` beats a paragraph
- **`cannot reproduce`** is a legitimate value, and it is also the argument for `reject`
- **`- test-tags:`** - which kinds of test cover the defect once it is understood: `unit`, `integration`, `functional`, `e2e`, `manual`. On a defect the tag names the regression test that keeps it fixed
- **`- evidence:`** - what proves the defect is gone, written by `close --evidence`: the regression test that now passes, the build it was verified on, the run that no longer reproduces. `the repro no longer fires on build 412, jest 43 green` is evidence; `fixed` is not
- The full study, when one is warranted, goes to a details doc; the `repro:` line stays one line regardless

`close` refuses to run without `--evidence`, so a defect cannot be marked fixed on assertion alone. A `reject` needs a reason, not evidence - nothing was fixed. Reopening a closed defect keeps the evidence where it is and files a regression instead, because the fix was genuinely proven at the time and deleting that proof would erase a true fact.

## Regressions

A defect that was fixed and broke again gets a derived id rather than a reopened checkbox, so each occurrence is counted rather than overwritten.

- **Minting** - `reopen DEF-LNCH-3` opens `DEF-LNCH-3-1` with the same title and severity, and leaves `DEF-LNCH-3` closed
- **Flat ordinals** - reopening `DEF-LNCH-3-1` gives `DEF-LNCH-3-2`, never `-1-1`; the highest ordinal is how many times that defect has come back
- **Both sides logged** - the parent logs `regressed as DEF-LNCH-3-1`, the child logs `regression of DEF-LNCH-3`, so the chain reads in either direction
- **No repro is carried over** - a regression may reproduce differently, so `check` warns until the new one is recorded with `edit --repro`
- **Rejected is not regressed** - a rejected defect reopens normally; nothing was fixed, so nothing regressed
- **Orphans are an error** - a `-N` id whose root is missing counts nothing and points nowhere, and `check` fails on it
- **Counting** - `report` prints `N regressions across M defects` above the SUMMARY grid, in the summary form too

## Details document

What earns one: a deep root-cause analysis, a design tradeoff, or a reproduction study. Link it from a `log:` line, and keep the master line terse.

## Working the file

```bash
pm-tools author docs/defects-app.md --handle @kj --name "Konrad Jelen"
pm-tools add docs/defects-app.md --category LNCH --name Launch --severity MAJOR --author @kj \
    --description "Cold start, splash screen and the first turn after a fork" \
    --title "token race on relaunch" \
    --text "auth token empty on the first turn; cause under investigation; \`src/session.ts\`" \
    --repro "fork under load, send a turn inside 2s" --test-tags "integration"
pm-tools log    docs/defects-app.md --id DEF-LNCH-3 --author @kj \
    --event "attempted: 200ms pre-turn delay - did NOT work"
pm-tools close  docs/defects-app.md --id DEF-LNCH-3 --author @kj \
    --event "fixed: token awaited before the first turn" \
    --evidence "the 2s repro no longer fires on build 412; 79 pytest green"
pm-tools reject docs/defects-app.md --id DEF-LNCH-7 --author @ac \
    --event "not reproduced on 3 devices over 40 cold starts"
pm-tools report docs/defects-app.md
pm-tools check docs --strict
```
