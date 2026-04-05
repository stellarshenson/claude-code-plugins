# journal

Project journal management plugin for Claude Code. Enforces append-only entry format, continuous numbering, entry verification, and automatic archiving. Auto-triggers after completing substantive work to ensure consistent audit trail.

## Skills (auto-triggered)

| Skill | Triggers when |
|-------|--------------|
| `journal` | After completing substantive work - enforces append-only entries with verification |

## Commands (user-invoked)

| Command | What it does |
|---------|-------------|
| `/journal:create` | Create a new journal entry for completed work |
| `/journal:update` | Update the most recent entry with additional details or corrections |
| `/journal:archive` | Archive older entries, keeping last 20 in main file |

## Entry Format

```
<number>. **Task - <short depiction>** (v1.2.3): task description<br>
    **Result**: summary of work done
```

Version tag `(v1.2.3)` only for versioned projects. Three detail levels: short (~80 words) for bug fixes, normal (~150-200 words, default) for features, extended (~350+ words) for architectural changes.

## Rules

- **Append-only**: new entries at the END of the file, never between existing entries
- **Continuous numbering**: never reset entry numbers, even across archive boundaries
- **Verification**: after writing, read back to confirm entry was appended correctly
- **Archive at 40**: when entries exceed 40, archive older ones keeping last 20
- **Skip maintenance**: git commits, file cleanup, and maintenance tasks are not logged
