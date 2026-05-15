"""Realism tests that exercise real recorded `claude -p` responses.

The synthetic-mock tests in `test_journal_tools.py::TestSpawnSubprocessSoftLanding`
and `test_orchestrator.py::TestClaudeEvaluateNoSessionPersistence` verify the
structural contract (flag presence, retry logic, parse paths). These tests
verify the same code paths against REAL claude output - format drift in the
binary's response (stderr leaks, JSON envelope changes, model-swap retry text)
would silently break the synthetic-mock tests because the mocks are
hand-crafted. Cassettes recorded once via `tests/record_claude_cassettes.py`
catch that drift.

Cassettes live in `tests/cassettes/claude_p/<hash>.json` and are content-
addressed by SHA-256(prompt). Tests render the same prompt the production
code would, install the cassette layer over `subprocess.run`, and assert the
parsed result.

To re-record (requires the `claude` binary):

    uv run python tests/record_claude_cassettes.py
"""

from __future__ import annotations

import pytest

from _cassette_prompts import (
    build_pass_evaluation_prompt,
    build_standardize_padded_prompt,
    build_standardize_rationale_rich_prompt,
)
from stellars_claude_code_plugins.journal import journal_tools
from stellars_claude_code_plugins.journal.journal_tools import (
    parse_standardize_decision,
)


class TestStandardizeSubprocessRealism:
    """Real recorded claude responses for `_spawn_standardize_subprocess`."""

    def test_rationale_rich_body_parses_cleanly(self, claude_p_cassette, monkeypatch):
        """Real claude response for a 200-word rationale-rich entry parses
        via the YAML grammar into one of the three legal decisions.

        Sonnet 4 typically returns CONDENSE here (the rubric is strict
        about what counts as "load-bearing rationale segments"). What
        matters for this test is that the response shape parses - not
        which specific decision was made.
        """
        monkeypatch.setattr(journal_tools.subprocess, "run", claude_p_cassette)
        prompt = build_standardize_rationale_rich_prompt()
        response = journal_tools._spawn_standardize_subprocess(prompt)
        assert response is not None, "cassette replay returned None"

        parsed = parse_standardize_decision(response)
        assert parsed is not None, (
            f"parser could not match recorded response shape: {response[:200]!r}"
        )
        decision, body = parsed
        assert decision in {"extended", "condense", "drop_marker"}
        if decision == "condense":
            assert body is not None and len(body.split()) > 0

    def test_padded_body_returns_condense_with_body(self, claude_p_cassette, monkeypatch):
        """500-word boilerplate body -> CONDENSE decision with a rewritten body.
        Recorded cassette confirms claude follows the rubric's Format B layout
        (`DECISION: CONDENSE\\nBODY:\\n<rewritten>`)."""
        monkeypatch.setattr(journal_tools.subprocess, "run", claude_p_cassette)
        prompt = build_standardize_padded_prompt()
        response = journal_tools._spawn_standardize_subprocess(prompt)
        parsed = parse_standardize_decision(response)
        assert parsed is not None
        decision, rewritten = parsed
        assert decision == "condense"
        assert rewritten is not None
        # Rewritten body sits within the Extended tier (or condensed below).
        assert 1 <= len(rewritten.split()) <= 400


class TestOrchestratorClaudeEvaluateRealism:
    """Real recorded claude response for `_claude_evaluate` PASS verdict."""

    def test_simple_pass_evaluation(self, claude_p_cassette, monkeypatch, tmp_path):
        """Recorded PASS/FAIL prompt -> real claude returns 'PASS: ...' on first
        line. `_claude_evaluate` parses the first line to decide passed/failed.

        This is the canonical happy path the autobuild readback/gatekeeper
        gates hit dozens of times per iteration.
        """
        from stellars_claude_code_plugins.autobuild import orchestrator

        monkeypatch.setattr(orchestrator.subprocess, "run", claude_p_cassette)
        monkeypatch.setattr(orchestrator, "DEFAULT_ARTIFACTS_DIR", tmp_path)

        prompt = build_pass_evaluation_prompt()
        passed, output = orchestrator._claude_evaluate(prompt)
        assert passed is True
        assert output.strip().upper().startswith("PASS")


class TestCassetteMissingFailsLoudly:
    """A test using a prompt with no recorded cassette must raise, not
    silently fall back. Prevents accidentally adding tests that drift away
    from the recorded responses without anyone noticing."""

    def test_unknown_prompt_raises(self, claude_p_cassette, monkeypatch):
        monkeypatch.setattr(journal_tools.subprocess, "run", claude_p_cassette)
        # An obviously-unrecorded prompt
        novel_prompt = "this-prompt-has-no-cassette-recorded-anywhere"
        with pytest.raises(RuntimeError, match="cassette missing"):
            journal_tools._spawn_standardize_subprocess(novel_prompt)
