# Upgrading a legacy document

Old acc-crit and defects documents predate ids and categories codes. `pm-tools upgrade` rebuilds one in place: it assigns ids, puts a code on every category, converts dated notes to `log:` lines, and drops the hand-kept `## Contents`.

## Procedure

0. **Build the roster first** - `pm-tools author FILE --handle @xx --name "Full Name"` for everyone who will write. Nothing else can run until at least one handle exists

1. **Name the file so the type is unambiguous** - `docs/acc-crit*.md` or `docs/defects*.md`. The tool reads the type from the filename first, from the ids present second
2. **Dry run** - `pm-tools upgrade FILE` prints every change and every item it cannot handle, and writes nothing
3. **Override the proposed codes** that read badly - `--code "Frontend=FRONT"`, repeatable. The proposal takes the first word whole when it is three to six letters (`Launch` -> `LAUNCH`) and its first four otherwise (`Authentication` -> `AUTH`), extending on collision. Override wherever a letter or two more spells the real word: `FRON` -> `FRONT`, `GUAR` -> `GUARD`. Three to five is the normal range, six the ceiling; readability decides, not brevity
4. **Apply, signing the imported history** - `pm-tools upgrade FILE --author @xx --apply`. A legacy file carries no handles, and hand-editing hundreds of inherited log lines is not a migration; `--author` signs every unauthored one with the importer's handle. Without it the dry run refuses to guess and says so
5. **Clear the MANUAL lines** by hand - the tool refuses to guess on these
6. **Triage every defect** - the dry run prints a ready `pm-tools edit ... --severity ...` line per untriaged defect. Read each symptom, pick the level yourself against the rubric in `references/defects.md`, and run the line. Never ask the user and never skip one - an untriaged defect is a `check` error, so the gate stays red until the whole file is triaged
7. **Describe every category** - `pm-tools describe FILE --category CODE --text "..."`; the tool never invents a description
8. **Fill the per-item lines** - `pm-tools edit FILE --id ID --repro/--test "..." --test-tags "..."`; these are warnings, not errors, so a large legacy file can be filled over several passes
9. **Gate** - `pm-tools check FILE` must exit 0, and `--strict` once the fill is done

## What it changes

| Legacy                                   | After |
|------------------------------------------|-------|
| `## Launch`                              | ``## Launch `LNCH` `` |
| `- [ ] **Label** - text` (no id)          | ``- [ ] `ACC-LNCH-4` **Label** - text`` |
| ``- [ ] `DEF-3` **title** - text``        | ``- [ ] `DEF-LNCH-3` **title** - text`` |
| `  - 2026-06-21 reported: ...`            | `  - log: 2026-06-21T00:00:00Z @xx reported: ...` |
| `  - log: 2026-06-21 fixed: ...`          | `  - log: 2026-06-21T00:00:00Z @xx fixed: ...` |
| `**title** - P1; symptom`                 | `**title** - MAJOR; symptom` - see Severity vocabularies |
| `## Contents` and its list                | deleted; `list-categories` derives it |

Left alone: category descriptions, `repro:` / `test:` hints and `test-tags:`. None can be derived from a legacy file, so `upgrade` reports them rather than guessing.

## Severity vocabularies

A tracker rarely arrives speaking `CRITICAL` / `MAJOR` / `MEDIUM` / `MINOR`. `upgrade` renames the common ones in place and prints what it did (`severity renamed: P1 -> MAJOR x1, URGENT -> CRITICAL x1`).

| Arrives as | Becomes |
|------------|---------|
| `BLOCKER`, `URGENT`, `P0`, `S1`, `SEV1` | `CRITICAL` |
| `HIGH`, `IMPORTANT`, `P1`, `S2`, `SEV2` | `MAJOR` |
| `NORMAL`, `MODERATE`, `P2`, `S3`, `SEV3` | `MEDIUM` |
| `LOW`, `TRIVIAL`, `COSMETIC`, `P3`, `P4`, `S4`, `SEV4` | `MINOR` |

Anything outside that map is not guessed at. An all-caps word before the first `;` that means nothing to the tool is reported as `carries an unmapped severity word 'WISHLIST'`, and you triage it from the symptom like any untriaged defect.

## Numbering

- **An existing number is kept** - a legacy `DEF-3` becomes `DEF-LNCH-3`, so every reference to "DEF-3" in a journal, task or commit still reads true
- **Items with no number** continue above the highest number already in the file, skipping the ones in use
- **Nothing is renumbered** - the upgrade never moves an id that already exists

## What needs a hand

Reported as `MANUAL` on stderr, left untouched:

- **A nested `- [ ]` sub-item** - sub-checkboxes do not exist in this schema. Promote it to its own top-level item under a category, or fold it into its parent's body
- **An item above every `##` heading** - it has no category. Move it under one, or add the heading
- **A category with no description** - reported on every upgrade; `describe` fixes it
A legacy day carries no time, so a widened stamp lands at `00:00:00Z`. That is the honest reading - the day is known, the hour is not - and only new events get a real clock time.

- **A defect with no severity** - legacy files rarely carry one and it cannot be derived; triage each from its symptom with `edit --severity`. This one is a `check` error, so the gate stays red until it is done
- **An item with no log line at all** - `--author` can only sign lines that exist. Give the item one with `log`, then it is signed like the rest. Also a `check` error

The first two are errors in `check`, the third a warning, so none can be forgotten.
