# Item codes and migration

Every item id is `PREFIX-CAT-N-CODE` (`DEF-LNCH-3-PARSER`). `add --code` writes the code on a new item; a document that predates the rule gains one through `migrate-codes`, and a wrong code is corrected with `rename-code`.

## Grammar

- `CODE` is one or two hyphen-separated segments of `A-Z0-9`, each starting with a letter: `PARSER`, `RETRY-LOOP`
- A final all-digit segment is the regression ordinal, read from the right, so a code can never end in one: `DEF-JRNL-1-PARSER-1` is code `PARSER`, regression `1`
- The code sits before the ordinal: a regression item is `<base>-<code>-<n>`
- A base id `<PREFIX>-<CAT>-<N>` names one root and its regressions. Two roots in the scanned files cannot share a base with different codes; `check` errors and names both files and ids
- A code is permanent once assigned. `edit` and `amend` keep it and `reopen` carries it into the new regression id; only `rename-code` changes it, and only to correct a wrong code

## The mapping file

One line per item, `BASE-ID CODE`:

```text
# defects-claude-code-plugins.md
DEF-LNCH-1 TOKEN
DEF-LNCH-2 RENDER
DEF-UI-7 LAYOUT
```

- `BASE-ID` is `PREFIX-CAT-N` with no code and no regression ordinal: `DEF-LNCH-2`, never `DEF-LNCH-2-RENDER` and never `DEF-LNCH-2-RENDER-1`
- One line covers the parent and every regression item sharing that base id; each gets the code before its ordinal
- Blank lines and lines starting with `#` are skipped
- Give each tracker its own mapping file. `migrate-codes` takes one FILE per call, so an id from the other discipline is reported as not in this file
- Every item that carries no code and is not named by the mapping is reported as uncovered, and the command exits 1 while any remains

## Order of operations

`upgrade` first, then the mapping, then the gate.

1. **Rebuild a legacy document first.** `pm-tools upgrade FILE --apply` assigns ids and category codes and converts the old sub-lines. Migration names `PREFIX-CAT-N` ids, so it runs after `upgrade`. A document already on the current schema skips this step
2. **Write the mapping.** Name each item for what it is about, not for its number. Two items sharing a number and category differ by code
3. **Migrate.** `pm-tools migrate-codes FILE --map MAPPING --author @xx`
   - appends the code to every item id the mapping names, before any regression ordinal
   - writes one `- log: <stamp> @xx coded CODE` line per changed item, and one tracker record `coded N item(s) from MAPPING` when it codes at least one
   - is idempotent: an item already carrying the mapped code is left alone with no second log line, so a re-run writes nothing
   - reports the items that carry no code and are not named by the mapping, the mapping ids that match no item, and the items already carrying a different code; the exit code is 1 while any remain
4. **Correct a wrong code with a rename.** `pm-tools rename-code FILE --id ID --code NEW --author @xx`
   - renames the item and every regression sharing its root and code, keeping each ordinal
   - rewrites every `related`, `blocked-by`, `overrides` and `overridden-by` line in the scanned trackers that names the old full id; a base-id link needs no rewrite because it still resolves
   - logs `renamed code "OLD" -> "NEW"` on each item it renames
   - `--id` accepts the base id; the full id wins when both shapes exist. A re-run that finishes an interrupted link rewrite must name the item by its base id or its current full id, because the old full id no longer names an item
5. **Gate.** `pm-tools check FILE` must exit 0, and `pm-tools check FILE --strict` once every other warning is cleared

## Checks

- `pm-tools list FILE --columns id,code` shows a code on every row
- `check` no longer prints `id has no code; every id carries one`
- a second `migrate-codes` run with the same mapping on a clean tracker reports `0 item(s) coded` and leaves the file byte-identical
- after a rename, `check` reports no dangling relation and `refs --id ID` shows the links
- `check` errors on a malformed code and warns, not errors, on a missing one
- `check` warns on a base id written on an item's line or a sub-line other than `log:` and `attachment:`, naming the full id: `DEF-LNCH-2 has no code; write DEF-LNCH-2-RENDER`; a base id plus ordinal (`DEF-LNCH-2-1`) names the coded regression

## Rules

- **Never hand-edit a tracker to add a code.** `migrate-codes` writes the id and its log line together; a hand edit writes the id with no record of why it changed
- **Link by the full id.** `relate` writes a base id as the full id it names, keeps the text around it as typed and prints the code it added
- **Never renumber to make a code fit.** The code is appended to the existing id; the number never moves
- **A code is not a category.** `DEF-LNCH-3-PARSER` may sit under any `##` section; the category segment records where the item was born
- **One root per base id.** A second root claiming an already-used base with a different full id makes every base-id link ambiguous, so `check` errors and names both files and ids; a regression shares its root's base and is not a second root
