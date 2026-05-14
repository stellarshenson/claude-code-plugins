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
    return (
        f"{num}. **Task - Demo** (v0.1.0): one-line summary<br>\n"
        f"    **Result**: {body}\n"
    )


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
        assert any(
            s == "warning" and "body is empty" in m for s, m in msgs
        ), f"expected empty-body warning; got: {msgs}"

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
        msgs = [
            v.message
            for v in violations
            if v.entry_number == 1 and v.severity == "error"
        ]
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
            _load_standardize_prompt,
        )

        data = _load_standardize_prompt()
        assert data["version"] == 1
        assert "system" in data and "user_template" in data
        assert {"standard_target", "extended_min", "extended_max"} <= data["limits"].keys()

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

    def test_cli_apply_extended_via_subprocess(self, tmp_path):
        import json
        import subprocess
        import sys

        journal = tmp_path / "J.md"
        journal.write_text(self._journal(_entry(1, marker="", words=200, title="X")))

        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.journal.journal_tools",
             "standardize", str(journal), "--list"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        candidates = json.loads(r.stdout)
        assert candidates[0]["number"] == 1
        assert candidates[0]["action_needed"] == "decide"

        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.journal.journal_tools",
             "standardize", str(journal), "--apply", "1", "--decision", "extended"],
            capture_output=True, text=True,
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
            [sys.executable, "-m", "stellars_claude_code_plugins.journal.journal_tools",
             "standardize", str(journal), "--apply", "1",
             "--decision", "condense", "--body-file", str(body)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        text = journal.read_text()
        assert "[Extended]" not in text
        assert "now Standard" in r.stdout
