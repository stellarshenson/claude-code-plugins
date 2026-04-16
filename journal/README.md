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

| Command | What it does |
|---------|-------------|
| `/journal:create` | Create a new journal entry for completed work |
| `/journal:update` | Update the most recent entry with additional details or corrections |
| `/journal:archive` | Archive older entries, keeping the last 20 in the main file |

## Skills

| Skill | Triggers when |
|-------|--------------|
| `journal` | After completing substantive work - enforces append-only entries, format, numbering, and verification |

## CLI tools

Deterministic validation, archiving, and sorting - no generative AI in the loop.

```bash
# Validate format, numbering, and word counts
journal-tools check .claude/JOURNAL.md

# Archive old entries (threshold 40, keep last 20)
journal-tools archive .claude/JOURNAL.md

# Re-number entries sequentially (fix gaps/ordering)
journal-tools sort .claude/JOURNAL.md --dry-run
```

The checker enforces two word-count tiers for entry bodies (after `**Result**:`):

| Tier | Target | Use when |
|------|--------|----------|
| **Standard** | <=150 words | DEFAULT. Features, bug fixes, multi-file changes |
| **Extended** | <=400 words | Architectural decisions, cross-cutting refactors, debugging sagas |

Entries exceeding standard target get a warning; entries exceeding extended max get an error.

## Entry format

Entries follow the pattern `N. **Task - <short name>**:` / `**Result**:`, optionally tagged with a project version (e.g. `(v1.3.1)`) when the project has a `package.json`, `pyproject.toml`, or similar manifest. Numbering is continuous across the lifetime of the journal and never resets across archive boundaries.

Two detail tiers (Standard and Extended) cover the span from quick fix to multi-topic release. Standard is the default - match the user's own summary length and do not inflate. Full examples in `skills/journal/references/examples.md`.

## Rules summary

- Append-only writes, entries never inserted between existing ones
- Continuous numbering preserved across archive boundaries
- Archive threshold at 40 entries, main file trimmed to last 20
- Maintenance tasks (git commits, cleanup) are skipped, not logged
- Standard tier <=150 words is the default; Extended only when justified

## Documentation

- `skills/journal/SKILL.md` - full entry spec, verification, append-only enforcement, archive flow
- `skills/journal/references/examples.md` - worked examples for each detail tier
