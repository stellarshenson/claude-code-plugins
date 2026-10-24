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

import pytest

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
        f"{num}. **Task {marker}- {title}** (v0.1.0): one-line summary<br>\n"
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

    def test_unmarked_over_extended_max_suggests_article(self):
        """Over the Extended ceiling, the validator no longer suggests adding
        the [Extended] marker (the entry would still warn since Extended caps
        at 400). Instead it points at `/journal:article` to extract the depth
        into a `docs/` article and slim the entry to a Standard summary."""
        text = HEADER + _entry(1, "", EXTENDED_MAX + 50)
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs
        assert "over extended max" in msgs[0]
        assert "docs/" in msgs[0]
        assert "/journal:article" in msgs[0]

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


# ---------------------------------------------------------------------------
# Result-marker structural checks (Task without Result, orphan Result,
# multiple Result markers per Task) - introduced in plugins v1.4.19
# ---------------------------------------------------------------------------


from stellars_claude_code_plugins.journal.journal_tools import (
    parse_journal_with_diagnostics,
)


def _task_no_result(num: int) -> str:
    return f"{num}. **Task - Demo** (v0.1.0): one-line summary\n"


def _task_with_result(num: int, body_words: int = 50) -> str:
    body = " ".join(["word"] * body_words)
    return f"{num}. **Task - Demo** (v0.1.0): one-line summary<br>\n    **Result**: {body}\n"


def _task_with_multiple_results(num: int) -> str:
    return (
        f"{num}. **Task - Demo** (v0.1.0): one-line summary<br>\n"
        f"    **Result**: first result paragraph here\n"
        f"    **Result**: second result paragraph here\n"
    )


def _orphan_result_block() -> str:
    return "    **Result**: this has no Task above it\n"


class TestStructuralResultMarkerChecks:
    def test_task_without_result_marker_flagged(self):
        text = HEADER + _task_no_result(1)
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        # The error message about missing Result marker fires.
        assert any("no `**Result**:` marker" in m for m in msgs), (
            f"expected missing-Result-marker error; got: {msgs}"
        )
        # Severity is error, not warning.
        errors = [v for v in violations if v.entry_number == 1 and v.severity == "error"]
        assert errors

    def test_task_with_result_but_empty_body_warns_not_errors(self):
        # The Task has the marker but the body is empty - should be a
        # warning, not the new structural error.
        text = HEADER + f"1. **Task - Demo** (v0.1.0): summary<br>\n    **Result**:\n"
        violations = check_journal(parse_journal(text))
        msgs = [(v.severity, v.message) for v in violations if v.entry_number == 1]
        # NO structural error for marker absence.
        assert not any("no `**Result**:` marker" in m for _s, m in msgs)
        # But the empty-body warning DOES fire.
        assert any(s == "warning" and "body is empty" in m for s, m in msgs), (
            f"expected empty-body warning; got: {msgs}"
        )

    def test_orphan_result_outside_entry_flagged(self):
        # **Result**: line before any Task line - the parser used to silently
        # absorb these; now we flag them as parser-level errors.
        text = HEADER + _orphan_result_block() + _task_with_result(1)
        entries, parser_violations = parse_journal_with_diagnostics(text)
        assert len(entries) == 1
        # Exactly one parser violation, severity error.
        assert len(parser_violations) == 1
        assert parser_violations[0].severity == "error"
        assert "orphan **Result**:" in parser_violations[0].message
        # Line number points at the orphan line (line 7 after the header).
        assert "line " in parser_violations[0].message

    def test_multiple_result_markers_in_one_entry_flagged(self):
        text = HEADER + _task_with_multiple_results(1)
        entries = parse_journal(text)
        assert len(entries) == 1
        # The entry now carries result_marker_count = 2 so check_journal
        # surfaces a structural error.
        assert entries[0].result_marker_count == 2
        violations = check_journal(entries)
        msgs = [v.message for v in violations if v.entry_number == 1 and v.severity == "error"]
        assert any("2 `**Result**:` markers" in m for m in msgs), (
            f"expected multi-marker error; got: {msgs}"
        )

    def test_normal_one_task_one_result_passes(self):
        text = HEADER + _task_with_result(1) + "\n" + _task_with_result(2)
        entries, parser_violations = parse_journal_with_diagnostics(text)
        violations = check_journal(entries)
        # No parser violations.
        assert parser_violations == []
        # No structural Result-marker errors on either entry.
        for entry_num in (1, 2):
            errors = [
                v for v in violations if v.entry_number == entry_num and v.severity == "error"
            ]
            assert not errors, f"entry {entry_num} unexpected errors: {errors}"

    def test_result_marker_count_populated_on_entries(self):
        # Parser populates result_marker_count even on the back-compat path.
        text = HEADER + _task_no_result(1) + _task_with_result(2) + _task_with_multiple_results(3)
        entries = parse_journal(text)
        assert [e.result_marker_count for e in entries] == [0, 1, 2]


class TestStandardize:
    """`journal-tools standardize` - identify + repair oversized / mis-marked entries.

    Three deterministic actions wrap the ACP repair loop:
    - drop_marker: spurious `[Extended]` on a sub-150-word body (no subprocess)
    - mark-extended: depth is real, add the marker
    - condense: oversized body + new shorter body from the subprocess; marker
      auto-drops if condensed body falls into Standard.
    """

    def _journal(self, *raws: str) -> str:
        return HEADER + "".join(raws)

    def test_list_classifies_three_actions(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            list_repair_candidates,
        )

        # 1: ok Standard. 2: needs decide. 3: spurious marker. 4: condense.
        text = self._journal(
            _entry(1, marker="", words=80),
            _entry(2, marker="", words=200),
            _entry(3, marker="[Extended] ", words=30),
            _entry(4, marker="[Extended] ", words=450),
        )
        candidates = list_repair_candidates(parse_journal(text))
        by_num = {c["number"]: c["action_needed"] for c in candidates}
        assert by_num == {2: "decide", 3: "drop_marker", 4: "condense"}
        c2 = next(c for c in candidates if c["number"] == 2)
        assert c2["body"], "body must be populated"
        assert "**Task" in c2["task_line"]

    def test_render_prompt_substitutes_placeholders(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            _load_standardize_prompt,
            render_standardize_prompt,
        )

        text = self._journal(_entry(7, marker="", words=200, title="Probe entry"))
        entry = parse_journal(text)[0]
        template = _load_standardize_prompt()
        rendered = render_standardize_prompt(entry, template)
        assert "standardizer for the Stellars" in rendered
        assert "Entry number: 7" in rendered
        assert "Current word count: 200" in rendered
        assert "Has `[Extended]` marker already: false" in rendered
        assert "DECISION: EXTENDED" in rendered
        assert "DECISION: CONDENSE" in rendered
        assert "DECISION: DROP_MARKER" in rendered

    def test_load_prompt_yaml_ships_in_wheel(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            STANDARDIZE_YAML_VERSION,
            _load_standardize_prompt,
        )

        data = _load_standardize_prompt()
        assert data["version"] == STANDARDIZE_YAML_VERSION
        assert "system" in data and "user_template" in data
        assert "limits" not in data  # nothing read it; the tiers live in journal_tools.py

    def test_rubric_includes_rule_3b_ceiling(self):
        """Rule 3b — unmarked >400 must CONDENSE (single-pass fix from kolomolo
        forensics: rule 3 used to have no upper bound, returning EXTENDED for
        460-word bodies that then needed a second pass to clear)."""
        from stellars_claude_code_plugins.journal.journal_tools import (
            _load_standardize_prompt,
        )

        data = _load_standardize_prompt()
        template_text = data["user_template"]
        assert "word_count <= 400" in template_text
        assert "word_count > 400" in template_text
        assert "caps at 400" in template_text

    def test_apply_mark_extended_inserts_marker(self):
        from stellars_claude_code_plugins.journal.journal_tools import apply_mark_extended

        text = self._journal(_entry(1, marker="", words=200, title="X"))
        entry = parse_journal(text)[0]
        out = apply_mark_extended(text, entry)
        assert "**Task [Extended] - X**" in out
        again = apply_mark_extended(out, parse_journal(out)[0])
        assert again == out

    def test_apply_drop_marker_removes_marker(self):
        from stellars_claude_code_plugins.journal.journal_tools import apply_drop_marker

        text = self._journal(_entry(1, marker="[Extended] ", words=30, title="X"))
        entry = parse_journal(text)[0]
        out = apply_drop_marker(text, entry)
        assert "[Extended]" not in out
        again = apply_drop_marker(out, parse_journal(out)[0])
        assert again == out

    def test_apply_condense_body_replaces_result(self):
        from stellars_claude_code_plugins.journal.journal_tools import apply_condense_body

        text = self._journal(_entry(1, marker="", words=500, title="X"))
        entry = parse_journal(text)[0]
        new_body = "Short rewrite. Trigger: bloat. Why: brevity. Result: passes."
        out = apply_condense_body(text, entry, new_body)
        new_entry = parse_journal(out)[0]
        assert new_entry.result_body == new_body
        result_lines = [line for line in out.split("\n") if line.lstrip().startswith("**Result")]
        assert len(result_lines) == 1

    def test_apply_condense_body_stops_at_the_entry_boundary(self):
        from stellars_claude_code_plugins.journal.journal_tools import apply_condense_body

        text = (
            self._journal(_entry(1, marker="", words=500, title="X"))
            + "\n## 2026-08 August\n\n"
            + _entry(2, marker="", words=60, title="Y")
            + "\n<!-- standardize-clean -->\n"
        )
        entries = parse_journal(text)
        out = apply_condense_body(text, entries[0], "Short rewrite of one.")
        out = apply_condense_body(out, parse_journal(out)[1], "Short rewrite of two.")
        assert "## 2026-08 August" in out
        assert "<!-- standardize-clean -->" in out
        assert [e.result_body for e in parse_journal(out)] == [
            "Short rewrite of one.",
            "Short rewrite of two.",
        ]

    def test_cli_apply_extended_via_subprocess(self, tmp_path):
        import json
        import subprocess
        import sys

        journal = tmp_path / "J.md"
        journal.write_text(self._journal(_entry(1, marker="", words=200, title="X")))

        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "stellars_claude_code_plugins.journal.journal_tools",
                "standardize",
                str(journal),
                "--list",
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        candidates = json.loads(r.stdout)
        assert candidates[0]["number"] == 1
        assert candidates[0]["action_needed"] == "decide"

        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "stellars_claude_code_plugins.journal.journal_tools",
                "standardize",
                str(journal),
                "--apply",
                "1",
                "--decision",
                "extended",
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert "now Extended" in r.stdout
        assert "[Extended]" in journal.read_text()

    def test_cli_condense_auto_drops_marker_when_body_becomes_standard(self, tmp_path):
        import subprocess
        import sys

        journal = tmp_path / "J.md"
        journal.write_text(self._journal(_entry(1, marker="[Extended] ", words=500, title="X")))
        body = tmp_path / "new.txt"
        body.write_text("Tight rewrite. Trigger: bloat. Why: testing the auto-drop path.")

        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "stellars_claude_code_plugins.journal.journal_tools",
                "standardize",
                str(journal),
                "--apply",
                "1",
                "--decision",
                "condense",
                "--body-file",
                str(body),
            ],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        text = journal.read_text()
        assert "[Extended]" not in text
        assert "now Standard" in r.stdout


class TestSortPreservesExtendedMarker:
    """`sort_entries` + `render_entries` round-trip must preserve `[Extended]`.

    Earlier the `JournalEntry` reconstruction in `sort_entries` dropped
    `is_extended` (default False) and `render_entries` hard-coded
    `**Task -` with no marker, so any `journal-tools sort` run silently
    stripped Extended markers and fired over-150 warnings on the next
    `check` (the entries were correctly long for their tier, but the
    marker had been stripped). Caught preemptively before it bit
    production.
    """

    def _journal(self, *raws: str) -> str:
        return HEADER + "".join(raws)

    def test_render_emits_marker(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            render_entries,
        )

        text = HEADER + _entry(1, marker="[Extended] ", words=200, title="Real depth")
        entries = parse_journal(text)
        rendered = render_entries(entries)
        assert "**Task [Extended] - Real depth**" in rendered

    def test_render_omits_marker_for_standard(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            render_entries,
        )

        text = HEADER + _entry(1, marker="", words=100, title="Standard work")
        entries = parse_journal(text)
        rendered = render_entries(entries)
        assert "**Task - Standard work**" in rendered
        assert "[Extended]" not in rendered

    def test_sort_is_idempotent_on_the_header_gap(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import main

        path = tmp_path / "JOURNAL.md"
        path.write_text(
            self._journal(_entry(1, marker="", words=60), "\n", _entry(2, marker="", words=60))
        )
        for _ in range(3):
            assert main(["sort", str(path)]) == 0
        assert path.read_text().count("\n\n\n") == 0
        bare = tmp_path / "BARE.md"
        bare.write_text(_entry(1, marker="", words=60))
        assert main(["sort", str(bare)]) == 0
        assert bare.read_text().startswith("1. **Task")

    def test_sort_keeps_an_archived_journal_numbered_from_its_first_entry(self, tmp_path):
        """DEF-JRNL-34. After archiving, a journal starts at entry 110; a bare sort
        renumbered it from 1, one missed flag away from rewriting every reference."""
        from stellars_claude_code_plugins.journal.journal_tools import main

        path = tmp_path / "JOURNAL.md"
        path.write_text(
            self._journal(_entry(110, marker="", words=60), "\n", _entry(112, marker="", words=60))
        )
        assert main(["sort", str(path)]) == 0
        numbers = [e.number for e in parse_journal(path.read_text())]
        assert numbers == [110, 111]
        assert main(["sort", str(path), "--start-from", "1"]) == 0
        assert [e.number for e in parse_journal(path.read_text())] == [1, 2]

    def test_sort_preserves_marker_on_renumber(self):
        """Mixed-tier entries renumbered: each entry keeps its marker."""
        from stellars_claude_code_plugins.journal.journal_tools import (
            render_entries,
            sort_entries,
        )

        text = (
            HEADER
            + _entry(3, marker="[Extended] ", words=200, title="Architectural")
            + _entry(1, marker="", words=100, title="Quick fix")
            + _entry(2, marker="[Extended] ", words=250, title="Multi-thread release")
        )
        entries = parse_journal(text)
        sorted_entries = sort_entries(entries)
        rendered = render_entries(sorted_entries)
        # Entry 1 (originally 1) keeps Standard
        assert "1. **Task - Quick fix**" in rendered
        # Entry 2 (originally 2) keeps Extended
        assert "2. **Task [Extended] - Multi-thread release**" in rendered
        # Entry 3 (originally 3) keeps Extended
        assert "3. **Task [Extended] - Architectural**" in rendered

    def test_sort_round_trip_validator_clean(self):
        """End-to-end: write -> parse -> sort -> render -> parse -> check
        should leave Extended entries silent in [150, 400] (not warn)."""
        from stellars_claude_code_plugins.journal.journal_tools import (
            render_entries,
            sort_entries,
        )

        text = HEADER + _entry(1, marker="[Extended] ", words=250, title="Real depth")
        entries = parse_journal(text)
        rendered = HEADER + render_entries(sort_entries(entries)) + "\n"
        reparsed = parse_journal(rendered)
        assert reparsed[0].is_extended is True
        # No word-count warning because marker preserved
        violations = check_journal(reparsed)
        assert not any("over Standard target" in v.message for v in violations)


class TestStandardFloorWarning:
    """`STANDARD_MIN = 50` floor warning + `[Short]` marker opt-out.

    Tier ladder:
      - 1-49 words unmarked   -> warn "too terse, add [Short] or expand"
      - 1-49 words [Short]    -> silent (intentionally brief)
      - 50+ words [Short]     -> warn "marker is false advertising, drop it"
      - 50-150 words unmarked -> silent (Standard sweet spot)
    """

    def _journal(self, *raws: str) -> str:
        return HEADER + "".join(raws)

    def test_sub_50_unmarked_warns(self):
        text = self._journal(_entry(1, marker="", words=30, title="Terse"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations]
        assert any("under Standard min 50" in m for m in msgs)
        # Advice mentions the [Short] marker as the cheap fix
        assert any("[Short]" in m for m in msgs)

    def test_50_words_exactly_no_warning(self):
        text = self._journal(_entry(1, marker="", words=50, title="Threshold"))
        violations = check_journal(parse_journal(text))
        assert not any("under Standard min" in v.message for v in violations)

    def test_extended_marker_under_50_uses_extended_min_path(self):
        """Marker + 30-word body should fire the existing extended-min warning,
        not the new STANDARD_MIN warning (they would overlap otherwise)."""
        text = self._journal(_entry(1, marker="[Extended] ", words=30, title="Marked"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations]
        assert any("marked [Extended]" in m for m in msgs)
        assert not any("under Standard min" in m for m in msgs)


class TestShortMarker:
    """`[Short]` marker - intentionally brief opt-out for the sub-50 band."""

    def _journal(self, *raws: str) -> str:
        return HEADER + "".join(raws)

    def test_parser_recognises_short_marker(self):
        text = self._journal(_entry(1, marker="[Short] ", words=30, title="Typo fix"))
        entries = parse_journal(text)
        assert len(entries) == 1
        assert entries[0].is_short is True
        assert entries[0].is_extended is False

    def test_parser_case_insensitive(self):
        text = self._journal(_entry(1, marker="[short] ", words=30, title="X"))
        entries = parse_journal(text)
        assert entries[0].is_short is True

    def test_short_marker_under_50_silent(self):
        text = self._journal(_entry(1, marker="[Short] ", words=30, title="Typo"))
        violations = check_journal(parse_journal(text))
        assert all(v.entry_number != 1 for v in violations), (
            f"expected no warnings for marked [Short] sub-50 entry, got: "
            f"{[v.message for v in violations]}"
        )

    def test_short_marker_at_50_warns_false_advertising(self):
        text = self._journal(_entry(1, marker="[Short] ", words=50, title="Over"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs
        assert "marked [Short]" in msgs[0]
        assert "Drop the marker" in msgs[0]

    def test_short_marker_at_100_warns_false_advertising(self):
        text = self._journal(_entry(1, marker="[Short] ", words=100, title="Over"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert any("marked [Short]" in m for m in msgs)

    def test_render_emits_short_marker(self):
        from stellars_claude_code_plugins.journal.journal_tools import render_entries

        text = self._journal(_entry(1, marker="[Short] ", words=30, title="Typo"))
        entries = parse_journal(text)
        rendered = render_entries(entries)
        assert "**Task [Short] - Typo**" in rendered

    def test_sort_preserves_short_marker(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            render_entries,
            sort_entries,
        )

        text = self._journal(
            _entry(2, marker="[Short] ", words=30, title="Quick fix"),
            _entry(1, marker="", words=100, title="Standard work"),
        )
        entries = parse_journal(text)
        rendered = render_entries(sort_entries(entries))
        assert "1. **Task - Standard work**" in rendered
        assert "2. **Task [Short] - Quick fix**" in rendered


class TestOverMaxArticleAdvice:
    """Validator advice on >400-word entries points at `/journal:article`."""

    def _journal(self, *raws: str) -> str:
        return HEADER + "".join(raws)

    def test_unmarked_over_400_suggests_article(self):
        text = self._journal(_entry(1, marker="", words=500, title="Sprawling"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs
        assert "docs/" in msgs[0]
        assert "/journal:article" in msgs[0]

    def test_extended_over_400_suggests_article(self):
        text = self._journal(_entry(1, marker="[Extended] ", words=500, title="Marked"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations if v.entry_number == 1]
        assert msgs
        # Same article advice fires for both the marked and unmarked over-max
        # branches - they go through the shared `article_advice` string.
        assert "docs/" in msgs[0]
        assert "/journal:article" in msgs[0]


class TestStandardizeCleanFooter:
    """`write_standardize_clean_footer` writes `<!-- standardize-clean: DATE -->`
    near the journal top, idempotently.

    Forensics need: agents and humans want a one-grep answer to "when was
    this journal last standardize-cleaned." Inserted only when validator
    is fully clean (driven by `--all`, not by this helper directly).
    """

    def _bare(self) -> str:
        return "# Claude Code Journal\n\nIntro paragraph.\n\n---\n\n1. **Task - X** (v0.1.0): summary<br>\n    **Result**: body\n"

    def _with_note(self) -> str:
        return (
            "# Claude Code Journal\n\nIntro paragraph.\n\n"
            "**Note**: Entries 1-50 archived to [JOURNAL_ARCHIVE.md].\n\n"
            "---\n\n51. **Task - X** (v0.1.0): summary<br>\n    **Result**: body\n"
        )

    def test_inserts_after_note_line(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import (
            write_standardize_clean_footer,
        )

        journal = tmp_path / "J.md"
        journal.write_text(self._with_note())
        write_standardize_clean_footer(journal, date="2026-05-14")
        text = journal.read_text()
        assert "<!-- standardize-clean: 2026-05-14 -->" in text
        # Must land after the **Note** line, before the entries
        note_idx = text.find("**Note**:")
        comment_idx = text.find("<!-- standardize-clean:")
        entry_idx = text.find("\n51.")
        assert note_idx < comment_idx < entry_idx

    def test_inserts_after_h1_when_no_note(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import (
            write_standardize_clean_footer,
        )

        journal = tmp_path / "J.md"
        journal.write_text(self._bare())
        write_standardize_clean_footer(journal, date="2026-05-14")
        text = journal.read_text()
        assert "<!-- standardize-clean: 2026-05-14 -->" in text
        h1_idx = text.find("# Claude Code Journal")
        comment_idx = text.find("<!-- standardize-clean:")
        assert h1_idx < comment_idx

    def test_replaces_existing_date_in_place(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import (
            write_standardize_clean_footer,
        )

        journal = tmp_path / "J.md"
        journal.write_text(self._bare())
        write_standardize_clean_footer(journal, date="2026-01-01")
        write_standardize_clean_footer(journal, date="2026-05-14")
        text = journal.read_text()
        # Old date gone, new date present, only one comment in file
        assert "2026-01-01" not in text
        assert text.count("<!-- standardize-clean:") == 1
        assert "<!-- standardize-clean: 2026-05-14 -->" in text


class TestStandardizeAll:
    """`run_standardize_all` orchestrates list → render → spawn → apply → check.

    Driven by the kolomolo session forensics finding (51 invocations, 1
    full procedure executed) that agents drop after enqueueing the skill.
    `--all` collapses the 5-step manual procedure into one CLI call.

    Tests use a stub `spawn` callable so the actual subprocess is never
    invoked; the production driver `_spawn_standardize_subprocess` is
    covered by its own test.
    """

    def _journal(self, *raws: str) -> str:
        return HEADER + "".join(raws)

    def test_no_candidates_writes_footer(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import (
            run_standardize_all,
        )

        journal = tmp_path / "J.md"
        # 100 words, no marker -> Standard, no candidates, no warnings
        journal.write_text(self._journal(_entry(1, marker="", words=100, title="OK")))
        rc = run_standardize_all(journal, today="2026-05-14")
        assert rc == 0
        text = journal.read_text()
        assert "<!-- standardize-clean: 2026-05-14 -->" in text

    def test_extended_decision_applied(self, tmp_path, capsys):
        from stellars_claude_code_plugins.journal.journal_tools import (
            run_standardize_all,
        )

        journal = tmp_path / "J.md"
        # 200 words unmarked -> "decide" candidate; mock subprocess returns EXTENDED
        journal.write_text(self._journal(_entry(1, marker="", words=200, title="Real depth")))
        rc = run_standardize_all(
            journal,
            spawn=lambda prompt: "DECISION: EXTENDED\n",
            today="2026-05-14",
        )
        assert rc == 0
        text = journal.read_text()
        assert "**Task [Extended] - Real depth**" in text

    def test_condense_decision_applied(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import (
            run_standardize_all,
        )

        journal = tmp_path / "J.md"
        # 500 words unmarked -> over-Standard; mock returns CONDENSE+short body
        journal.write_text(self._journal(_entry(1, marker="", words=500, title="Bloated")))
        new_body = " ".join(["word"] * 100)
        rc = run_standardize_all(
            journal,
            spawn=lambda prompt: f"DECISION: CONDENSE\nBODY:\n{new_body}",
            today="2026-05-14",
        )
        # Standard at 100 words is acceptable; footer should land
        assert rc == 0
        entries = parse_journal(journal.read_text())
        assert entries[0].body_word_count == 100

    def test_drop_marker_no_subprocess(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import (
            run_standardize_all,
        )

        journal = tmp_path / "J.md"
        # marker + 30 words -> drop_marker action, no subprocess needed
        journal.write_text(self._journal(_entry(1, marker="[Extended] ", words=30, title="Thin")))
        spawn_calls = []

        def stub_spawn(prompt):
            spawn_calls.append(prompt)
            return "DECISION: EXTENDED\n"  # should NOT fire

        rc = run_standardize_all(journal, spawn=stub_spawn, today="2026-05-14")
        # The thin marker drops, leaving a 30-word entry -> STANDARD_MIN
        # warning fires, footer skipped, rc=0 (no errors).
        assert rc == 0
        assert "[Extended]" not in journal.read_text()
        # No subprocess spawned for drop_marker
        assert spawn_calls == []

    def test_unparseable_response_skips_entry(self, tmp_path, capsys):
        from stellars_claude_code_plugins.journal.journal_tools import (
            run_standardize_all,
        )

        journal = tmp_path / "J.md"
        journal.write_text(self._journal(_entry(1, marker="", words=200, title="X")))
        rc = run_standardize_all(
            journal,
            spawn=lambda prompt: "this is not a valid decision response at all",
            today="2026-05-14",
        )
        captured = capsys.readouterr()
        assert "SKIP (unparseable" in captured.out
        # Entry unchanged (still 200 words, no marker -> validator warns)
        # So rc may be 0 (warnings only).
        assert rc == 0
        text = journal.read_text()
        assert "[Extended]" not in text

    def test_subprocess_refusal_skips_entry(self, tmp_path, capsys):
        from stellars_claude_code_plugins.journal.journal_tools import (
            run_standardize_all,
        )

        journal = tmp_path / "J.md"
        journal.write_text(self._journal(_entry(1, marker="", words=200, title="X")))
        # spawn returning None mirrors what _spawn_standardize_subprocess does
        # after both default-model and sonnet-4 refusals.
        rc = run_standardize_all(journal, spawn=lambda prompt: None, today="2026-05-14")
        captured = capsys.readouterr()
        assert "SKIP (subprocess refused" in captured.out
        assert rc == 0


class TestSpawnSubprocessSoftLanding:
    """`_spawn_standardize_subprocess` retries with sonnet-4 on usage-policy
    refusal. Patches `subprocess.run` so the test never spawns claude.
    """

    def test_default_model_success(self, monkeypatch):
        from stellars_claude_code_plugins.journal import journal_tools

        calls = []

        class StubResult:
            stdout = "DECISION: EXTENDED\n"

        def fake_run(args, **kwargs):
            calls.append(args)
            return StubResult()

        monkeypatch.setattr(journal_tools.subprocess, "run", fake_run)
        out = journal_tools._spawn_standardize_subprocess("prompt-text")
        assert out == "DECISION: EXTENDED\n"
        assert len(calls) == 1
        # Default model call has no --model flag
        assert "--model" not in calls[0]
        # Session persistence MUST be disabled - otherwise each one-shot
        # standardize decision (17+ per sweep) writes a JSONL session file
        # under ~/.claude/projects/<slug>/ that no one ever resumes.
        assert "--no-session-persistence" in calls[0]

    def test_usage_policy_refusal_retries_sonnet_4(self, monkeypatch):
        from stellars_claude_code_plugins.journal import journal_tools

        calls = []

        class FirstResult:
            stdout = "API Error: violate our Usage Policy ..."

        class SecondResult:
            stdout = "DECISION: EXTENDED\n"

        responses = [FirstResult(), SecondResult()]

        def fake_run(args, **kwargs):
            calls.append(args)
            return responses.pop(0)

        monkeypatch.setattr(journal_tools.subprocess, "run", fake_run)
        out = journal_tools._spawn_standardize_subprocess("prompt-text")
        assert out == "DECISION: EXTENDED\n"
        assert len(calls) == 2
        # First call: no --model. Second call: --model sonnet - an alias, because a
        # dated id is withdrawn (claude-sonnet-4-20250514 was, 2026-06-15; DEF-JRNL-78)
        assert "--model" not in calls[0]
        assert "--model" in calls[1]
        assert calls[1][calls[1].index("--model") + 1] == "sonnet"

    def test_both_models_refuse_returns_none(self, monkeypatch):
        from stellars_claude_code_plugins.journal import journal_tools

        class Refusal:
            stdout = "API Error: violate our Usage Policy ..."

        def fake_run(args, **kwargs):
            return Refusal()

        monkeypatch.setattr(journal_tools.subprocess, "run", fake_run)
        out = journal_tools._spawn_standardize_subprocess("prompt-text")
        assert out is None

    def test_timeout_returns_none(self, monkeypatch):
        from stellars_claude_code_plugins.journal import journal_tools

        def fake_run(args, **kwargs):
            raise journal_tools.subprocess.TimeoutExpired(cmd=args, timeout=180)

        monkeypatch.setattr(journal_tools.subprocess, "run", fake_run)
        out = journal_tools._spawn_standardize_subprocess("prompt-text")
        assert out is None

    def test_claude_binary_missing_returns_none(self, monkeypatch):
        from stellars_claude_code_plugins.journal import journal_tools

        def fake_run(args, **kwargs):
            raise FileNotFoundError("claude")

        monkeypatch.setattr(journal_tools.subprocess, "run", fake_run)
        out = journal_tools._spawn_standardize_subprocess("prompt-text")
        assert out is None


class TestParseStandardizeDecision:
    """`parse_standardize_decision` uses the YAML grammar to parse subprocess
    output into a structured `(decision, body_or_None)` tuple."""

    def test_extended(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            parse_standardize_decision,
        )

        result = parse_standardize_decision("DECISION: EXTENDED\n")
        assert result == ("extended", None)

    def test_condense_extracts_body(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            parse_standardize_decision,
        )

        text = "DECISION: CONDENSE\nBODY:\nNew condensed body text here."
        result = parse_standardize_decision(text)
        assert result is not None
        decision, body = result
        assert decision == "condense"
        assert body == "New condensed body text here."

    def test_drop_marker(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            parse_standardize_decision,
        )

        result = parse_standardize_decision("DECISION: DROP_MARKER\n")
        assert result == ("drop_marker", None)

    def test_unparseable_returns_none(self):
        from stellars_claude_code_plugins.journal.journal_tools import (
            parse_standardize_decision,
        )

        result = parse_standardize_decision("I have an opinion but no decision tag")
        assert result is None


class TestYamlVersionRefusal:
    """The CLI hard-fails when the shipped YAML's `version` does not match
    `STANDARDIZE_YAML_VERSION`. Tests an in-process override of the loader's
    YAML source to simulate version drift.
    """

    def test_unknown_version_raises(self, monkeypatch):
        import yaml

        from stellars_claude_code_plugins.journal import journal_tools

        # Force loader to read an old-v1 YAML body
        old_yaml = yaml.safe_dump(
            {
                "version": 1,
                "limits": {"standard_target": 150, "extended_min": 150, "extended_max": 400},
                "system": "stub",
                "user_template": "stub",
                "decision_grammar": {"formats": []},
            }
        )

        class FakeRef:
            def read_text(self, encoding):
                return old_yaml

        class FakeFiles:
            def joinpath(self, name):
                return FakeRef()

        import importlib

        def fake_files(pkg):
            return FakeFiles()

        monkeypatch.setattr(importlib.resources, "files", fake_files)

        import pytest

        with pytest.raises(RuntimeError, match="standardize.yaml version"):
            journal_tools._load_standardize_prompt()


def test_the_standardize_prompt_states_the_validators_standard_band():
    """DEF-JRNL-36. The prompt told the repair subprocess to rewrite to 70-150 words
    after the validator's Standard floor had moved to 50."""
    from importlib.resources import files

    from stellars_claude_code_plugins.journal.journal_tools import STANDARD_MIN, STANDARD_TARGET

    text = (files("stellars_claude_code_plugins.journal") / "prompts/standardize.yaml").read_text()
    assert f"{STANDARD_MIN}-{STANDARD_TARGET} words" in text
    assert "70-150" not in text


def test_no_shipped_file_names_the_retired_sonnet_4_id():
    """DEF-JRNL-78. The standardize fallback and its docs pinned
    claude-sonnet-4-20250514, which the CLI reports retired on 2026-06-15."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    retired = "claude-sonnet-4-" + "20250514"
    shipped = [p for d in ("plugins", "src") for p in (root / d).rglob("*") if p.is_file()]
    hits = [
        str(p.relative_to(root))
        for p in shipped
        if p.suffix in {".md", ".py", ".yaml", ".js"}
        and retired in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not hits, hits


class TestLinkedJournal:
    """A journal kept in `.agents/JOURNAL.md` and reached through the link
    `.claude/JOURNAL.md -> ../.agents/JOURNAL.md`.

    Every command that writes the journal writes through the link: the link
    stays a link and the real file receives the text (ACC-JRNL-267-LINK-KEPT).
    `archive` writes JOURNAL_ARCHIVE.md beside the real file, where the
    journal's relative archive link points (ACC-JRNL-266-ARCHIVE-LINK).
    """

    def _project(self, tmp_path, text: str):
        """Write `text` to .agents/JOURNAL.md, link .claude/JOURNAL.md to it."""
        real = tmp_path / ".agents" / "JOURNAL.md"
        real.parent.mkdir()
        real.write_text(text)
        link = tmp_path / ".claude" / "JOURNAL.md"
        link.parent.mkdir()
        link.symlink_to("../.agents/JOURNAL.md")
        return link, real

    def _assert_link_kept(self, link):
        import os

        assert link.is_symlink()
        assert os.readlink(link) == "../.agents/JOURNAL.md"

    def _assert_archived_beside_real(self, tmp_path, link, real):
        import os
        import re

        archive = tmp_path / ".agents" / "JOURNAL_ARCHIVE.md"
        claude_archive = tmp_path / ".claude" / "JOURNAL_ARCHIVE.md"
        self._assert_link_kept(link)
        # no real archive in .claude/; the CLI leaves the layout link there (ACC-JRNL-268-LAYOUT-NEW)
        assert not os.path.lexists(claude_archive) or claude_archive.is_symlink()
        assert [e.number for e in parse_journal(archive.read_text())] == list(range(1, 22))
        assert [e.number for e in parse_journal(real.read_text())] == list(range(22, 42))
        target = re.search(r"\[JOURNAL_ARCHIVE\.md\]\(([^)]+)\)", real.read_text()).group(1)
        assert (real.parent / target).samefile(archive)

    def _many(self) -> str:
        return HEADER + "".join(_entry(n, marker="", words=60) for n in range(1, 42))

    def test_archive_writes_the_archive_beside_the_real_journal(self, tmp_path):
        from pathlib import Path

        from stellars_claude_code_plugins.journal.journal_tools import archive_journal

        link, real = self._project(tmp_path, self._many())
        result = archive_journal(link)
        assert Path(result.archive_path).samefile(tmp_path / ".agents" / "JOURNAL_ARCHIVE.md")
        self._assert_archived_beside_real(tmp_path, link, real)

    def test_cli_archive_on_a_linked_journal(self, tmp_path):
        import subprocess
        import sys

        link, real = self._project(tmp_path, self._many())
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "stellars_claude_code_plugins.journal.journal_tools",
                "archive",
                ".claude/JOURNAL.md",
            ],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert r.returncode == 0, r.stderr
        assert ".agents/JOURNAL_ARCHIVE.md" in r.stdout
        self._assert_archived_beside_real(tmp_path, link, real)

    def test_sort_writes_through_the_link(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import main

        link, real = self._project(
            tmp_path,
            HEADER + _entry(1, marker="", words=60) + "\n" + _entry(3, marker="", words=60),
        )
        assert main(["sort", str(link)]) == 0
        self._assert_link_kept(link)
        assert [e.number for e in parse_journal(real.read_text())] == [1, 2]

    def test_standardize_apply_writes_through_the_link(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import main

        link, real = self._project(tmp_path, HEADER + _entry(1, marker="", words=200, title="X"))
        assert main(["standardize", str(link), "--apply", "1", "--decision", "extended"]) == 0
        self._assert_link_kept(link)
        assert "**Task [Extended] - X**" in real.read_text()

    def test_standardize_all_writes_through_the_link(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import main

        # a marker on a 100-word body drops without a subprocess, then the clean footer lands
        link, real = self._project(
            tmp_path, HEADER + _entry(1, marker="[Extended] ", words=100, title="X")
        )
        assert main(["standardize", str(link), "--all"]) == 0
        self._assert_link_kept(link)
        text = real.read_text()
        assert "[Extended]" not in text
        assert "<!-- standardize-clean:" in text


class TestJournalLayout:
    """The real journal is `<dir>/.agents/JOURNAL.md` and `<dir>/.claude/JOURNAL.md`
    is the relative link `../.agents/JOURNAL.md`; JOURNAL_ARCHIVE.md follows the same
    pattern. `journal-tools layout` makes that layout, and every command that writes
    the journal runs it first (ACC-JRNL-268..273). Unit tests call the module;
    functional tests run the CLI in a scratch project.
    """

    # a CRLF header, a non-ASCII byte and no final newline: a text round trip changes these bytes
    OLD = b"# Claude Code Journal\r\n\r\ncaf\xc3\xa9, no final newline"
    OLD_ARCHIVE = b"# Claude Code Journal Archive\n"

    @staticmethod
    def _cli(cwd, *args):
        import subprocess
        import sys

        cmd = [sys.executable, "-m", "stellars_claude_code_plugins.journal.journal_tools", *args]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    @staticmethod
    def _tree(root) -> dict:
        """Each file and link under root: its bytes, or its link target."""
        import os

        return {
            str(p.relative_to(root)): ("->", os.readlink(p)) if p.is_symlink() else p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_symlink() or p.is_file()
        }

    @staticmethod
    def _entries(*numbers) -> bytes:
        return (HEADER + "\n".join(_entry(n, marker="", words=60) for n in numbers)).encode()

    def _old(self, root, journal: bytes = OLD, archive: bytes = OLD_ARCHIVE):
        """The old layout, real files in root/.claude/; returns the journal path."""
        (root / ".claude").mkdir(parents=True)
        (root / ".claude" / "JOURNAL_ARCHIVE.md").write_bytes(archive)
        (root / ".claude" / "JOURNAL.md").write_bytes(journal)
        return root / ".claude" / "JOURNAL.md"

    @staticmethod
    def _assert_linked(root, name: str, data: bytes | None = None):
        """root/.claude/<name> is the link ../.agents/<name> to a real file, holding data when given."""
        import os

        real = root / ".agents" / name
        assert os.readlink(root / ".claude" / name) == f"../.agents/{name}"
        assert real.is_file() and not real.is_symlink()
        if data is not None:
            assert real.read_bytes() == data

    # LAYOUT-NEW

    def test_new_journal_is_created_in_agents(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import adopt_layout, main

        link = tmp_path / ".claude" / "JOURNAL.md"
        assert adopt_layout(link) == [f"linked {link} -> ../.agents/JOURNAL.md"]
        (tmp_path / ".agents" / "JOURNAL.md").write_text(HEADER)  # what /journal:create writes
        self._assert_linked(tmp_path, "JOURNAL.md", HEADER.encode())
        (tmp_path / ".agents" / "JOURNAL.md").write_bytes(self._entries(*range(1, 42)))
        assert main(["archive", str(link)]) == 0
        self._assert_linked(tmp_path, "JOURNAL_ARCHIVE.md")

    def test_cli_new_journal_and_its_archive(self, tmp_path):
        r = self._cli(tmp_path, "layout", ".claude/JOURNAL.md")
        assert r.returncode == 0, r.stderr
        (tmp_path / ".agents" / "JOURNAL.md").write_bytes(self._entries(*range(1, 42)))
        r = self._cli(tmp_path, "archive", ".claude/JOURNAL.md")
        assert r.returncode == 0, r.stderr
        assert "linked .claude/JOURNAL_ARCHIVE.md -> ../.agents/JOURNAL_ARCHIVE.md" in r.stdout
        self._assert_linked(tmp_path, "JOURNAL.md")
        self._assert_linked(tmp_path, "JOURNAL_ARCHIVE.md")

    # LAYOUT-MOVE

    def test_move_keeps_every_byte(self, tmp_path):
        import os

        from stellars_claude_code_plugins.journal.journal_tools import adopt_layout

        assert len(adopt_layout(self._old(tmp_path))) == 2
        self._assert_linked(tmp_path, "JOURNAL.md", self.OLD)
        self._assert_linked(tmp_path, "JOURNAL_ARCHIVE.md", self.OLD_ARCHIVE)
        assert sorted(os.listdir(tmp_path / ".agents")) == ["JOURNAL.md", "JOURNAL_ARCHIVE.md"]
        assert sorted(os.listdir(tmp_path / ".claude")) == ["JOURNAL.md", "JOURNAL_ARCHIVE.md"]

    def test_read_only_journal_moves(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import adopt_layout

        journal = self._old(tmp_path)
        journal.chmod(0o444)
        assert len(adopt_layout(journal)) == 2
        self._assert_linked(tmp_path, "JOURNAL.md", self.OLD)

    def test_failed_move_leaves_the_original(self, tmp_path, monkeypatch):
        import os

        from stellars_claude_code_plugins.journal import journal_tools

        journal = self._old(tmp_path)
        before = self._tree(tmp_path)
        replace = os.replace

        def fail_on_the_link(src, dst):
            if str(dst) == str(journal):
                raise OSError("simulated failure before the link replaces the journal")
            return replace(src, dst)

        monkeypatch.setattr(journal_tools.os, "replace", fail_on_the_link)
        with pytest.raises(OSError, match="simulated"):
            journal_tools.adopt_layout(journal)
        assert self._tree(tmp_path) == before
        monkeypatch.undo()
        journal_tools.adopt_layout(journal)  # nothing left behind blocks the rerun
        self._assert_linked(tmp_path, "JOURNAL.md", self.OLD)

    def test_cli_write_moves_first(self, tmp_path):
        self._old(tmp_path, journal=self._entries(1, 3))
        r = self._cli(tmp_path, "sort", ".claude/JOURNAL.md")
        assert r.returncode == 0, r.stderr
        assert r.stdout.startswith("moved .claude/JOURNAL.md to .agents/JOURNAL.md")
        self._assert_linked(tmp_path, "JOURNAL_ARCHIVE.md", self.OLD_ARCHIVE)
        self._assert_linked(tmp_path, "JOURNAL.md")
        text = (tmp_path / ".agents" / "JOURNAL.md").read_text()
        assert [e.number for e in parse_journal(text)] == [1, 2]

    # LAYOUT-CONFLICT

    CONFLICTS = ["both real", "archive both real", "link elsewhere"]

    @staticmethod
    def _conflict(root, case: str):
        """Write one conflicting layout; return the two paths the refusal must name."""
        claude, agents = root / ".claude", root / ".agents"
        claude.mkdir()
        agents.mkdir()
        if case == "link elsewhere":
            (root / "docs").mkdir()
            (root / "docs" / "JOURNAL.md").write_bytes(b"elsewhere\n")
            (claude / "JOURNAL.md").symlink_to("../docs/JOURNAL.md")
            return ".claude/JOURNAL.md", ".agents/JOURNAL.md"
        (claude / "JOURNAL.md").write_bytes(b"claude side\n")
        if case == "both real":
            (agents / "JOURNAL.md").write_bytes(b"agents side\n")
            return ".claude/JOURNAL.md", ".agents/JOURNAL.md"
        (claude / "JOURNAL_ARCHIVE.md").write_bytes(b"claude archive\n")
        (agents / "JOURNAL_ARCHIVE.md").write_bytes(b"agents archive\n")
        return ".claude/JOURNAL_ARCHIVE.md", ".agents/JOURNAL_ARCHIVE.md"

    @pytest.mark.parametrize("case", CONFLICTS)
    def test_conflict_changes_nothing(self, tmp_path, case):
        from stellars_claude_code_plugins.journal.journal_tools import LayoutConflict, adopt_layout

        first, second = self._conflict(tmp_path, case)
        before = self._tree(tmp_path)
        with pytest.raises(LayoutConflict) as exc:
            adopt_layout(tmp_path / ".claude" / "JOURNAL.md")
        assert first in str(exc.value) and second in str(exc.value)
        assert self._tree(tmp_path) == before

    @pytest.mark.parametrize("case", CONFLICTS)
    def test_cli_conflict_changes_nothing(self, tmp_path, case):
        first, second = self._conflict(tmp_path, case)
        before = self._tree(tmp_path)
        for command in ("layout", "sort"):
            r = self._cli(tmp_path, command, ".claude/JOURNAL.md")
            assert r.returncode == 1
            assert first in r.stderr and second in r.stderr
            assert self._tree(tmp_path) == before

    # LAYOUT-STEP

    WRITERS = [
        (["archive"], range(1, 42), "have been archived to"),
        (["sort"], (1, 3), "2. **Task"),
        (["standardize", "--apply", "1", "--decision", "extended"], (1,), "**Task [Extended] -"),
        (["standardize", "--all"], (1,), "<!-- standardize-clean:"),
    ]
    WRITER_IDS = ["archive", "sort", "standardize-apply", "standardize-all"]
    READERS = [
        ["check"],
        ["sort", "--dry-run"],
        ["standardize", "--list"],
        ["standardize", "--prompt", "1"],
    ]

    @pytest.mark.parametrize("argv, numbers, written", WRITERS, ids=WRITER_IDS)
    def test_every_writing_command_moves_first(self, tmp_path, capsys, argv, numbers, written):
        from stellars_claude_code_plugins.journal.journal_tools import main

        journal = self._old(tmp_path, journal=self._entries(*numbers))
        assert main([argv[0], str(journal), *argv[1:]]) == 0
        assert capsys.readouterr().out.startswith(f"moved {journal} to ")
        self._assert_linked(tmp_path, "JOURNAL.md")
        self._assert_linked(tmp_path, "JOURNAL_ARCHIVE.md")
        assert written in (tmp_path / ".agents" / "JOURNAL.md").read_text()

    @pytest.mark.parametrize("argv", READERS, ids=" ".join)
    def test_read_only_commands_move_nothing(self, tmp_path, argv):
        from stellars_claude_code_plugins.journal.journal_tools import adopt_layout, main

        journal = self._old(tmp_path, journal=self._entries(1))
        before = self._tree(tmp_path)
        assert main([argv[0], str(journal), *argv[1:]]) == 0
        assert self._tree(tmp_path) == before
        assert len(adopt_layout(journal)) == 2  # the same tree moves under the step

    @pytest.mark.parametrize("argv, numbers, written", WRITERS, ids=WRITER_IDS)
    def test_cli_every_writing_command_moves_first(self, tmp_path, argv, numbers, written):
        self._old(tmp_path, journal=self._entries(*numbers))
        r = self._cli(tmp_path, argv[0], ".claude/JOURNAL.md", *argv[1:])
        assert r.returncode == 0, r.stderr
        assert r.stdout.startswith("moved .claude/JOURNAL.md to .agents/JOURNAL.md")
        self._assert_linked(tmp_path, "JOURNAL.md")
        self._assert_linked(tmp_path, "JOURNAL_ARCHIVE.md")
        assert written in (tmp_path / ".agents" / "JOURNAL.md").read_text()

    @pytest.mark.parametrize("argv", READERS, ids=" ".join)
    def test_cli_read_only_commands_move_nothing(self, tmp_path, argv):
        self._old(tmp_path, journal=self._entries(1))
        before = self._tree(tmp_path)
        r = self._cli(tmp_path, argv[0], ".claude/JOURNAL.md", *argv[1:])
        assert r.returncode == 0, r.stderr
        assert self._tree(tmp_path) == before
        assert self._cli(tmp_path, "layout", ".claude/JOURNAL.md").returncode == 0
        self._assert_linked(tmp_path, "JOURNAL.md")  # the same tree moves under the step

    @pytest.mark.parametrize("argv, numbers, written", WRITERS, ids=WRITER_IDS)
    def test_cli_writing_command_links_an_agents_only_journal(
        self, tmp_path, argv, numbers, written
    ):
        # another agent created the shared journal: .agents/JOURNAL.md exists, .claude/ does not
        (tmp_path / ".agents").mkdir()
        (tmp_path / ".agents" / "JOURNAL.md").write_bytes(self._entries(*numbers))
        r = self._cli(tmp_path, argv[0], ".claude/JOURNAL.md", *argv[1:])
        assert r.returncode == 0, r.stderr
        assert r.stdout.startswith("linked .claude/JOURNAL.md -> ../.agents/JOURNAL.md")
        self._assert_linked(tmp_path, "JOURNAL.md")
        assert written in (tmp_path / ".agents" / "JOURNAL.md").read_text()

    @pytest.mark.parametrize("command", ["archive", "sort"])
    @pytest.mark.parametrize("claude_dir", [False, True], ids=["empty", "empty-claude"])
    def test_cli_writing_command_on_a_missing_journal_changes_nothing(
        self, tmp_path, command, claude_dir
    ):
        if claude_dir:
            (tmp_path / ".claude").mkdir()
        before = sorted(tmp_path.rglob("*"))
        r = self._cli(tmp_path, command, ".claude/JOURNAL.md")
        assert r.returncode == 1
        assert "not found" in r.stderr
        assert sorted(tmp_path.rglob("*")) == before  # no new directory, no link

    # LAYOUT-ANYDIR

    def test_any_claude_directory_moves_another_path_stays(self, tmp_path):
        import os

        from stellars_claude_code_plugins.journal.journal_tools import adopt_layout

        home, project = tmp_path / "home", tmp_path / "project"
        for root in (home, project):
            assert len(adopt_layout(self._old(root))) == 2
            self._assert_linked(root, "JOURNAL.md", self.OLD)
        other = project / "docs" / "JOURNAL.md"
        other.parent.mkdir()
        other.write_bytes(self.OLD)
        assert adopt_layout(other) == []
        assert os.listdir(other.parent) == ["JOURNAL.md"]
        assert not other.is_symlink() and other.read_bytes() == self.OLD

    def test_absolute_path_through_a_symlinked_ancestor_gets_a_relative_link(self, tmp_path):
        from stellars_claude_code_plugins.journal.journal_tools import adopt_layout

        real = tmp_path / "real" / "proj"
        self._old(real)
        (tmp_path / "alias").symlink_to(tmp_path / "real")
        assert len(adopt_layout(tmp_path / "alias" / "proj" / ".claude" / "JOURNAL.md")) == 2
        self._assert_linked(real, "JOURNAL.md", self.OLD)
        self._assert_linked(real, "JOURNAL_ARCHIVE.md", self.OLD_ARCHIVE)

    def test_cli_home_journal_moves_another_path_stays(self, tmp_path):
        import os
        import shlex
        import subprocess
        import sys

        home, project = tmp_path / "home", tmp_path / "project"
        self._old(home)
        self._old(project)
        other = project / "docs" / "JOURNAL.md"
        other.parent.mkdir()
        other.write_bytes(self.OLD)
        cli = (
            f"{shlex.quote(sys.executable)} -m stellars_claude_code_plugins.journal.journal_tools"
        )
        env = {**os.environ, "HOME": str(home)}
        # the shell expands ~ to HOME, as it does for ~/.claude/JOURNAL.md
        for path in ("~/.claude/JOURNAL.md", ".claude/JOURNAL.md", "docs/JOURNAL.md"):
            r = subprocess.run(
                f"{cli} layout {path}", shell=True, cwd=project, env=env, capture_output=True
            )
            assert r.returncode == 0, r.stderr
        for root in (home, project):
            self._assert_linked(root, "JOURNAL.md", self.OLD)
            self._assert_linked(root, "JOURNAL_ARCHIVE.md", self.OLD_ARCHIVE)
        assert os.listdir(other.parent) == ["JOURNAL.md"]
        assert not other.is_symlink() and other.read_bytes() == self.OLD

    def test_cli_malformed_path_fails_and_creates_nothing(self, tmp_path):
        import os

        # a quoted ~ is not expanded: the parent of .claude is the missing directory ./~
        r = self._cli(tmp_path, "layout", "~/.claude/JOURNAL.md")
        assert r.returncode != 0
        assert os.listdir(tmp_path) == []

    # LAYOUT-DOCS

    def test_docs_state_the_layout_once(self):
        from pathlib import Path
        import re

        root = Path(__file__).resolve().parents[1]
        plugin = root / "plugins" / "journal"
        stating = [
            str(p.relative_to(plugin))
            for p in sorted(plugin.rglob("*.md"))
            if "../.agents/JOURNAL.md" in p.read_text(encoding="utf-8")
        ]
        assert stating == ["skills/journal/SKILL.md"]
        for skill in ("create", "update"):
            text = (plugin / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            assert text.index("journal-tools layout .claude/JOURNAL.md") < text.index(
                "into `.agents/JOURNAL.md`"
            ), skill
            assert re.search(r"journal-tools layout [^\n]*refus[^\n]*ask the user", text), skill
        changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        unreleased = changelog.split("## [Unreleased]")[1].split("\n## [")[0]
        assert "journal-tools layout" in unreleased

    def test_documented_layout_command_runs(self, tmp_path):
        import os
        from pathlib import Path
        import re

        plugin = Path(__file__).resolve().parents[1] / "plugins" / "journal"
        for skill in ("create", "update"):
            text = (plugin / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            args = re.search(r"`journal-tools (layout [^`]+)`", text).group(1).split()
            project = tmp_path / skill
            project.mkdir()
            if skill == "update":
                self._old(project)
            r = self._cli(project, *args)
            assert r.returncode == 0, r.stderr
            assert os.readlink(project / ".claude" / "JOURNAL.md") == "../.agents/JOURNAL.md"
        self._assert_linked(tmp_path / "update", "JOURNAL.md", self.OLD)
