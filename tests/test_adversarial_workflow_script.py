"""Guardrails for the canonical adversarial-review workflow script.

The script IS the loop protocol - plugins/devils-advocate ships it so the
control flow (forced adjudication, computed verdict, pinned confirms, fanout
and round caps) is versioned code instead of orchestrator context. These tests
pin the gates so an edit cannot silently drop one.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

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


def test_bar_must_name_purpose_inputs_and_primary_path():
    """DEF-ADVR-40: an output-only bar promotes every input in the world into
    scope. The script refuses a bar without purpose, inputs and primaryPath."""
    t = text()
    assert re.search(r"args\.bar\.purpose.*args\.bar\.inputs.*args\.bar\.primaryPath", t)
    assert "PURPOSE" in t and "INPUT UNIVERSE" in t and "PRIMARY PATH" in t


def test_materiality_before_severity():
    """DEF-ADVR-40: every finding answers who is harmed on the primary path;
    material=false is capped by the script at MINOR/outOfBar - scope, not
    blocking - and the adjudicator triages materiality before verifying."""
    t = text()
    assert "'material'" in t and "'materiality'" in t
    assert "material === false" in t and "capImmaterial" in t
    assert (
        "return capImmaterial(rows)" in t
    )  # the cap is wired into mergeFindings, not just defined
    assert "severity: 'MINOR', outOfBar: true" in t
    assert "MATERIALITY TRIAGE" in t and "refute it as immaterial" in t
    assert "Technical truth is not materiality" in t or "technically true defect" in t


def test_new_mechanism_flag_and_change_budget():
    """DEF-ADVR-41: every planned change says whether it adds review surface;
    the plan is budgeted and mechanisms are surfaced in the PLAN payload."""
    t = text()
    assert "'newMechanism'" in t and "newMechanism: { type: 'boolean'" in t
    assert "MAX_CHANGES" in t and "CHANGE BUDGET" in t
    assert "mechanisms," in t and "NEW MECHANISM" in t


def test_revert_before_refine():
    """DEF-ADVR-42: loop-introduced machinery is removed, not polished - the
    adjudication carries reverts, and PLAN / STOP / FANOUT_STOP hand them to
    the main session (every applied change when the adjudicator ruled none)."""
    t = text()
    assert "'reverts'" in t and "REVERT BEFORE REFINE" in t and "REVERT CANDIDATE" in t
    assert "contested semantics" in t
    assert t.count("reverts: reverts.length ? reverts : closures") == 2  # STOP and FANOUT_STOP
    assert "status: 'PLAN',\n        reverts," in t
    assert "NO revert ruled" in t  # fanout above 0.5 without a revert is called out


def test_confirm_round_filter_is_script_enforced():
    """DEF-ADVR-43: pinning was prompt-only on record and reviewers swept
    anyway; a confirming finding survives only if it names a failing closure
    or sits in the applied delta, and is not taste - dropped ones are logged."""
    t = text()
    assert "pinFilter" in t and t.count("pinFilter(mergeFindings(") == 2  # both confirm panels
    assert "f.closure" in t and "inDelta(f)" in t and "!f.taste" in t
    assert "confirm filter:" in t and "confirm-filter" in t  # logged and in history
    assert "TURN BUDGET" in t and "DISCARDS" in t


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
    assert (
        "fanout > 0.5 && refining" in t
    )  # DEF-ADVR-46: an adjudicated-clean round never trips the fanout gate
    assert (
        "const refining = adj.changes.length > 0 || reverts.length > 0" in t
    )  # the definition, not just its use
    assert "highFanoutStreak = 0" in t  # the no-findings clean branch resets the streak too
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
        "Materiality before severity",
        "Revert before refine",
        "`reverts`",
        "newMechanism",
        "discarded before adjudication",
    ):
        assert marker in t, marker
    assert "docs/spec-adversarial-loop-execution" not in t  # old repo-only home is gone


PLUGIN = Path(__file__).parent.parent / "plugins/devils-advocate"


def test_routing_dynamic_constructs_from_spec_shipped_script_is_fallback():
    """The directive: a harness WITH the dynamic Workflow capability constructs
    the workflow from the spec (guidelines only); a harness WITHOUT it runs the
    shipped pre-built script. Every routing surface must say exactly that, and
    the shipped script must be named as the fallback, never the default."""
    skill = (PLUGIN / "skills/adversarial-review/SKILL.md").read_text(encoding="utf-8")
    command = (PLUGIN / "commands/adversarial-review.md").read_text(encoding="utf-8")
    spec = SPEC.read_text(encoding="utf-8")
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    # dynamic path: construct from the spec
    assert "Construct the workflow for the task from the spec" in skill
    assert "construct the workflow from the spec" in command
    assert "**Dynamic (default)**" in spec and "constructs the workflow from this spec" in spec
    assert "authors the workflow from the execution spec" in readme
    # fallback path: the shipped script, only without the capability
    assert "No dynamic Workflow capability (different harness)" in skill
    assert (
        "the supplied workflow is the protocol: execute `workflows/adversarial-loop.js`" in skill
    )
    assert "**Supplied (no dynamic capability - different harness)**" in spec
    assert "supplied fallback for harnesses without the dynamic Workflow capability" in command
    assert "fallback protocol for harnesses without the dynamic capability" in readme
    # the shipped script never presents itself as the default path
    assert "worked example" in spec.lower() and "Worked example" in skill
    assert "Managed adversarial review" in text()
