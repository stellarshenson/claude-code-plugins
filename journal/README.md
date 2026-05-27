# journal

Append-only project journal with continuous numbering, archiving, and entry format enforcement. Auto-triggers after completing substantive work to maintain a consistent, machine-readable audit trail in `.claude/JOURNAL.md`.

Unlike ad-hoc changelog updates, this plugin enforces a single entry shape, guarantees new entries land at the end of the file, preserves continuous numbering across archive boundaries, and verifies each write by reading the last lines back.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install journal@stellarshenson-marketplace
```

The `journal-tools` CLI ships as part of the shared Python package:

```bash
pip install stellars-claude-code-plugins
journal-tools --help
```

## Commands

Clear split, no ambiguity:

| Command | Use |
|---------|-----|
| `/journal:create` | INIT only — scaffolds empty `JOURNAL.md` and backfills entries from conversation context. Refuses if file exists. Triggers: "create journal", "init journal", "start journal" |
| `/journal:update` | DEFAULT write — appends a new numbered entry (or extends the last entry's Result paragraph when the work is the same task). Triggers: "update journal", "add journal entry", "log this", "journal this", "record this in the journal" |
| `/journal:archive` | Archive older entries via `journal-tools archive` (keeps last 20 in main, appends rest to `JOURNAL_ARCHIVE.md`). Triggers: "archive journal", "prune journal" |
| `/journal:standardize` | REPAIR word-count drift for entries `check` warned on. For each offender (oversized Standard, oversized Extended, spurious `[Extended]` marker), a focused `claude -p` subprocess decides Extended vs Condense vs Drop-marker; the CLI applies the verdict. Use after `check` reports warnings — never inline-edit oversized entries by hand. Triggers: "standardize journal", "fix journal entry tiers", "repair journal" |
| `/journal:article` | EXTRACT depth from an over-Extended-max entry (>400 words) into a standalone `docs/<slug>.md` article and condense the entry to a Standard-tier summary linking to the article. Asks via `AskUserQuestion` for title / location / scope / summary length. Triggers: "create article from entry", "extract journal entry to article" |

All five commands auto-run `journal-tools check` after writing and refuse to proceed on format / numbering errors.

## Skills

| Skill | Triggers when |
|-------|--------------|
| `journal` | Auto-triggered on any of the phrases above or after finishing substantive work - enforces append-only entries, format, numbering, and post-write CLI validation |

## CLI tools

Deterministic validation, archiving, sorting, and word-count repair - the three pure-string subcommands run with no generative AI in the loop; `standardize` orchestrates a focused `claude -p` subprocess per offender for the edit step itself.

```bash
# Validate format, numbering, and word counts
journal-tools check .claude/JOURNAL.md

# Archive old entries (threshold 40, keep last 20)
journal-tools archive .claude/JOURNAL.md

# Re-number entries sequentially (fix gaps/ordering)
journal-tools sort .claude/JOURNAL.md --dry-run

# Repair word-count drift on entries `check` warned on.
# Three-mode invocation: list offenders, render the per-entry ACP prompt,
# then apply the decision returned by a `claude -p` subprocess.
journal-tools standardize --list .claude/JOURNAL.md
journal-tools standardize --prompt N .claude/JOURNAL.md
journal-tools standardize --apply N --decision extended|condense|drop-marker .claude/JOURNAL.md
```

The checker enforces three word-count tiers for entry bodies (after `**Result**:`) plus a fourth "outgrown the journal" overflow:

| Tier | Marker | Words | Use when |
|------|--------|-------|----------|
| **Short** | `[Short]` | 1 - 49 | Trivial: typo fix, one-line URL bump, dep pin. No WHY to preserve - the diff IS the WHY |
| **Standard** | none | 50 - 150 | DEFAULT. Features, bug fixes, multi-file changes |
| **Extended** | `[Extended]` | 150 - 400 | Architectural decision, platform migration, multi-iteration debug, novel algorithm |
| **Article** | (entry links to `docs/`) | > 400 | Run `/journal:article N` to move depth into `docs/<slug>.md` and condense the entry to a Standard summary + link |

Markers are mandatory. `[Short]` is needed under 50 words (otherwise the validator warns "too terse"); `[Extended]` is needed over 150 words (otherwise the validator warns "condense or add marker"). False-advertising markers (e.g. `[Short]` body at 100 words, `[Extended]` body at 50 words) also warn. Length warnings are nudges (never errors); format violations (duplicate numbers, out-of-order entries, missing title, missing or duplicate `**Result**:`) are errors since they break the audit trail.

## Entry format

Entries follow the pattern `N. **Task - <short name>**:` / `**Result**:`, optionally tagged with a project version (e.g. `(v1.3.1)`) when the project has a `package.json`, `pyproject.toml`, or similar manifest. Numbering is continuous across the lifetime of the journal and never resets across archive boundaries.

Three detail tiers (Short, Standard, Extended) cover the span from typo fix to multi-topic release; anything heavier graduates to a `docs/` article via `/journal:article`. **Standard is the default** - match the user's own summary length and do not inflate. Full examples in `skills/journal/references/examples.md`.

## Rules summary

- Append-only writes, entries never inserted between existing ones
- Continuous numbering preserved across archive boundaries
- Archive threshold at 40 entries, main file trimmed to last 20
- Maintenance tasks (git commits, cleanup) are skipped, not logged
- Standard tier (50-150 words) is the default; Short / Extended / Article when justified

## Documentation

- `skills/journal/SKILL.md` - full entry spec, verification, append-only enforcement, archive flow
- `skills/journal/references/examples.md` - worked examples for each detail tier
