# Merge conflicts in a shared document

One markdown file per discipline means two people editing the same tracker will collide in git. Every collision is resolvable without losing work, because the format is append-only per item and every line names its author.

## Why conflicts are cheap here

- **Items never move** - status lives in the checkbox, so closing something is a one-character edit in place, never a section move
- **Logs are append-only** - two people appending to the same item produce two lines, and both are correct
- **Every log line names its author** - `- log: 2026-08-27 @kj closed: ...`, so "whose line is this" is never a guess
- **Ids are permanent and never reused** - the same id on both sides is the same item

## Default resolution: union

Keep both sides. This settles most conflicts outright.

- **Both appended log lines** - keep every line from both sides, ordered by date. Never drop one; a failed attempt is exactly the record the file exists for
- **Both added relations** - keep both `related:` / `blocked-by:` lines; `check` and `refs` union them anyway
- **Both added items** - keep both, then check the numbering below

## Two people filed the same number

Both sides ran `add` against the same head, so the merged file carries one id twice with different content. `check` reports it as a duplicate.

- **The earlier commit keeps the number** - `git log -S'DEF-AUTH-14' --format='%ai %an %s'` dates both sides
- **The later one is renumbered** to the highest number in the merged file plus one; nothing else about it changes
- **Repoint inbound references** - run `pm-tools refs docs --id DEF-AUTH-14` before editing to see what cites it
- **Never renumber the earlier one** - journals, tasks and commits already cite it, and those citations must stay true

## Two people changed the same single-valued line

The checkbox, severity, the body, `repro:` / `test:`, or `test-tags:`. Union does not apply, so decide - or ask.

- **Checkbox** - the more advanced state wins; closed and rejected both beat open. Between a close and a reopen, the later `log:` date wins. Read the dates off the log lines, not off the commit order
- **Severity** - the higher level wins by default. Keep a demotion only when its log line says why
- **Body, repro, test, tags** - the later commit wins, unless the earlier text carries a fact the later one dropped; then merge them into one line
- **Log the resolution** - `pm-tools log ... --author @you --event "merge: kept @kj MAJOR over @ac MEDIUM"`. The resolver is an author too, and the next reader needs to see the call was deliberate

## Reading the history

- `git log -L<start>,<end>:<file>` - the history of one item's lines
- `git log -S'<ID>' --format='%ai %an %s'` - every commit that added or removed a mention of that id
- `git blame -L<start>,<end> <file>` - who last touched each line, which cross-checks the `@handle` on it

Where the `@handle` and the git author disagree, the handle is authoritative for who **decided** the change and the git author for who committed it. They differ legitimately when one person files on another's behalf.

## In doubt, ask

The rules above cover the common cases, not every case. Where the history does not settle it - a severity demoted with no stated reason, two different fixes for one defect, an item one side closed and the other rejected - stop and ask. Ask the author of the other side where you can reach them, the user otherwise.

- **A wrong merge is silent.** It reads as a clean file, `check` passes, and the lost decision surfaces months later as a defect that was already fixed once
- **Ask with the evidence in hand** - both versions of the line, both `@handle`s, both dates. That makes it a yes-or-no question rather than an investigation
- **Never split the difference** to avoid asking. Half of each side is a third version nobody wrote

## After any resolution

`pm-tools check <dir> --strict` must exit 0. It is what catches a duplicate id, an orphaned relation, an unauthored line, or an item left truncated by a bad merge.
