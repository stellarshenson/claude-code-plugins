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


def agent(name: str) -> str:
    """ACC-REVIEW-62: the review method lives in the agent files; the script's
    prompts carry data only. Method guardrails assert against the agent file."""
    return (SCRIPT.parents[3] / "agents" / f"{name}.md").read_text(encoding="utf-8")


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
    assert "caps material=false" in t  # the reviewer prompt names the script's cap
    adj = agent("adjudicator")
    assert "Materiality triage" in adj and "refute it as immaterial" in adj
    assert "Technical truth is not materiality" in adj or "technically true defect" in adj
    rev = agent("adversarial-reviewer")
    assert "Materiality before severity" in rev and "technically true defect" in rev
    assert "EDIT" in rev and "DEFER" in rev and "NEW MECHANISM" in rev


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
    assert "'reverts'" in t and "REVERT BEFORE REFINE" in t
    adj = agent("adjudicator")
    assert "Revert before refine" in adj and "REVERT CANDIDATE" in adj
    assert "contested semantics" in adj and "`reverted:`" in adj
    assert "above 0.5 with no revert must be justified" in adj
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
    assert "never a gate" in t
    assert "An empty change plan rules the round clean" in agent("adjudicator")
    assert "who alone decides what blocks" in agent("adversarial-reviewer")
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
    assert (
        "never modify any file" in t
    )  # reviewers in the script prompt; the adjudicator in its agent file
    assert "Never modify a file in the repo under review" in agent("adjudicator")


def test_instrument_threaded_as_data_never_prescribed():
    """ACC-REVIEW-72. An instrument reaches the agents as data - what exists,
    where, what it answers - and the agent decides whether and how to use it,
    reading the tool's own help for its current surface. A command spelled out
    here pins an API that moves, and a hardcoded approach overfits to the
    problems it was written for and misclassifies the rest. So the pins are the
    threading and the outcome, never a vendor command string."""
    t = text()
    assert "args.graph" in t and "graphBlock" in t
    assert "${GRAPH}" in t  # the caller's own path reaches the prompt
    assert "INSTRUMENT AVAILABLE" in t and "as your method sees fit" in t
    assert t.count(".filter(Boolean)") >= 2  # optional block dropped cleanly from both prompts
    assert "blast radius" in agent("adversarial-reviewer")
    for name in ("adversarial-reviewer", "adjudicator"):
        body = agent(name)
        assert "whatever instrument answers fastest" in body
        assert "tmp/graphify-out/graph.json" not in body  # no hardcoded path
        assert "graphify " not in body  # no pinned command surface


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


ROUTING = (
    "construct the workflow from the spec and pass it inline; "
    "without it, run the shipped `adversarial-loop.js` as the supplied protocol"
)


def test_routing_dynamic_constructs_from_spec_shipped_script_is_fallback():
    """ACC-REVIEW-61: one routing sentence on every surface read on its own
    (skill, command, README) plus a pointer to the spec; the spec alone carries
    the full contract and the incident record, so the `<select>` anecdote
    appears in no other plugin file."""
    skill = (PLUGIN / "skills/adversarial-review/SKILL.md").read_text(encoding="utf-8")
    command = (PLUGIN / "commands/adversarial-review.md").read_text(encoding="utf-8")
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    spec = SPEC.read_text(encoding="utf-8")
    for surface in (skill, command, readme):
        assert ROUTING in surface
        assert "references/loop-spec.md" in surface
    assert "**Dynamic (default)**" in spec
    assert "**Supplied (no dynamic capability - different harness)**" in spec
    # the worked example's meta names are its own - a constructed loop names
    # itself for its target - so pin the harness convention, not the string
    meta = text()[: text().index("\n}") + 2]
    name = re.search(r"name: '([^']+)'", meta).group(1)
    desc = re.search(r"description: '([^']+)'", meta).group(1)
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name), name  # kebab-case, lowercase
    assert desc[0].islower(), desc[:40]  # no sentence case in a meta description
    offenders = [
        str(p.relative_to(PLUGIN))
        for p in PLUGIN.rglob("*")
        if p.is_file() and p != SPEC and "<select>" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, offenders
