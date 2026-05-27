"""Deterministic journal operations: parse, check, archive, sort, standardize.

Pure string parsing, validation, and file manipulation. The `standardize`
subcommand additionally drives an ACP subprocess (a fresh `claude -p` call)
to make the per-entry Extended-vs-Condense decision; the orchestration is
deterministic, the decision is the only generative step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(
    r"^(\d+)\.\s+\*\*Task\s*(?P<marker>\[(?:Extended|Short)\])?\s*-\s*(.+?)\*\*"
    r"(?:\s*\(([^)]*)\))?"
    r":\s*(.*?)(?:<br>|$)",
    re.IGNORECASE,
)

RESULT_PREFIX = re.compile(r"^\s+\*\*Result\*\*:\s*", re.IGNORECASE)

STANDARD_MIN = 50
STANDARD_TARGET = 150
EXTENDED_MIN = 150
EXTENDED_MAX = 400
# Entries marked [Short] must sit under STANDARD_MIN (intentionally brief).
# A [Short]-marked body at or above the threshold is false advertising -
# warn and tell the user to drop the marker.
SHORT_MAX = STANDARD_MIN

# Bump when the rubric in prompts/standardize.yaml gets a breaking change.
# The CLI refuses to load any other version - prevents an old wheel pinned
# alongside a new YAML (or vice versa) from silently misfiring on the
# subprocess decision rules.
STANDARDIZE_YAML_VERSION = 2


@dataclass
class JournalEntry:
    number: int
    title: str
    version_tag: str
    description: str
    result_body: str
    is_extended: bool = False
    is_short: bool = False  # `[Short]` marker: intentionally brief (<STANDARD_MIN)
    result_marker_count: int = 0  # number of `**Result**:` lines seen for this Task
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


def parse_journal_with_diagnostics(
    text: str,
) -> tuple[list[JournalEntry], list[Violation]]:
    """Parse a JOURNAL.md file into structured entries + parser-level violations.

    Handles the standard format:
        N. **Task - Title** (vX.Y.Z): description<br>
            **Result**: body text...

    Parser-level violations cover format errors that don't correspond to a
    successfully-parsed entry:
    - Orphan `**Result**:` lines outside any Task (silently absorbed today
      would be a silent bug; surface as an error so the author can fix)

    Per-entry violations like "Task without Result marker" or "multiple
    Result markers" are NOT in the parser-violations list - they live on
    the entry via `result_marker_count` and are surfaced by `check_journal`.
    """
    lines = text.split("\n")
    entries: list[JournalEntry] = []
    parser_violations: list[Violation] = []
    current: JournalEntry | None = None
    in_result = False

    for i, line in enumerate(lines):
        m = ENTRY_RE.match(line)
        if m:
            if current is not None:
                current.result_body = current.result_body.strip()
                entries.append(current)
            marker_text = (m.group("marker") or "").lower()
            current = JournalEntry(
                number=int(m.group(1)),
                title=m.group(3).strip(),
                version_tag=m.group(4) or "",
                description=m.group(5).strip(),
                is_extended="extended" in marker_text,
                is_short="short" in marker_text,
                result_body="",
                raw_lines=[line],
                line_start=i + 1,
            )
            in_result = False
            continue

        if current is None:
            # Outside any entry. Flag orphan `**Result**:` lines as errors -
            # they were silently absorbed by the previous parser, masking
            # malformed entries where the Task line was missing or mistyped.
            if RESULT_PREFIX.match(line):
                parser_violations.append(
                    Violation(
                        entry_number=None,
                        severity="error",
                        message=(
                            f"line {i + 1}: orphan **Result**: marker outside "
                            "any Task entry. Add a `N. **Task - ...**` line "
                            "above it, or remove the stray marker."
                        ),
                    )
                )
            continue

        current.raw_lines.append(line)
        rm = RESULT_PREFIX.match(line)
        if rm:
            current.result_marker_count += 1
            if current.result_marker_count == 1:
                in_result = True
                current.result_body = line[rm.end() :]
            else:
                # Second (or later) Result marker on the same Task. Keep the
                # content (append instead of overwrite) so nothing is lost,
                # but the entry now carries result_marker_count > 1 which
                # `check_journal` flags as an error.
                current.result_body += " " + line[rm.end() :]
            continue
        if in_result and line.strip():
            current.result_body += " " + line.strip()

    if current is not None:
        current.result_body = current.result_body.strip()
        entries.append(current)

    return entries, parser_violations


def parse_journal(text: str) -> list[JournalEntry]:
    """Parse a JOURNAL.md file into structured entries.

    Thin wrapper around `parse_journal_with_diagnostics` that drops the
    parser-violations list - kept for back-compat with callers that only
    need the entries. New code should prefer the diagnostics form so
    orphan-Result violations are surfaced.
    """
    entries, _ = parse_journal_with_diagnostics(text)
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
    - Word count thresholds (> standard_target = warning, > extended_max = warning)
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

        # Result marker checks. Three failure modes:
        # 1. No `**Result**:` line at all -> structural error (the Task has no result)
        # 2. Exactly one `**Result**:` line but body is empty -> warning (marker present, no content)
        # 3. More than one `**Result**:` line on the same Task -> structural error
        if entry.result_marker_count == 0:
            violations.append(
                Violation(
                    entry.number,
                    "error",
                    "Task line has no `**Result**:` marker. Every Task must "
                    "be followed by a `    **Result**: ...` line on the next "
                    "indented line.",
                )
            )
        elif entry.result_marker_count > 1:
            violations.append(
                Violation(
                    entry.number,
                    "error",
                    f"Task has {entry.result_marker_count} `**Result**:` "
                    "markers; expected exactly 1. Merge the bodies into a "
                    "single **Result** paragraph or split into separate "
                    "numbered Task entries.",
                )
            )
        elif not entry.result_body:
            violations.append(
                Violation(entry.number, "warning", "`**Result**:` marker found but body is empty")
            )

        # Word count: warnings only (never errors).
        # Tier ladder (any-marker = false-advertising warnings included):
        #   - empty body              -> warning (covered above)
        #   - [Short]: must be < STANDARD_MIN; >= STANDARD_MIN warns
        #   - unmarked < STANDARD_MIN -> "too terse, add [Short] or expand"
        #   - unmarked <= standard_target -> silent (Standard sweet spot)
        #   - unmarked > standard_target, <= extended_max -> "condense or [Extended]"
        #   - [Extended]: must be [EXTENDED_MIN, extended_max]; outside warns
        #   - any > extended_max      -> "create article in docs/ + link"
        wc = entry.body_word_count
        article_advice = (
            f"body {wc} words, over extended max {extended_max}. Even Extended "
            "caps here - move the depth into a standalone article in `docs/` "
            "and condense this entry to a Standard-tier summary that links to "
            f"the article (run `/journal:article {entry.number}` for the "
            "guided flow)."
        )
        if entry.is_extended:
            if wc > extended_max:
                violations.append(Violation(entry.number, "warning", article_advice))
            elif wc < EXTENDED_MIN:
                violations.append(
                    Violation(
                        entry.number,
                        "warning",
                        f"body {wc} words but marked [Extended] "
                        f"(min {EXTENDED_MIN}). Expand or drop the marker.",
                    )
                )
        elif entry.is_short:
            if wc >= SHORT_MAX:
                violations.append(
                    Violation(
                        entry.number,
                        "warning",
                        f"body {wc} words but marked [Short] (intended for "
                        f"< {SHORT_MAX}). Drop the marker - the body sits in "
                        "Standard tier already.",
                    )
                )
        elif wc > extended_max:
            violations.append(Violation(entry.number, "warning", article_advice))
        elif wc > standard_target:
            violations.append(
                Violation(
                    entry.number,
                    "warning",
                    f"body {wc} words, over Standard target {standard_target}. "
                    "Condense or add `**Task [Extended] - ...**` marker if "
                    "depth is real.",
                )
            )
        elif 0 < wc < STANDARD_MIN:
            violations.append(
                Violation(
                    entry.number,
                    "warning",
                    f"body {wc} words, under Standard min {STANDARD_MIN}. "
                    "Too terse to carry rationale six months out - add the "
                    "`**Task [Short] - ...**` marker if intentionally brief, "
                    "or expand with trigger / why-this-approach / "
                    "cause-and-effect.",
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
    ``render_entries`` to produce the corrected markdown. The
    ``is_extended`` flag is preserved so renumbering does not strip
    `[Extended]` markers (which would silently downgrade architectural
    entries to Standard tier and trigger over-150 warnings on the next
    `check` run).
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
            is_extended=entry.is_extended,
            is_short=entry.is_short,
            result_marker_count=entry.result_marker_count,
            raw_lines=entry.raw_lines,
            line_start=entry.line_start,
        )
        result.append(new)
    return result


def render_entries(entries: list[JournalEntry]) -> str:
    """Render a list of JournalEntry objects back to markdown text.

    Emits the ``[Extended]`` or ``[Short]`` marker between `Task` and the
    dash when the respective flag is true so sort/render round-trips
    preserve tier markers (an earlier bug where sort dropped the marker
    silently downgraded entries to Standard tier and fired bogus
    word-count warnings on the next `check` run).
    """
    parts: list[str] = []
    for entry in entries:
        version = f" ({entry.version_tag})" if entry.version_tag else ""
        if entry.is_extended:
            marker = "[Extended] "
        elif entry.is_short:
            marker = "[Short] "
        else:
            marker = ""
        header = (
            f"{entry.number}. **Task {marker}- {entry.title}**{version}: {entry.description}<br>"
        )
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


# ---------------------------------------------------------------------------
# Standardize - identify and repair oversized / mis-marked entries
# ---------------------------------------------------------------------------


def _load_standardize_prompt() -> dict:
    """Load the standardize prompt template from package data.

    The YAML ships with the wheel under
    ``stellars_claude_code_plugins/journal/prompts/standardize.yaml``.
    Returns the parsed dict; raises if the file is missing or the
    ``version`` field is unsupported.
    """
    from importlib import resources

    import yaml

    try:
        ref = resources.files("stellars_claude_code_plugins.journal.prompts").joinpath(
            "standardize.yaml"
        )
        text = ref.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "standardize.yaml prompt template not found in package data; "
            "reinstall stellars-claude-code-plugins"
        ) from exc
    data = yaml.safe_load(text)
    if data.get("version") != STANDARDIZE_YAML_VERSION:
        raise RuntimeError(
            f"standardize.yaml version={data.get('version')!r} unsupported by this CLI "
            f"(expected {STANDARDIZE_YAML_VERSION}); upgrade stellars-claude-code-plugins"
        )
    return data


def _classify_repair_action(
    entry: JournalEntry,
    standard_target: int = STANDARD_TARGET,
    extended_max: int = EXTENDED_MAX,
) -> str | None:
    """Return the standardize action for an entry, or None if it is fine.

    Possible actions:
    - ``"drop_marker"``: ``[Extended]`` present but body < standard_target.
      Deterministic; no subprocess decision needed.
    - ``"decide"``: no marker, body > standard_target, body <= extended_max.
      Subprocess decides EXTENDED vs CONDENSE.
    - ``"condense"``: body > extended_max (regardless of marker). Subprocess
      must condense.
    """
    wc = entry.body_word_count
    if entry.is_extended and wc < standard_target:
        return "drop_marker"
    if wc > extended_max:
        return "condense"
    if not entry.is_extended and wc > standard_target:
        return "decide"
    return None


def list_repair_candidates(
    entries: list[JournalEntry],
    standard_target: int = STANDARD_TARGET,
    extended_max: int = EXTENDED_MAX,
) -> list[dict]:
    """Return JSON-shaped list of entries needing standardize repair."""
    out: list[dict] = []
    for entry in entries:
        action = _classify_repair_action(entry, standard_target, extended_max)
        if action is None:
            continue
        task_line = entry.raw_lines[0] if entry.raw_lines else ""
        out.append(
            {
                "number": entry.number,
                "line_start": entry.line_start,
                "line_end": entry.line_start + len(entry.raw_lines) - 1,
                "word_count": entry.body_word_count,
                "has_extended_marker": entry.is_extended,
                "action_needed": action,
                "task_line": task_line.rstrip("\n"),
                "body": entry.result_body,
            }
        )
    return out


def render_standardize_prompt(entry: JournalEntry, template: dict | None = None) -> str:
    """Render the per-entry standardize prompt as one block of text.

    Substitutes ``{{number}}``, ``{{word_count}}``, ``{{has_marker}}``,
    ``{{task_line}}``, ``{{body}}`` in the template's ``user_template``.
    The system prompt is prepended as a header so the subprocess sees both
    in one ``claude -p`` invocation.
    """
    if template is None:
        template = _load_standardize_prompt()
    task_line = entry.raw_lines[0].rstrip("\n") if entry.raw_lines else ""
    rendered = template["user_template"]
    for key, value in (
        ("number", str(entry.number)),
        ("word_count", str(entry.body_word_count)),
        ("has_marker", "true" if entry.is_extended else "false"),
        ("task_line", task_line),
        ("body", entry.result_body),
    ):
        rendered = rendered.replace("{{" + key + "}}", value)
    return f"{template['system']}\n\n{rendered}"


# --- Apply helpers --------------------------------------------------------


def _entry_task_line_index(text: str, entry: JournalEntry) -> int:
    """0-based index into ``text.split('\\n')`` for the entry's Task line."""
    return entry.line_start - 1  # line_start is 1-based


def apply_mark_extended(text: str, entry: JournalEntry) -> str:
    """Insert ``[Extended]`` into entry's Task bold span. No-op if already marked."""
    lines = text.split("\n")
    idx = _entry_task_line_index(text, entry)
    if idx < 0 or idx >= len(lines):
        raise ValueError(f"entry {entry.number}: line {entry.line_start} out of range")
    line = lines[idx]
    if "[Extended]" in line:
        return text  # already marked, idempotent
    # Insert "[Extended] " after "**Task" and before " - " (or "-")
    # ENTRY_RE shape: `N. **Task - <title>** ...`
    pattern = re.compile(r"(\*\*Task)(\s*)(-)")
    new_line, count = pattern.subn(r"\1 [Extended] \3", line, count=1)
    if count != 1:
        raise ValueError(
            f"entry {entry.number}: could not locate '**Task - ' span in line {entry.line_start}"
        )
    lines[idx] = new_line
    return "\n".join(lines)


def apply_drop_marker(text: str, entry: JournalEntry) -> str:
    """Remove ``[Extended]`` from entry's Task bold span. No-op if not marked."""
    lines = text.split("\n")
    idx = _entry_task_line_index(text, entry)
    if idx < 0 or idx >= len(lines):
        raise ValueError(f"entry {entry.number}: line {entry.line_start} out of range")
    line = lines[idx]
    new_line = re.sub(r"\s*\[Extended\]\s*", " ", line, count=1, flags=re.IGNORECASE)
    # Collapse the double space that may result, but preserve indentation.
    new_line = re.sub(r"(\*\*Task)\s\s+", r"\1 ", new_line)
    lines[idx] = new_line
    return "\n".join(lines)


def apply_condense_body(text: str, entry: JournalEntry, new_body: str) -> str:
    """Replace the entry's Result body with ``new_body``.

    Preserves the leading indentation of the original `**Result**:` line
    and reflows the new body onto that same line (one paragraph per the
    journal format).
    """
    lines = text.split("\n")
    # Find the Result line within the entry's raw_lines span.
    start = _entry_task_line_index(text, entry)
    end = start + len(entry.raw_lines)
    result_idx = None
    result_indent_prefix = "    "
    for i in range(start, min(end, len(lines))):
        m = RESULT_PREFIX.match(lines[i])
        if m:
            result_idx = i
            indent_match = re.match(r"^(\s+)\*\*Result\*\*:\s*", lines[i])
            result_indent_prefix = indent_match.group(1) if indent_match else "    "
            break
    if result_idx is None:
        raise ValueError(f"entry {entry.number}: no `**Result**:` line found in span")

    # Replace the Result line + any continuation lines belonging to this
    # entry's body (everything up to `end`).
    new_body_clean = " ".join(new_body.split())  # collapse all internal whitespace
    new_result_line = f"{result_indent_prefix}**Result**: {new_body_clean}"
    new_lines = lines[:result_idx] + [new_result_line] + lines[end:]
    return "\n".join(new_lines)


_STANDARDIZE_CLEAN_COMMENT_RE = re.compile(r"<!--\s*standardize-clean:\s*\d{4}-\d{2}-\d{2}\s*-->")

_USAGE_POLICY_REFUSAL = "violate our Usage Policy"
_SONNET_4_MODEL = "claude-sonnet-4-20250514"
_SUBPROCESS_TIMEOUT_SECONDS = 180


def parse_standardize_decision(
    response: str,
    template: dict | None = None,
) -> tuple[str, str | None] | None:
    """Parse the subprocess response into ``(decision, body_or_None)``.

    Uses the ``decision_grammar`` block in the shipped standardize.yaml so
    the wire format stays the YAML's single source of truth. Returns
    ``None`` when the response matches no format - the caller should skip
    the entry with a SKIP log line.
    """
    if template is None:
        template = _load_standardize_prompt()
    grammar = template["decision_grammar"]
    for fmt in grammar["formats"]:
        flags = 0
        if fmt.get("multiline"):
            flags |= re.MULTILINE
        if fmt.get("dotall"):
            flags |= re.DOTALL
        m = re.search(fmt["regex"], response, flags)
        if m:
            body = m.group(fmt["body_group"]) if "body_group" in fmt else None
            return fmt["name"], body
    return None


def _spawn_standardize_subprocess(
    prompt: str,
    timeout: int = _SUBPROCESS_TIMEOUT_SECONDS,
) -> str | None:
    """Spawn ``claude -p`` to decide one entry.

    Returns the subprocess stdout text, or ``None`` on refusal / timeout /
    binary-missing. CLAUDECODE is stripped from the env (ACP rule:
    otherwise the SDK enters degraded mode and hangs on file ops). stderr
    is suppressed to drop the harmless "no stdin data received in 3s"
    leak. ``--no-session-persistence`` keeps the subprocess from writing
    a JSONL file under ``~/.claude/projects/<slug>/`` per entry - the
    standardize decisions are one-shot and never resumed, so persisting
    them is pure noise (one extra file per entry, 17+ per sweep).
    On ``violate our Usage Policy`` in the first response, retries once
    with ``--model claude-sonnet-4-20250514`` (sonnet-4 has a different
    safety profile and clears benign technical content the default
    model occasionally flags). Two refusals -> return None.
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    base_args = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "text",
        "--dangerously-skip-permissions",
        "--max-turns",
        "3",
        "--no-session-persistence",
    ]
    try:
        first = subprocess.run(
            base_args,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    out = first.stdout
    if _USAGE_POLICY_REFUSAL not in out:
        return out

    try:
        retry = subprocess.run(
            base_args + ["--model", _SONNET_4_MODEL],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    out = retry.stdout
    if _USAGE_POLICY_REFUSAL in out:
        return None
    return out


def _apply_one_decision(
    text: str,
    entry: JournalEntry,
    decision: str,
    new_body: str | None = None,
) -> tuple[str, str]:
    """Apply a parsed decision to the journal text. Returns ``(new_text, outcome)``.

    Mirrors the existing ``--apply`` argparse branch so ``--all`` can reuse
    the write logic without going through argparse. ``decision`` is one of
    ``"extended" / "condense" / "drop_marker" / "drop-marker"`` (both
    underscore and dash forms accepted for symmetry with the argparse
    surface).
    """
    decision = decision.replace("_", "-")
    if decision == "extended":
        return apply_mark_extended(text, entry), "marked Extended"
    if decision == "drop-marker":
        return apply_drop_marker(text, entry), "dropped [Extended] marker"
    if decision == "condense":
        if new_body is None:
            raise ValueError("condense decision requires new_body")
        new_text = apply_condense_body(text, entry, new_body)
        # When a previously-Extended body condenses below the Extended min,
        # the marker becomes false advertising — drop it. Same rule used by
        # the legacy --apply branch.
        if entry.is_extended:
            post_entries = parse_journal(new_text)
            post_target = next((e for e in post_entries if e.number == entry.number), None)
            if post_target is not None and post_target.body_word_count < EXTENDED_MIN:
                new_text = apply_drop_marker(new_text, post_target)
        return new_text, "condensed body"
    raise ValueError(f"unknown decision: {decision!r}")


def run_standardize_all(
    journal_path: Path,
    standard_target: int = STANDARD_TARGET,
    extended_max: int = EXTENDED_MAX,
    spawn: callable = _spawn_standardize_subprocess,
    today: str | None = None,
) -> int:
    """Walk every standardize candidate and apply decisions in one pass.

    Returns 0 if the final ``check_journal`` reports zero errors, 1
    otherwise. The ``spawn`` parameter lets tests inject a mock subprocess
    driver; production calls accept the module-level default.

    Process per candidate:
      - ``drop_marker`` actions apply immediately (no subprocess).
      - ``decide`` / ``condense`` actions spawn one ``claude -p`` per
        entry, parse via the YAML grammar, apply. Unparseable / refused /
        timed-out responses skip the entry and surface in the summary.

    After the loop, re-validates the file. On a fully clean validator
    exit (zero errors AND zero warnings), writes the ``standardize-clean``
    footer.
    """
    template = _load_standardize_prompt()
    text = journal_path.read_text(encoding="utf-8")
    entries = parse_journal(text)
    candidates = list_repair_candidates(
        entries,
        standard_target=standard_target,
        extended_max=extended_max,
    )
    if not candidates:
        # Nothing to do; still run the final validator + footer step.
        return _finalize_standardize(journal_path, standard_target, extended_max, [], today)

    summary: list[str] = []
    for cand in candidates:
        # Re-parse the file each iteration so line spans stay correct after
        # earlier applies.
        text = journal_path.read_text(encoding="utf-8")
        entries = parse_journal(text)
        entry = next((e for e in entries if e.number == cand["number"]), None)
        if entry is None:
            summary.append(f"entry {cand['number']}: SKIP (no longer in journal)")
            continue

        action = cand["action_needed"]
        if action == "drop_marker":
            new_text, _ = _apply_one_decision(text, entry, "drop-marker")
            journal_path.write_text(new_text, encoding="utf-8")
            post_entries = parse_journal(new_text)
            post = next((e for e in post_entries if e.number == entry.number), None)
            wc = post.body_word_count if post else entry.body_word_count
            summary.append(
                f"entry {entry.number}: dropped [Extended] marker -> now Standard ({wc} words)"
            )
            continue

        # decide or condense -> spawn subprocess
        prompt = render_standardize_prompt(entry, template=template)
        response = spawn(prompt)
        if response is None:
            summary.append(f"entry {entry.number}: SKIP (subprocess refused / timed out)")
            continue

        parsed = parse_standardize_decision(response, template=template)
        if parsed is None:
            summary.append(f"entry {entry.number}: SKIP (unparseable subprocess response)")
            continue

        decision, body = parsed
        try:
            new_text, _ = _apply_one_decision(text, entry, decision, new_body=body)
        except ValueError as exc:
            summary.append(f"entry {entry.number}: SKIP ({exc})")
            continue
        journal_path.write_text(new_text, encoding="utf-8")

        post_entries = parse_journal(new_text)
        post = next((e for e in post_entries if e.number == entry.number), None)
        wc = post.body_word_count if post else entry.body_word_count
        tier = "Extended" if (post and post.is_extended) else "Standard"
        if decision == "drop_marker":
            verb = "dropped marker"
        elif decision == "extended":
            verb = "marked Extended"
        else:
            verb = "condensed body"
        summary.append(f"entry {entry.number}: {verb} -> now {tier} ({wc} words)")

    return _finalize_standardize(journal_path, standard_target, extended_max, summary, today)


def _finalize_standardize(
    journal_path: Path,
    standard_target: int,
    extended_max: int,
    summary: list[str],
    today: str | None,
) -> int:
    """Print the per-entry summary, run the final validator, and write the
    standardize-clean footer when fully clean. Returns 0 on clean exit, 1 if
    any errors remain.
    """
    for line in summary:
        print(line)

    text = journal_path.read_text(encoding="utf-8")
    entries, parser_violations = parse_journal_with_diagnostics(text)
    violations = parser_violations + check_journal(
        entries,
        standard_target=standard_target,
        extended_max=extended_max,
    )
    errors = sum(1 for v in violations if v.severity == "error")
    warnings = sum(1 for v in violations if v.severity == "warning")

    if not violations:
        print(f"OK: {len(entries)} entries, no violations.")
        write_standardize_clean_footer(journal_path, date=today)
        return 0

    for v in violations:
        prefix = f"[{v.severity.upper()}]"
        label = f"entry {v.entry_number}" if v.entry_number else "global"
        print(f"{prefix} {label}: {v.message}")
    print(f"\n{len(entries)} entries, {errors} errors, {warnings} warnings.")
    return 1 if errors else 0


def write_standardize_clean_footer(
    journal_path: Path,
    date: str | None = None,
) -> None:
    """Idempotently write `<!-- standardize-clean: YYYY-MM-DD -->` near top.

    If the comment already exists anywhere in the file, its date is
    replaced in place. Otherwise the comment is inserted on the line after
    the journal's `**Note**:` line if present, or after the H1 title line.

    Called by `standardize --all` only after a clean validator exit (zero
    errors AND zero warnings) so forensics can grep `standardize-clean`
    across journals to find which have a recent standardize sweep.
    """
    if date is None:
        from datetime import date as _date

        date = _date.today().isoformat()

    text = journal_path.read_text(encoding="utf-8")
    new_comment = f"<!-- standardize-clean: {date} -->"

    if _STANDARDIZE_CLEAN_COMMENT_RE.search(text):
        text = _STANDARDIZE_CLEAN_COMMENT_RE.sub(new_comment, text)
        journal_path.write_text(text, encoding="utf-8")
        return

    lines = text.split("\n")
    insert_at: int | None = None
    for i, line in enumerate(lines):
        if line.startswith("**Note**:"):
            insert_at = i + 1
            break
    if insert_at is None:
        for i, line in enumerate(lines):
            if line.startswith("# "):
                insert_at = i + 1
                break
    if insert_at is None:
        insert_at = 0

    lines = lines[:insert_at] + [new_comment] + lines[insert_at:]
    journal_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``journal-tools check|archive|sort|standardize <path>``."""
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

    # standardize - identify and repair oversized / mis-marked entries via ACP
    p_std = sub.add_parser(
        "standardize",
        help="List, prompt-render, and apply repairs for oversized / mis-marked entries.",
        description=(
            "Four modes. --all is the recommended happy path - walks every "
            "flagged entry, spawns one focused `claude -p` subprocess per "
            "decision (with sonnet-4 fallback on usage-policy refusal), "
            "applies via the CLI, validates at the end. The other three "
            "are the manual procedure the /journal:standardize slash "
            "command used pre-`--all`: (1) --list emits a JSON array of "
            "entries needing repair; (2) --prompt N renders the per-entry "
            "ACP prompt from the shipped prompts/standardize.yaml; "
            "(3) --apply N --decision <extended|condense|drop-marker> "
            "writes the decision back to the file."
        ),
    )
    p_std.add_argument("path", help="Path to JOURNAL.md")
    p_std_mode = p_std.add_mutually_exclusive_group(required=True)
    p_std_mode.add_argument(
        "--all",
        action="store_true",
        dest="all_mode",
        help="Walk every candidate end-to-end in one invocation (recommended).",
    )
    p_std_mode.add_argument(
        "--list",
        action="store_true",
        help="Emit a JSON array of entries needing repair.",
    )
    p_std_mode.add_argument(
        "--prompt",
        type=int,
        metavar="N",
        help="Render the per-entry ACP prompt for entry N.",
    )
    p_std_mode.add_argument(
        "--apply",
        type=int,
        metavar="N",
        help="Apply the subprocess decision to entry N (requires --decision).",
    )
    p_std.add_argument(
        "--decision",
        choices=["extended", "condense", "drop-marker"],
        help="Decision to apply (only with --apply).",
    )
    p_std.add_argument(
        "--body-file",
        help="Path to a file containing the new Result body (only with --decision condense).",
    )
    p_std.add_argument(
        "--standard-target",
        type=int,
        default=STANDARD_TARGET,
        help=f"Word count target for Standard entries (default: {STANDARD_TARGET})",
    )
    p_std.add_argument(
        "--extended-max",
        type=int,
        default=EXTENDED_MAX,
        help=f"Word count ceiling for Extended entries (default: {EXTENDED_MAX})",
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
    entries, parser_violations = parse_journal_with_diagnostics(text)

    if args.command == "check":
        violations = parser_violations + check_journal(
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

    elif args.command == "standardize":
        import json as _json

        # --all: end-to-end orchestration; spawns one subprocess per
        # candidate, applies all decisions, validates, writes footer.
        if args.all_mode:
            return run_standardize_all(
                path,
                standard_target=args.standard_target,
                extended_max=args.extended_max,
            )

        # --list: emit JSON of repair candidates and exit.
        if args.list:
            candidates = list_repair_candidates(
                entries,
                standard_target=args.standard_target,
                extended_max=args.extended_max,
            )
            print(_json.dumps(candidates, indent=2))
            return 0

        # --prompt N: render the per-entry ACP prompt.
        if args.prompt is not None:
            target = next((e for e in entries if e.number == args.prompt), None)
            if target is None:
                print(f"ERROR: entry {args.prompt} not found", file=sys.stderr)
                return 1
            print(render_standardize_prompt(target))
            return 0

        # --apply N --decision ...: write the decision back to the file.
        if args.apply is not None:
            if args.decision is None:
                print("ERROR: --apply requires --decision", file=sys.stderr)
                return 1
            target = next((e for e in entries if e.number == args.apply), None)
            if target is None:
                print(f"ERROR: entry {args.apply} not found", file=sys.stderr)
                return 1
            if args.decision == "extended":
                new_text = apply_mark_extended(text, target)
                outcome = "marked Extended"
            elif args.decision == "drop-marker":
                new_text = apply_drop_marker(text, target)
                outcome = "dropped [Extended] marker"
            elif args.decision == "condense":
                if not args.body_file:
                    print("ERROR: --decision condense requires --body-file", file=sys.stderr)
                    return 1
                body_path = Path(args.body_file)
                if not body_path.exists():
                    print(f"ERROR: body file {body_path} not found", file=sys.stderr)
                    return 1
                new_body = body_path.read_text(encoding="utf-8")
                new_text = apply_condense_body(text, target, new_body)
                # If the condensed body falls back into the Standard band, the
                # `[Extended]` marker becomes false advertising - drop it.
                # Re-parse the post-write text so we operate on a fresh entry
                # at the same number with the right line positions.
                if target.is_extended:
                    post_entries = parse_journal(new_text)
                    post_target = next(
                        (e for e in post_entries if e.number == target.number), None
                    )
                    if post_target is not None and post_target.body_word_count < EXTENDED_MIN:
                        new_text = apply_drop_marker(new_text, post_target)
                outcome = "condensed body"
            else:
                print(f"ERROR: unknown decision {args.decision!r}", file=sys.stderr)
                return 1

            path.write_text(new_text, encoding="utf-8")

            # Re-parse + re-classify to report the post-state.
            new_entries = parse_journal(new_text)
            new_target = next((e for e in new_entries if e.number == args.apply), None)
            if new_target is None:
                print(f"WARNING: entry {args.apply} not found after write", file=sys.stderr)
                return 0
            tier = "Extended" if new_target.is_extended else "Standard"
            print(
                f"entry {args.apply}: {outcome} -> now {tier} ({new_target.body_word_count} words)"
            )
            return 0

        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
