"""Deterministic journal operations: parse, check, archive, sort.

No generative AI — pure string parsing, validation, and file manipulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import sys

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(
    r"^(\d+)\.\s+\*\*Task\s*-\s*(.+?)\*\*"
    r"(?:\s*\(([^)]*)\))?"
    r":\s*(.*?)(?:<br>|$)",
    re.IGNORECASE,
)

RESULT_PREFIX = re.compile(r"^\s+\*\*Result\*\*:\s*", re.IGNORECASE)

STANDARD_TARGET = 150
EXTENDED_MAX = 400


@dataclass
class JournalEntry:
    number: int
    title: str
    version_tag: str
    description: str
    result_body: str
    raw_lines: list[str] = field(default_factory=list)
    line_start: int = 0

    @property
    def body_word_count(self) -> int:
        return len(self.result_body.split())


@dataclass
class Violation:
    entry_number: int | None
    severity: str  # "error" | "warning"
    message: str


@dataclass
class ArchiveResult:
    moved_count: int
    remaining_count: int
    archive_path: str


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_journal(text: str) -> list[JournalEntry]:
    """Parse a JOURNAL.md file into structured entries.

    Handles the standard format:
        N. **Task - Title** (vX.Y.Z): description<br>
            **Result**: body text...
    """
    lines = text.split("\n")
    entries: list[JournalEntry] = []
    current: JournalEntry | None = None
    in_result = False

    for i, line in enumerate(lines):
        m = ENTRY_RE.match(line)
        if m:
            if current is not None:
                current.result_body = current.result_body.strip()
                entries.append(current)
            current = JournalEntry(
                number=int(m.group(1)),
                title=m.group(2).strip(),
                version_tag=m.group(3) or "",
                description=m.group(4).strip(),
                result_body="",
                raw_lines=[line],
                line_start=i + 1,
            )
            in_result = False
            continue

        if current is not None:
            current.raw_lines.append(line)
            rm = RESULT_PREFIX.match(line)
            if rm:
                in_result = True
                current.result_body = line[rm.end() :]
            elif in_result and line.strip():
                current.result_body += " " + line.strip()

    if current is not None:
        current.result_body = current.result_body.strip()
        entries.append(current)

    return entries


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------


def check_journal(
    entries: list[JournalEntry],
    standard_target: int = STANDARD_TARGET,
    extended_max: int = EXTENDED_MAX,
) -> list[Violation]:
    """Validate journal entries. Returns a list of violations (may be empty).

    Checks:
    - Continuous numbering (no gaps, no duplicates)
    - Ascending order (append-only)
    - Entry format (has title, has Result body)
    - Word count thresholds (> standard_target = warning, > extended_max = error)
    """
    violations: list[Violation] = []

    if not entries:
        return violations

    seen: dict[int, int] = {}
    prev_num = 0

    for entry in entries:
        # Duplicate check
        if entry.number in seen:
            violations.append(
                Violation(
                    entry.number,
                    "error",
                    f"duplicate entry number {entry.number} "
                    f"(first at line {seen[entry.number]}, again at line {entry.line_start})",
                )
            )
        seen[entry.number] = entry.line_start

        # Ordering check
        if entry.number <= prev_num:
            violations.append(
                Violation(
                    entry.number,
                    "error",
                    f"entry {entry.number} is out of order (previous was {prev_num})",
                )
            )
        prev_num = entry.number

        # Format checks
        if not entry.title:
            violations.append(Violation(entry.number, "error", "missing title after 'Task -'"))

        if not entry.result_body:
            violations.append(
                Violation(entry.number, "warning", "missing or empty **Result** body")
            )

        # Word count
        wc = entry.body_word_count
        if wc > extended_max:
            violations.append(
                Violation(
                    entry.number,
                    "error",
                    f"body is {wc} words (max extended = {extended_max}). "
                    f"Condense to standard ({standard_target}) or justify extended.",
                )
            )
        elif wc > standard_target:
            violations.append(
                Violation(
                    entry.number,
                    "warning",
                    f"body is {wc} words (standard target = {standard_target}). "
                    f"Consider condensing unless extended is justified.",
                )
            )

    # Continuity check (gaps)
    numbers = sorted(seen.keys())
    if numbers:
        expected = list(range(numbers[0], numbers[-1] + 1))
        missing = set(expected) - set(numbers)
        if missing:
            violations.append(
                Violation(
                    None,
                    "warning",
                    f"gap in numbering: missing entries {sorted(missing)}",
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Sorter
# ---------------------------------------------------------------------------


def sort_entries(entries: list[JournalEntry], start_from: int = 1) -> list[JournalEntry]:
    """Re-number entries sequentially starting from ``start_from``.

    Returns a NEW list with corrected numbers. Does not modify the input.
    Entries are sorted by their original number first, so out-of-order
    entries are fixed. The raw_lines are NOT updated - use
    ``render_entries`` to produce the corrected markdown.
    """
    sorted_entries = sorted(entries, key=lambda e: e.number)
    result: list[JournalEntry] = []
    for i, entry in enumerate(sorted_entries):
        new = JournalEntry(
            number=start_from + i,
            title=entry.title,
            version_tag=entry.version_tag,
            description=entry.description,
            result_body=entry.result_body,
            raw_lines=entry.raw_lines,
            line_start=entry.line_start,
        )
        result.append(new)
    return result


def render_entries(entries: list[JournalEntry]) -> str:
    """Render a list of JournalEntry objects back to markdown text."""
    parts: list[str] = []
    for entry in entries:
        version = f" ({entry.version_tag})" if entry.version_tag else ""
        header = f"{entry.number}. **Task - {entry.title}**{version}: {entry.description}<br>"
        result = f"    **Result**: {entry.result_body}"
        parts.append(f"{header}\n{result}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Archiver
# ---------------------------------------------------------------------------

JOURNAL_HEADER = """# Claude Code Journal

This journal tracks substantive work on documents, diagrams, and documentation content.
"""

ARCHIVE_HEADER = """# Claude Code Journal Archive

This file contains archived journal entries from the main JOURNAL.md.

---
"""


def archive_journal(
    journal_path: str | Path,
    archive_path: str | Path | None = None,
    keep_last: int = 20,
    threshold: int = 40,
) -> ArchiveResult | None:
    """Move older entries from JOURNAL.md to JOURNAL_ARCHIVE.md when
    the entry count exceeds ``threshold``.

    Returns an ArchiveResult on success, None if no archiving was needed.
    Maintains continuous numbering. Appends to existing archive if present.
    """
    journal_path = Path(journal_path)
    if archive_path is None:
        archive_path = journal_path.parent / "JOURNAL_ARCHIVE.md"
    else:
        archive_path = Path(archive_path)

    text = journal_path.read_text(encoding="utf-8")
    entries = parse_journal(text)

    if len(entries) <= threshold:
        return None

    to_archive = entries[:-keep_last]
    to_keep = entries[-keep_last:]

    # Build archive content
    if archive_path.exists():
        existing_archive = archive_path.read_text(encoding="utf-8")
        existing_archived = parse_journal(existing_archive)
    else:
        existing_archived = []

    all_archived = existing_archived + to_archive
    archive_body = render_entries(all_archived)
    archive_text = ARCHIVE_HEADER + "\n" + archive_body + "\n"
    archive_path.write_text(archive_text, encoding="utf-8")

    # Build new journal
    last_archived = to_archive[-1].number if to_archive else 0
    archive_note = (
        f"**Note**: Entries 1-{last_archived} have been archived to "
        f"[JOURNAL_ARCHIVE.md](JOURNAL_ARCHIVE.md).\n"
    )
    journal_body = render_entries(to_keep)
    journal_text = JOURNAL_HEADER + "\n" + archive_note + "\n---\n\n" + journal_body + "\n"
    journal_path.write_text(journal_text, encoding="utf-8")

    return ArchiveResult(
        moved_count=len(to_archive),
        remaining_count=len(to_keep),
        archive_path=str(archive_path),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``journal-tools check|archive|sort <path>``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="journal-tools",
        description="Deterministic journal validation, archiving, and sorting.",
    )
    sub = parser.add_subparsers(dest="command")

    # check
    p_check = sub.add_parser("check", help="Validate journal entries.")
    p_check.add_argument("path", help="Path to JOURNAL.md")
    p_check.add_argument(
        "--standard-target",
        type=int,
        default=STANDARD_TARGET,
        help=f"Word count target for standard entries (default: {STANDARD_TARGET})",
    )
    p_check.add_argument(
        "--extended-max",
        type=int,
        default=EXTENDED_MAX,
        help=f"Word count max for extended entries (default: {EXTENDED_MAX})",
    )

    # archive
    p_archive = sub.add_parser("archive", help="Archive old entries.")
    p_archive.add_argument("path", help="Path to JOURNAL.md")
    p_archive.add_argument(
        "--keep-last", type=int, default=20, help="Entries to keep (default: 20)"
    )
    p_archive.add_argument(
        "--threshold",
        type=int,
        default=40,
        help="Archive only when entry count exceeds this (default: 40)",
    )
    p_archive.add_argument("--archive-path", default=None, help="Path for archive file")

    # sort
    p_sort = sub.add_parser("sort", help="Re-number entries sequentially.")
    p_sort.add_argument("path", help="Path to JOURNAL.md")
    p_sort.add_argument("--start-from", type=int, default=1, help="Starting number (default: 1)")
    p_sort.add_argument(
        "--dry-run",
        action="store_true",
        help="Print corrected output without writing",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    entries = parse_journal(text)

    if args.command == "check":
        violations = check_journal(
            entries,
            standard_target=args.standard_target,
            extended_max=args.extended_max,
        )
        if not violations:
            print(f"OK: {len(entries)} entries, no violations.")
            return 0
        for v in violations:
            prefix = f"[{v.severity.upper()}]"
            entry_label = f"entry {v.entry_number}" if v.entry_number else "global"
            print(f"{prefix} {entry_label}: {v.message}")
        errors = sum(1 for v in violations if v.severity == "error")
        warnings = sum(1 for v in violations if v.severity == "warning")
        print(f"\n{len(entries)} entries, {errors} errors, {warnings} warnings.")
        return 1 if errors else 0

    elif args.command == "archive":
        result = archive_journal(
            path,
            archive_path=args.archive_path,
            keep_last=args.keep_last,
            threshold=args.threshold,
        )
        if result is None:
            print(f"No archiving needed ({len(entries)} entries, threshold={args.threshold}).")
            return 0
        print(
            f"Archived {result.moved_count} entries to {result.archive_path}, "
            f"{result.remaining_count} remaining in {path}."
        )
        return 0

    elif args.command == "sort":
        sorted_entries = sort_entries(entries, start_from=args.start_from)
        # Preserve the header and any non-entry content before first entry
        header_end = 0
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if ENTRY_RE.match(line):
                header_end = i
                break
        header = "\n".join(lines[:header_end])
        body = render_entries(sorted_entries)
        output = header + "\n\n" + body + "\n"

        if args.dry_run:
            print(output)
        else:
            path.write_text(output, encoding="utf-8")
            changes = sum(
                1 for old, new in zip(entries, sorted_entries) if old.number != new.number
            )
            print(
                f"Re-numbered {changes} entries "
                f"({sorted_entries[0].number}-{sorted_entries[-1].number})."
            )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
