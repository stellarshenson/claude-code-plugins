"""Tests for the journal-tools CLI Extended-marker convention.

The format introduced in plugins v1.4.17 lets entries opt in to the wider
~150-400 word band by tagging the Task line with `[Extended]`:

    134. **Task [Extended] - Architectural migration** (vX.Y.Z): summary
        **Result**: 250-400 word paragraph...

Marked entries get warned only when over `EXTENDED_MAX` or under
`EXTENDED_MIN` (false advertising). Unmarked entries default to Standard
(<= STANDARD_TARGET) and the gate suggests adding the marker if depth is
warranted.
"""

from __future__ import annotations

import textwrap

from stellars_claude_code_plugins.journal.journal_tools import (
    EXTENDED_MAX,
    EXTENDED_MIN,
    STANDARD_TARGET,
    check_journal,
    parse_journal,
)


HEADER = textwrap.dedent("""\
    # Claude Code Journal

    This journal tracks substantive work.

    ---

""")


def _entry(num: int, marker: str, words: int, title: str = "Demo task") -> str:
    """Build a synthetic entry with `words` worth of body."""
    body = " ".join(["word"] * words)
    return (
        f"{num}. **Task{marker} - {title}** (v0.1.0): one-line summary<br>\n"
        f"    **Result**: {body}\n"
    )


class TestExtendedMarkerParsing:
    def test_unmarked_entry(self):
        text = HEADER + _entry(1, "", 100)
        entries = parse_journal(text)
        assert len(entries) == 1
        assert entries[0].is_extended is False
        assert entries[0].title == "Demo task"

    def test_marked_extended_entry(self):
        text = HEADER + _entry(1, " [Extended]", 300)
        entries = parse_journal(text)
        assert len(entries) == 1
        assert entries[0].is_extended is True
        assert entries[0].title == "Demo task"

    def test_marker_case_insensitive(self):
        # ENTRY_RE has re.IGNORECASE so [extended] / [EXTENDED] also parse.
        text = HEADER + _entry(1, " [extended]", 300)
        entries = parse_journal(text)
        assert entries[0].is_extended is True


class TestExtendedMarkerValidation:
    """The new word-count rules:

    Unmarked entries (Standard):
      <= STANDARD_TARGET (150)         -> silent
      > STANDARD_TARGET, <= EXTENDED   -> warn, suggest [Extended]
      > EXTENDED_MAX (400)             -> warn, suggest [Extended] OR condense

    Marked [Extended] entries:
      < EXTENDED_MIN (150)             -> warn (false advertising)
      [EXTENDED_MIN, EXTENDED_MAX]     -> silent
      > EXTENDED_MAX (400)             -> warn (too long for any tier)
    """

    def test_unmarked_short_entry_silent(self):
        text = HEADER + _entry(1, "", 100)
        violations = check_journal(parse_journal(text))
        assert all(v.entry_number != 1 for v in violations)

    def test_unmarked_over_standard_suggests_marker(self):
        text = HEADER + _entry(1, "", STANDARD_TARGET + 50)
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs, "expected a warning for over-standard unmarked entry"
        assert "Task [Extended]" in msgs[0]

    def test_unmarked_over_extended_max_suggests_marker(self):
        text = HEADER + _entry(1, "", EXTENDED_MAX + 50)
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs
        assert "over extended max" in msgs[0]
        assert "Task [Extended]" in msgs[0]

    def test_marked_in_band_silent(self):
        # 300 words, marked [Extended] -> within [150, 400] band -> silent.
        text = HEADER + _entry(1, " [Extended]", 300)
        violations = check_journal(parse_journal(text))
        assert all(v.entry_number != 1 for v in violations), (
            f"expected no warnings for in-band Extended entry, got: "
            f"{[v.message for v in violations]}"
        )

    def test_marked_below_min_warns_false_advertising(self):
        text = HEADER + _entry(1, " [Extended]", EXTENDED_MIN - 50)
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs
        assert "marked [Extended]" in msgs[0]
        assert "drop the marker" in msgs[0]

    def test_marked_over_max_warns(self):
        text = HEADER + _entry(1, " [Extended]", EXTENDED_MAX + 50)
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs
        assert "even extended caps here" in msgs[0].lower()

    def test_marker_does_not_break_existing_format(self):
        # Mix of marked and unmarked - parser handles both, version tag is
        # extracted correctly from each.
        text = (
            HEADER
            + _entry(1, "", 100)
            + "\n"
            + _entry(2, " [Extended]", 300)
            + "\n"
            + _entry(3, "", 80)
        )
        entries = parse_journal(text)
        assert len(entries) == 3
        assert [e.is_extended for e in entries] == [False, True, False]
        assert [e.version_tag for e in entries] == ["v0.1.0"] * 3
