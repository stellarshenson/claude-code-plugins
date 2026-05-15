"""Shared test fixtures for the orchestration engine."""

from pathlib import Path

import pytest

from _claude_cassette import ClaudePCassette


def pytest_addoption(parser):
    """Register the cassette-record CLI flag.

    Cassettes for `claude -p` subprocess calls live in
    `tests/cassettes/claude_p/<hash>.json`. Default behaviour is REPLAY:
    missing cassettes raise, tests fail loudly. `--record-cassettes`
    flips into RECORD mode: missing cassettes are populated by actually
    running the `claude` binary (requires it on PATH). Maintainers run
    this once, commit the JSON files, and CI replays them.
    """
    parser.addoption(
        "--record-cassettes",
        action="store_true",
        default=False,
        help=(
            "Record claude -p cassettes by shelling out to the real "
            "binary when a cassette is missing. Without this flag, "
            "missing cassettes fail the test."
        ),
    )


@pytest.fixture
def claude_p_cassette(request):
    """Yield a `ClaudePCassette` callable suitable for monkeypatching
    `subprocess.run` in tests that exercise a `claude -p` spawn site.

    Usage::

        def test_extended_decision(claude_p_cassette, monkeypatch):
            from stellars_claude_code_plugins.journal import journal_tools

            monkeypatch.setattr(
                journal_tools.subprocess, "run", claude_p_cassette
            )
            out = journal_tools._spawn_standardize_subprocess("...")
            assert "EXTENDED" in out

    On `pytest --record-cassettes`, the first run of a new test will
    call the real `claude` binary and persist its response.
    """
    record = request.config.getoption("--record-cassettes")
    return ClaudePCassette(record=record)


@pytest.fixture
def autobuild_resources():
    """Path to bundled YAML resource files in the autobuild module."""
    return (
        Path(__file__).resolve().parent.parent
        / "src"
        / "stellars_claude_code_plugins"
        / "autobuild"
        / "resources"
    )


@pytest.fixture
def minimal_resources(tmp_path):
    """Create minimal YAML resource files for testing.

    Uses FQN workflow names (WORKFLOW::TEST_WORKFLOW) and merged
    phases format (agents/gates inline in phases.yaml, no agents.yaml).
    Uses the start/execution/end lifecycle structure.
    """
    resources = tmp_path / "resources"
    resources.mkdir()

    (resources / "workflow.yaml").write_text("""
WORKFLOW::TEST_WORKFLOW:
  cli_name: test_workflow
  description: "A test workflow"
  phases:
    - name: ALPHA
      skippable: false
    - name: BETA
      skippable: true
    - name: GAMMA
      skippable: false
""")

    (resources / "phases.yaml").write_text("""
actions:
  ACTION::TEST_ACTION:
    cli_name: test_action
    type: programmatic
    description: "A test action"

shared_gates:
  skip:
    gatekeeper_skip:
      mode: standalone_session
      description: "Skip gatekeeper"
      prompt: "Evaluate skip for {phase} in iteration {iteration} type {itype} objective {objective}: {reason}"
    gatekeeper_force_skip:
      mode: standalone_session
      description: "Force-skip gatekeeper"
      prompt: "Evaluate force-skip for {phase} in iteration {iteration}: {reason}"

ALPHA:
  auto_actions:
    on_complete: []
  start:
    template: "Start alpha phase. Objective: {objective}"
    agents:
      - name: readback
        mode: standalone_session
        description: "Validate understanding"
        prompt: "Phase {phase}: does '{understanding}' capture the requirements?"
  execution:
    agents:
      - name: researcher
        display_name: Researcher
        prompt: "Research the topic"
  end:
    template: "End alpha phase. Evidence: {evidence}"
    agents:
      - name: gatekeeper
        mode: standalone_session
        description: "Validate completion"
        prompt: "Phase {phase}: {evidence}"

BETA:
  auto_actions:
    on_complete: []
  start:
    template: "Start beta phase."
    agents:
      - name: readback
        mode: standalone_session
        description: "Validate understanding"
        prompt: "Phase {phase}: does '{understanding}' capture the requirements?"
  execution:
    agents:
      - name: planner
        display_name: Planner
        prompt: "Plan the work"
  end:
    template: "End beta phase."
    agents:
      - name: gatekeeper
        mode: standalone_session
        description: "Validate completion"
        prompt: "Phase {phase}: {evidence}"

GAMMA:
  auto_actions:
    on_complete: []
  start:
    template: "Start gamma phase."
    agents:
      - name: readback
        mode: standalone_session
        description: "Validate understanding"
        prompt: "Phase {phase}: does '{understanding}' capture the requirements?"
  execution:
    agents:
      - name: executor
        display_name: Executor
        prompt: "Execute the work"
  end:
    template: "End gamma phase."
    agents:
      - name: gatekeeper
        mode: standalone_session
        description: "Validate completion"
        prompt: "Phase {phase}: {evidence}"
""")

    (resources / "app.yaml").write_text("""
app:
  name: test-plugin
  description: "Test orchestration plugin"
  cmd: "python orchestrate.py"
  artifacts_dir: ".test-plugin"

display:
  separator: "-"
  separator_width: 40
  header_char: "="
  header_width: 40

banner:
  header: "{header_line}\\nIteration {iter_label} ({itype}) - {action} {phase} [{phase_idx}/{total}]{reject_info}\\nObjective: {objective}\\n{progress}\\n{header_line}\\n"
  progress_current: "**{p}**"
  progress_done: "~~{p}~~"

footer:
  start: "\\n{separator_line}\\nPhase started. Run: {cmd} end --evidence \\"...\\"\\n"
  end: "\\n{separator_line}\\nPhase complete. Next: {cmd} start --understanding \\"...\\"\\n"
  final: "\\n{separator_line}\\nIteration complete.\\n"

messages:
  no_active: "No active iteration."
  validate_success: "Model validation: OK"
  validate_issues: "{count} issue(s) found:"
  validate_item: "  {num}. {issue}"
  benchmark_driven_label: "benchmark-driven {iteration}"
  benchmark_complete: "Benchmark conditions met - all iterations complete."
  benchmark_safety_cap: "WARNING: {count} iterations without benchmark completion. Pausing."

cli:
  description: "Test orchestration CLI"
  epilog: "Usage: {cmd} <command>"
  commands:
    new: "Start new iteration"
    start: "Begin phase"
    end: "Complete phase"
    status: "Show status"
  args:
    objective: "Iteration objective"
    iterations: "Number of iterations"
""")

    return resources
