---
description: Archive older journal entries via `journal-tools archive`. Keeps last 20 in main, appends rest to JOURNAL_ARCHIVE.md. Triggers - "archive journal", "prune journal", "compact journal".
allowed-tools: [Read, Write, Edit, Bash, Glob]
argument-hint: "(optional) --keep-last N, --threshold N"
---

# Archive Journal

Prefer the programmatic tool. It preserves numbering and appends idempotently.

## Pre-flight install (MANDATORY, no asking)

Before invoking `journal-tools archive`, always run:

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

No-op when the package is importable; auto-installs when missing or when a stale shim is on PATH but the package is uninstalled in the active Python. Never skip. Never ask.

## Primary path (programmatic)

```bash
uv run journal-tools archive .claude/JOURNAL.md
```

Default: threshold 40, keep last 20. Flags: `--keep-last N`, `--threshold N`, `--archive-path PATH`. If `uv` not available, try plain `journal-tools archive ...` or `python -m stellars_claude_code_plugins.journal_tools archive ...`.

After run:
1. Read `.claude/JOURNAL.md` last 5 lines — confirm last 20 entries remain, note at top links to archive
2. Read `.claude/JOURNAL_ARCHIVE.md` last 5 lines — confirm entries appended, numbering continuous
3. Run `uv run journal-tools check .claude/JOURNAL.md` — exit 0 = clean

## Fallback (manual, only if CLI unavailable)

1. Read `.claude/JOURNAL.md`, count entries
2. If count > 40, move all except last 20 to `.claude/JOURNAL_ARCHIVE.md` (create or append)
3. Keep main journal starting at entry `N-19` (not reset to 1)
4. Add top line: `**Note**: Entries 1-M have been archived to [JOURNAL_ARCHIVE.md](JOURNAL_ARCHIVE.md).`
5. Verify both files after — no entries lost, numbering continuous across archive + main

## Rules

- Numbering is continuous across archive + main. NEVER reset to 1.
- Archive file appends. NEVER overwrite.
- Threshold default 40, keep-last default 20 — do not change unless user asks.
