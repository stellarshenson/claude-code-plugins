"""Guardrails for the canonical adversarial-review workflow script.

The script IS the loop protocol - plugins/devils-advocate ships it so the
control flow (forced adjudication, computed verdict, pinned confirms, fanout
and round caps) is versioned code instead of orchestrator context. These tests
pin the gates so an edit cannot silently drop one.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parent.parent
    / "plugins/devils-advocate/skills/adversarial-review/workflows/adversarial-loop.js"
)


def text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_script_exists_with_pure_literal_meta():
    t = text()
    assert t.startswith("export const meta = {")
    meta = t[: t.index("\n}") + 2]
    for banned in ("${", "Date.", "Math.random", "...'"):
        assert banned not in meta


def test_no_runtime_banned_calls():
    t = text()
    assert "Date.now(" not in t and "Math.random(" not in t and "new Date(" not in t
    assert not re.search(r":\s*string\b|:\s*number\b|interface ", t)  # plain JS, not TS


def test_mandatory_args_throw():
    assert re.search(r"args\.target.*args\.bar.*args\.lenses.*mandatory", text(), re.S)


def test_adjudicator_decides_blocking_not_a_severity_gate():
    t = text()
    assert "REPORTING ONLY" in t and "severityTally" in t  # severities never gate
    assert "blockingOf" not in t  # the old deterministic gate is gone
    assert "YOU decide what blocks" in t and "not a gate" in t
    assert "adj.changes.length" in t  # empty plan rules the round clean
    assert "adjudicated clean" in t
    assert "prose verdict" in t.lower()  # reviewer verdicts never consumed


def test_adjudicator_continuity_threaded():
    """The adjudicator starts fresh every round - the script must thread its
    own prior record (rulings, refuted, deferred) into each prompt."""
    t = text()
    assert "priorRecord" in t and "PRIOR ADJUDICATIONS" in t
    assert "do not re-litigate" in t
    assert "rulings.push" in t


def test_gates_present():
    t = text()
    assert "'STOP'" in t and "FANOUT_STOP" in t and "ROUND_CAP" in t and "'PLAN'" in t
    assert "highFanoutStreak >= 2" in t and "> 0.5" in t  # two consecutive rounds over half
    assert "cleanStreak >= CLEAN_REQUIRED" in t
    assert "devils-advocate:adjudicator" in t and "devils-advocate:adversarial-reviewer" in t


def test_workflow_never_edits_the_tree():
    """The workflow reviews and adjudicates only: a non-empty plan EXITS with
    status PLAN for the main session to apply; the pinned confirm on the next
    invocation attacks exactly the applied delta - that is the regression
    protection, with no agent writing to the tree from inside the workflow."""
    t = text()
    assert "NEVER EDITS THE TREE" in t
    assert "FIX_SCHEMA" not in t and "'Fix'" not in t  # no fixer stage at all
    assert "Apply ONLY this plan in the main session" in t
    assert "args.state" in t and "appliedFixes" in t and "stateOut" in t  # cross-invocation state
    assert "never modify any file" in t  # reviewers and adjudicator both


def test_graph_threaded_when_present():
    t = text()
    assert "args.graph" in t and "graphBlock" in t
    assert "graphify affected" in t
    assert t.count(".filter(Boolean)") >= 2  # optional block dropped cleanly from both prompts


def test_confirm_round_is_pinned():
    t = text()
    assert "CONFIRMING round, pinned" in t and "CLOSURES (all applied so far):" in t
    assert "NEWEST DELTA" in t
    assert "do not review code the changes did not touch" in t


def test_phase_labels_match_meta():
    t = text()
    titles = re.findall(r"title: '([^']+)'", t[: t.index("\n}") + 2])
    assert titles == ["Discover", "Adjudicate", "Confirm"]
    for title in titles:
        assert f"'{title}'" in t[t.index("\n}") + 2 :]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_script_parses_as_workflow_body():
    """The runtime runs the body inside an async function (top-level return and
    await are legal); AsyncFunction reproduces that parse exactly."""
    body = text().replace("export const meta", "const meta", 1)
    check = (
        "const fs = require('fs');"
        "const body = fs.readFileSync(0, 'utf8');"
        "const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;"
        "new AsyncFunction('args','budget','agent','parallel','pipeline','phase','log','workflow', body);"
        "console.log('PARSE-OK');"
    )
    r = subprocess.run(
        ["node", "-e", check], input=body, capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0 and "PARSE-OK" in r.stdout, r.stderr


SPEC = (
    Path(__file__).parent.parent
    / "plugins/devils-advocate/skills/adversarial-review/references/loop-spec.md"
)


def test_spec_ships_in_the_plugin_with_the_full_contract():
    """The plugin owns the spec and ships it - constructing a workflow from it
    IS the dynamic execution path, so it must carry the whole contract."""
    t = SPEC.read_text(encoding="utf-8")
    assert "## Invariants" in t and "## Execution paths" in t
    for marker in (
        "No run without a bar",
        "adjudicator rules what blocks",
        "never edits the tree",
        "pinned",
        "`PLAN`",
        "FANOUT_STOP",
        "ROUND_CAP",
        "prior record",
    ):
        assert marker in t, marker
    assert "docs/spec-adversarial-loop-execution" not in t  # old repo-only home is gone
