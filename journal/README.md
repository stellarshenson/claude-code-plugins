# journal

Append-only project journal with continuous numbering, archiving, and entry format enforcement. Auto-triggers after completing substantive work to maintain a consistent, machine-readable audit trail in `.claude/JOURNAL.md`.

Unlike ad-hoc changelog updates, this plugin enforces a single entry shape, guarantees new entries land at the end of the file, preserves continuous numbering across archive boundaries, and verifies each write by reading the last lines back.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install journal@stellarshenson-marketplace
```

## Commands

| Command | What it does |
|---------|-------------|
| `/journal:create` | Create a new journal entry for completed work |
| `/journal:update` | Update the most recent entry with additional details or corrections |
| `/journal:archive` | Archive older entries, keeping the last 20 in the main file |

## Skills

| Skill | Triggers when |
|-------|--------------|
| `journal` | After completing substantive work - enforces append-only entries, format, numbering, and verification |

## Entry format

Entries follow the pattern `N. **Task - <short name>**:` / `**Result**:`, optionally tagged with a project version (e.g. `(v1.3.1)`) when the project has a `package.json`, `pyproject.toml`, or similar manifest. Numbering is continuous across the lifetime of the journal and never resets across archive boundaries.

Four detail levels (Short, Normal, Extended, Multi-topic Normal) cover the span from trivial fix to multi-topic release. Full examples and guidance on when to pick each shape live in `skills/journal/references/examples.md`.

## Example

```bash
# Create an entry after finishing a feature
/journal:create implemented workspace culling with last_modified timestamp

# Archive when the journal has grown past 40 entries
/journal:archive
```

The `journal` skill also fires automatically at the end of substantive sessions, so explicit `/journal:create` is mostly useful when forcing an entry or disambiguating a multi-part task.

## Rules summary

- Append-only writes, entries never inserted between existing ones
- Continuous numbering preserved across archive boundaries
- Archive threshold at 40 entries, main file trimmed to last 20
- Maintenance tasks (git commits, cleanup) are skipped, not logged

Full specification, verification steps, and archive renumbering flow in `skills/journal/SKILL.md`.

## Documentation

- `skills/journal/SKILL.md` - full entry spec, verification, append-only enforcement, archive flow
- `skills/journal/references/examples.md` - worked examples for each detail level
