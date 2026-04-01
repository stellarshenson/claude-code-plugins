"""Shared test fixtures for the orchestration engine."""

from pathlib import Path

import pytest


@pytest.fixture
def auto_build_claw_resources():
    """Path to auto-build-claw's YAML resource files (real plugin data)."""
    return Path(__file__).resolve().parent.parent / "auto-build-claw" / "skills" / "auto-build-claw" / "resources"


@pytest.fixture
def minimal_resources(tmp_path):
    """Create minimal YAML resource files for testing."""
    resources = tmp_path / "resources"
    resources.mkdir()

    (resources / "workflow.yaml").write_text("""
test_workflow:
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
ALPHA:
  start: "Start alpha phase. Objective: {objective}"
  end: "End alpha phase. Evidence: {evidence}"

BETA:
  start: "Start beta phase."
  end: "End beta phase."

GAMMA:
  start: "Start gamma phase."
  end: "End gamma phase."
""")

    (resources / "agents.yaml").write_text("""
shared_gates:
  on_skip:
    gatekeeper_skip:
      mode: standalone_session
      description: "Skip gatekeeper"
      prompt: "Evaluate skip for {phase} in iteration {iteration} type {itype} objective {objective}: {reason}"
    gatekeeper_force_skip:
      mode: standalone_session
      description: "Force-skip gatekeeper"
      prompt: "Evaluate force-skip for {phase} in iteration {iteration}: {reason}"

ALPHA:
  gates:
    on_start:
      readback:
        mode: standalone_session
        description: "Validate understanding"
        prompt: "Phase {phase}: does '{understanding}' capture the requirements?"
    on_end:
      agents:
        - name: researcher
          display_name: Researcher
          prompt: "Research the topic"
      gatekeeper:
        mode: standalone_session
        description: "Validate completion"
        prompt: "Phase {phase}: {evidence}"

BETA:
  gates:
    on_start:
      readback:
        mode: standalone_session
        description: "Validate understanding"
        prompt: "Phase {phase}: does '{understanding}' capture the requirements?"
    on_end:
      agents:
        - name: planner
          display_name: Planner
          prompt: "Plan the work"
      gatekeeper:
        mode: standalone_session
        description: "Validate completion"
        prompt: "Phase {phase}: {evidence}"

GAMMA:
  gates:
    on_start:
      readback:
        mode: standalone_session
        description: "Validate understanding"
        prompt: "Phase {phase}: does '{understanding}' capture the requirements?"
    on_end:
      agents:
        - name: executor
          display_name: Executor
          prompt: "Execute the work"
      gatekeeper:
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
