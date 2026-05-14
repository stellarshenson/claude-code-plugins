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
            STANDARDIZE_YAML_VERSION,
            _load_standardize_prompt,
        )

        data = _load_standardize_prompt()
        assert data["version"] == STANDARDIZE_YAML_VERSION
        assert "system" in data and "user_template" in data
        assert {"standard_target", "extended_min", "extended_max"} <= data["limits"].keys()

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

        text = (
            HEADER
            + _entry(1, marker="[Extended] ", words=250, title="Real depth")
        )
        entries = parse_journal(text)
        rendered = HEADER + render_entries(sort_entries(entries)) + "\n"
        reparsed = parse_journal(rendered)
        assert reparsed[0].is_extended is True
        # No word-count warning because marker preserved
        violations = check_journal(reparsed)
        assert not any("over Standard target" in v.message for v in violations)


class TestStandardFloorWarning:
    """`STANDARD_MIN = 70` floor warning (WI 4).

    Forensics on the kolomolo journal exposed several sub-50-word entries
    that carry no WHY — six months out they read as bare bullet points
    with no rationale. The validator now warns when an unmarked body sits
    in (0, 70). Empty bodies stay an error (existing behaviour); marker
    + body < EXTENDED_MIN stays its own warning (existing behaviour).
    """

    def _journal(self, *raws: str) -> str:
        return HEADER + "".join(raws)

    def test_sub_70_unmarked_warns(self):
        text = self._journal(_entry(1, marker="", words=50, title="Terse"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations]
        assert any("under Standard min 70" in m for m in msgs)

    def test_70_words_exactly_no_warning(self):
        text = self._journal(_entry(1, marker="", words=70, title="Threshold"))
        violations = check_journal(parse_journal(text))
        assert not any("under Standard min" in v.message for v in violations)

    def test_extended_marker_under_70_uses_extended_min_path(self):
        """Marker + 50-word body should fire the existing extended-min warning,
        not the new STANDARD_MIN warning (they would overlap otherwise)."""
        text = self._journal(_entry(1, marker="[Extended] ", words=50, title="Marked"))
        violations = check_journal(parse_journal(text))
        msgs = [v.message for v in violations]
        assert any("marked [Extended]" in m for m in msgs)
        assert not any("under Standard min" in m for m in msgs)


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
        journal.write_text(
            self._journal(_entry(1, marker="[Extended] ", words=30, title="Thin"))
        )
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
        # First call: no --model. Second call: includes --model claude-sonnet-4-20250514
        assert "--model" not in calls[0]
        assert "--model" in calls[1]
        assert "claude-sonnet-4-20250514" in calls[1]

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
