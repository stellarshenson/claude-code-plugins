# Upgrading a legacy document

Old acc-crit and defects documents predate ids and category codes. `pm-tools upgrade` rebuilds one in place: it assigns ids, puts a code on every category, converts dated notes to `log:` lines, canonicalises severities and upper-cases `test-tags:` lines, and drops the hand-kept `## Contents`.

`--apply` never refuses on content. Every safe rewrite lands and the command exits 0; every content problem - a missing roster, a missing `--author`, an unrated criterion, an untriaged defect, a missing description, hint or evidence line, a nested sub-item, an item above the first heading - prints as a `HINT` line on stderr carrying the exact command that fixes it. Non-zero exit means an I/O error or a file whose type cannot be read, nothing else.

## Procedure

Apply, read the hints, run the commands they carry, gate.

1. **Name the file so the type is unambiguous** - `docs/acc-crit*.md` or `docs/defects*.md`. The tool reads the type from the filename first, from the ids present second
2. **Dry run** - `pm-tools upgrade FILE` prints the plan and the hints, and writes nothing. Override proposed codes that read badly with `--code "Frontend=FRONT"`, repeatable: the proposal takes the first word whole when it is three to six letters (`Launch` -> `LAUNCH`) and its first four otherwise (`Authentication` -> `AUTH`), extending on collision. Override wherever a letter or two more spells the real word; readability decides, not brevity
3. **Apply, signing the imported history** - `pm-tools upgrade FILE --author @xx --apply`. A legacy file carries no handles; `--author` signs every unauthored log line with the importer's handle. With `--author` absent or not yet on the roster, everything needing no signature still applies, and the hints carry the `author` command and the re-run to finish the signing
4. **Run every hinted command.** Each `HINT` line is one content problem and the command that clears it:
   - **Roster and signatures** - `pm-tools author FILE --handle @xx --name "Full Name"`, then the hinted re-run of `upgrade --author @xx --apply`
   - **Rate every criterion yourself** - one ready `pm-tools edit FILE --id ID --importance CRITICAL|HIGH|MEDIUM|LOW` hint prints per unrated criterion. Read each criterion and pick the level against the rubric in `references/acceptance-criteria.md`; never ask the user and never skip one - an unrated criterion is a `check` error, so the gate stays red until the whole file is rated
   - **Triage every defect yourself** - the same, with `edit --severity` against the rubric in `references/defects.md`. A word the severity map does not know (`WISHLIST`) is named in the hint and triaged from the symptom like any other
   - **Describe every category** - `pm-tools describe FILE --category CODE --text "..."`; the tool never invents a description
   - **Fill the per-item lines** - `pm-tools edit FILE --id ID --repro/--test "..." --test-tags "..."` and `edit --evidence` on closures that carry no proof; these are `check` warnings, not errors, so a large file can be filled over several passes
   - **Restructure by hand where the schema cannot** - a nested `- [ ]` sub-item is promoted to its own item (`add`, then delete the nested line) or folded into its parent's body; an item above every `##` heading is moved under one, then `upgrade --apply` is re-run
5. **Gate** - `pm-tools check FILE` must exit 0, and `--strict` once the fill is done

## What it changes

| Legacy                                   | After |
|------------------------------------------|-------|
| `## Launch`                              | ``## Launch `LNCH` `` |
| `- [ ] **Label** - text` (no id)          | ``- [ ] `ACC-LNCH-4` **Label** - text`` |
| ``- [ ] `DEF-3` **title** - text``        | ``- [ ] `DEF-LNCH-3` **title** - text`` |
| `  - 2026-06-21 reported: ...`            | `  - log: 2026-06-21T00:00:00Z @xx reported: ...` |
| `  - log: 2026-06-21 fixed: ...`          | `  - log: 2026-06-21T00:00:00Z @xx fixed: ...` |
| `**title** - P1; symptom`                 | `**title** - MAJOR; symptom` - see Severity vocabularies |
| `  - test-tags: unit, e2e`                | `  - test-tags: UNIT, E2E` |
| `## Contents` and its list                | deleted; `list-categories` derives it |

A legacy day carries no time, so a widened stamp lands at `00:00:00Z`. That is the honest reading - the day is known, the hour is not - and only new events get a real clock time.

Left alone, and hinted instead: category descriptions, `repro:` / `test:` hints, evidence lines, criterion importance and unmapped severities. None can be derived from a legacy file, so `upgrade` prints the command rather than guessing.

## Severity vocabularies

A tracker rarely arrives speaking `CRITICAL` / `MAJOR` / `MEDIUM` / `MINOR`. `upgrade` renames the common ones in place and prints what it did (`severity renamed: P1 -> MAJOR x1, URGENT -> CRITICAL x1`). The map applies to defects only - on a criterion the body is left alone, and the rating arrives through the `--importance` hints.

| Arrives as | Becomes |
|------------|---------|
| `BLOCKER`, `URGENT`, `P0`, `S1`, `SEV1` | `CRITICAL` |
| `HIGH`, `IMPORTANT`, `P1`, `S2`, `SEV2` | `MAJOR` |
| `NORMAL`, `MODERATE`, `P2`, `S3`, `SEV3` | `MEDIUM` |
| `LOW`, `TRIVIAL`, `COSMETIC`, `P3`, `P4`, `S4`, `SEV4` | `MINOR` |

Anything outside that map is not guessed at - the hint names it (`carries an unmapped severity word 'WISHLIST'`) and you triage it from the symptom.

## Numbering

- **An existing number is kept** - a legacy `DEF-3` becomes `DEF-LNCH-3`, so every reference to "DEF-3" in a journal, task or commit still reads true
- **Items with no number** continue above the highest number already in the file, skipping the ones in use
- **Nothing is renumbered** - the upgrade never moves an id that already exists
