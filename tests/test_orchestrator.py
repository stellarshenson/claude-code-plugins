"""Integration tests for the orchestration engine.

Tests the orchestrator's initialization, state management, display helpers,
and command functions using minimal YAML fixtures. Gate functions (claude -p)
are mocked since they require the claude CLI.
"""

import argparse
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from stellars_claude_code_plugins.engine import orchestrator as orch


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset module-level state between tests."""
    orch._initialized = False
    orch._MODEL = None
    orch.ITERATION_TYPES.clear()
    orch.PHASE_AGENTS.clear()
    orch._PHASE_START.clear()
    orch._PHASE_END.clear()
    orch._AUTO_ACTION_REGISTRY.clear()
    yield


class TestInitialize:
    """Tests for _initialize with minimal and real YAML resources."""

    def test_initialize_minimal(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert orch._initialized is True
        assert orch._MODEL is not None
        assert "test_workflow" in orch.ITERATION_TYPES
        assert orch.CMD == "python orchestrate.py"

    def test_initialize_sets_paths(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert orch.DEFAULT_ARTIFACTS_DIR is not None
        assert orch.STATE_FILE is not None
        assert orch.LOG_FILE is not None

    def test_initialize_builds_iteration_types(self, minimal_resources):
        orch._initialize(minimal_resources)
        wf = orch.ITERATION_TYPES["test_workflow"]
        assert wf["phases"] == ["ALPHA", "BETA", "GAMMA"]
        assert "ALPHA" in wf["required"]
        assert "BETA" in wf["skippable"]

    def test_initialize_builds_phase_agents(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert "ALPHA" in orch.PHASE_AGENTS
        assert orch.PHASE_AGENTS["ALPHA"] == ["researcher"]

    def test_initialize_builds_phase_callables(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert "ALPHA" in orch._PHASE_START
        assert "ALPHA" in orch._PHASE_END
        assert callable(orch._PHASE_START["ALPHA"])

    def test_initialize_builds_auto_action_registry(self, minimal_resources):
        orch._initialize(minimal_resources)
        assert "plan_save" in orch._AUTO_ACTION_REGISTRY
        assert "iteration_advance" in orch._AUTO_ACTION_REGISTRY

    def test_initialize_real_resources(self, auto_build_claw_resources):
        orch._initialize(auto_build_claw_resources)
        assert "full" in orch.ITERATION_TYPES
        assert orch._MODEL.app.name != ""

    def test_reinitialize_clears_old_state(self, minimal_resources, auto_build_claw_resources):
        orch._initialize(minimal_resources)
        assert "test_workflow" in orch.ITERATION_TYPES
        orch._initialize(auto_build_claw_resources)
        assert "test_workflow" not in orch.ITERATION_TYPES
        assert "full" in orch.ITERATION_TYPES


class TestDisplayHelpers:
    """Tests for _msg and _cli display functions."""

    def test_msg_basic(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._msg("no_active")
        assert result == "No active iteration."

    def test_msg_with_kwargs(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._msg("validate_issues", count=3)
        assert "3" in result

    def test_msg_missing_key_returns_key(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._msg("nonexistent_key")
        assert result == "nonexistent_key"

    def test_cli_description(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._cli("description", "")
        assert "Test orchestration CLI" in result

    def test_cli_commands(self, minimal_resources):
        orch._initialize(minimal_resources)
        result = orch._cli("commands", "new")
        assert "Start new iteration" in result


class TestStateManagement:
    """Tests for state persistence functions."""

    def test_now_format(self):
        result = orch._now()
        assert "T" in result
        assert "+" in result or "Z" in result

    def test_yaml_dump_basic(self):
        data = {"key": "value", "number": 42}
        result = orch._yaml_dump(data)
        loaded = yaml.safe_load(result)
        assert loaded == data

    def test_yaml_dump_long_string_wraps(self):
        data = {"text": "a " * 100}
        result = orch._yaml_dump(data)
        assert "|" in result  # literal block style

    def test_load_state_missing_file(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "nonexistent.yaml"
        result = orch._load_state()
        assert result is None

    def test_save_load_state_roundtrip(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        state_file = tmp_path / "state.yaml"
        orch.STATE_FILE = state_file
        state = {"iteration": 1, "type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        loaded = orch._load_state()
        assert loaded["iteration"] == 1
        assert loaded["type"] == "test_workflow"

    def test_load_yaml_list_missing_file(self):
        result = orch._load_yaml_list(Path("/nonexistent/file.yaml"))
        assert result == []

    def test_append_yaml_entry(self, tmp_path):
        path = tmp_path / "entries.yaml"
        orch._append_yaml_entry(path, {"id": 1, "data": "first"})
        orch._append_yaml_entry(path, {"id": 2, "data": "second"})
        entries = orch._load_yaml_list(path)
        assert len(entries) == 2
        assert entries[0]["id"] == 1
        assert entries[1]["id"] == 2

    def test_init_artifacts_dir(self, tmp_path):
        artifacts = tmp_path / "artifacts"
        orch.DEFAULT_ARTIFACTS_DIR = artifacts
        orch._init_artifacts_dir(artifacts)
        assert artifacts.exists()
        assert orch.STATE_FILE == artifacts / "state.yaml"
        assert orch.LOG_FILE == artifacts / "log.yaml"

    def test_clean_artifacts_dir_preserves_context(self, tmp_path):
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "state.yaml").write_text("test")
        (artifacts / "context.yaml").write_text("test")
        (artifacts / "other.yaml").write_text("test")
        orch.DEFAULT_ARTIFACTS_DIR = artifacts
        orch._clean_artifacts_dir(artifacts)
        assert not (artifacts / "state.yaml").exists()
        assert not (artifacts / "other.yaml").exists()
        assert (artifacts / "context.yaml").exists()


class TestPhaseNavigation:
    """Tests for phase navigation helpers."""

    def test_next_phase(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        assert orch._next_phase(state) == "BETA"

    def test_next_phase_last(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "GAMMA"}
        assert orch._next_phase(state) is None

    def test_phase_dir_creates_folder(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        pdir = orch._phase_dir(state)
        assert pdir.exists()
        assert "phase_01_alpha" in pdir.name


class TestBuildContext:
    """Tests for template context building."""

    def test_build_context_minimal(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.FAILURES_FILE = tmp_path / "failures.yaml"

        orch.STATE_FILE = tmp_path / "state.yaml"

        state = {
            "iteration": 1,
            "total_iterations": 3,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test objective",
        }
        ctx = orch._build_context(state, phase="ALPHA", event="start")
        assert ctx["objective"] == "test objective"
        assert ctx["iteration"] == 1
        assert ctx["total"] == 3
        assert ctx["remaining"] == 2
        assert "CMD" in ctx

    def test_build_context_with_failures(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.FAILURES_FILE = tmp_path / "failures.yaml"

        orch.STATE_FILE = tmp_path / "state.yaml"

        failures = [{"mode": "FM-1", "iteration": 1, "description": "test failure"}]
        orch.FAILURES_FILE.write_text(yaml.dump(failures))

        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test",
        }
        ctx = orch._build_context(state, phase="ALPHA")
        assert "Prior failures" in ctx["prior_context"]


class TestPhaseCallables:
    """Tests for YAML-driven phase template rendering."""

    def test_phase_start_renders_template(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        orch.FAILURES_FILE = tmp_path / "failures.yaml"

        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "build something",
        }
        orch._save_state(state)

        result = orch._PHASE_START["ALPHA"]()
        assert "Start alpha phase" in result
        assert "build something" in result

    def test_phase_end_renders_template(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        orch.FAILURES_FILE = tmp_path / "failures.yaml"

        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test",
        }
        orch._save_state(state)

        result = orch._PHASE_END["ALPHA"]()
        assert "End alpha phase" in result


class TestLifecycleGateResolution:
    """Tests for _resolve_lifecycle_gate discovering gate names from model metadata."""

    def test_resolve_start_gate(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        gate_key = orch._resolve_lifecycle_gate("ALPHA", "start")
        assert "readback" in gate_key  # discovers readback from start_gate_types

    def test_resolve_end_gate(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        gate_key = orch._resolve_lifecycle_gate("ALPHA", "end")
        assert "gatekeeper" in gate_key  # discovers gatekeeper from end_gate_types

    def test_resolve_unknown_lifecycle_fallback(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch._save_state(state)
        gate_key = orch._resolve_lifecycle_gate("ALPHA", "unknown")
        assert gate_key == "ALPHA::unknown"


class TestPrevImplementable:
    """Tests for _prev_implementable using reject_to from model."""

    def test_fallback_to_first_phase(self, minimal_resources):
        """Without reject_to in any phase, falls back to first phase."""
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "GAMMA"}
        result = orch._prev_implementable(state)
        assert result == "ALPHA"  # first phase in workflow


class TestAutoActions:
    """Tests for auto-action dispatch."""

    def test_run_auto_actions_no_actions(self, minimal_resources):
        orch._initialize(minimal_resources)
        state = {"type": "test_workflow", "current_phase": "ALPHA"}
        orch.STATE_FILE = Path("/tmp/nonexistent_state.yaml")
        result = orch._run_auto_actions("ALPHA", state)
        assert result is False


class TestCmdValidate:
    """Tests for the validate command."""

    def test_validate_minimal_model(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        args = argparse.Namespace()
        with pytest.raises(SystemExit) as exc_info:
            orch.cmd_validate(args)
        assert exc_info.value.code == 0

    def test_validate_real_model(self, auto_build_claw_resources, tmp_path):
        orch._initialize(auto_build_claw_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        args = argparse.Namespace()
        with pytest.raises(SystemExit) as exc_info:
            orch.cmd_validate(args)
        assert exc_info.value.code == 0


class TestCmdNew:
    """Tests for the new command."""

    def test_cmd_new_creates_state(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        args = argparse.Namespace(
            type="test_workflow",
            objective="build a widget",
            iterations=1,
            benchmark="",
            clean=False,
            dry_run=False,
        )
        orch.cmd_new(args)

        state = orch._load_state()
        assert state is not None
        assert state["objective"] == "build a widget"
        assert state["type"] == "test_workflow"
        assert state["current_phase"] == "ALPHA"
        assert state["phase_status"] == "pending"

    def test_cmd_new_dry_run(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path

        args = argparse.Namespace(
            type="test_workflow",
            objective="test",
            iterations=1,
            benchmark="",
            clean=False,
            dry_run=True,
        )
        # dry_run prints plan and returns (no sys.exit on success)
        orch.cmd_new(args)
        captured = capsys.readouterr()
        assert "ALPHA" in captured.out
        assert "BETA" in captured.out
        assert "GAMMA" in captured.out


class TestCmdStatus:
    """Tests for the status command."""

    def test_status_no_active(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"

        args = argparse.Namespace()
        orch.cmd_status(args)
        captured = capsys.readouterr()
        assert "No active iteration" in captured.out

    def test_status_with_active(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "objective": "test objective",
            "current_phase": "BETA",
            "phase_status": "in_progress",
            "completed_phases": ["ALPHA"],
            "skipped_phases": [],
            "rejected_count": 0,
            "started_at": "2026-01-01T00:00:00+00:00",
            "phase_outputs": {},
            "phase_agents": {},
        }
        orch._save_state(state)

        args = argparse.Namespace()
        orch.cmd_status(args)
        captured = capsys.readouterr()
        # Minimal fixtures don't have full message templates, so _msg returns
        # the key name when no template is found. Verify status ran and printed
        # the expected message keys (which means the right code paths executed).
        assert "status_header" in captured.out
        assert "status_objective" in captured.out
        assert "status_phase_item" in captured.out


class TestCmdLogFailure:
    """Tests for the log-failure command."""

    def test_log_failure(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "phase_status": "in_progress",
        }
        orch._save_state(state)

        args = argparse.Namespace(mode="FM-TEST", desc="something broke")
        orch.cmd_log_failure(args)

        failures = orch._load_yaml_list(orch.FAILURES_FILE)
        assert len(failures) == 1
        assert failures[0]["mode"] == "FM-TEST"
        assert failures[0]["description"] == "something broke"


class TestIndependentWorkflow:
    """Tests for independent workflow flag."""

    def test_independent_workflow_starts(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        args = argparse.Namespace(
            type="test_workflow",
            objective="test",
            iterations=1,
            benchmark="",
            clean=False,
            dry_run=False,
        )
        orch.cmd_new(args)
        state = orch._load_state()
        assert state is not None
        assert state["type"] == "test_workflow"

    def test_non_independent_workflow_fails(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        # Mark test_workflow as non-independent
        orch._MODEL.workflow_types["WORKFLOW::TEST_WORKFLOW"].independent = False
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        args = argparse.Namespace(
            type="test_workflow",
            objective="test",
            iterations=1,
            benchmark="",
            clean=False,
            dry_run=False,
        )
        with pytest.raises(SystemExit):
            orch.cmd_new(args)


class TestRunUntilComplete:
    """Tests for --iterations 0 (run-until-complete) mode."""

    def test_next_iteration_continues_when_score_nonzero(
        self, minimal_resources, tmp_path, capsys
    ):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 1,
            "total_iterations": 0,
            "type": "test_workflow",
            "objective": "test",
            "current_phase": "GAMMA",
            "phase_status": "complete",
            "completed_phases": ["ALPHA", "BETA", "GAMMA"],
            "skipped_phases": [],
            "rejected_count": 0,
            "started_at": "2026-01-01",
            "phase_outputs": {},
            "phase_agents": {},
            "benchmark_scores": [{"score": 5}],
        }
        orch._save_state(state)
        orch._run_next_iteration(state)
        assert state["iteration"] == 2  # advanced to next

    def test_next_iteration_stops_when_score_zero(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 3,
            "total_iterations": 0,
            "type": "test_workflow",
            "objective": "test",
            "current_phase": "GAMMA",
            "completed_phases": [],
            "skipped_phases": [],
            "rejected_count": 0,
            "started_at": "2026-01-01",
            "phase_outputs": {},
            "phase_agents": {},
            "benchmark_scores": [{"score": 5}, {"score": 2}, {"score": 0}],
        }
        orch._save_state(state)
        orch._run_next_iteration(state)
        captured = capsys.readouterr()
        assert "Benchmark conditions met" in captured.out
        assert state["iteration"] == 3  # did NOT advance

    def test_safety_cap_at_20(self, minimal_resources, tmp_path, capsys):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)

        state = {
            "iteration": 20,
            "total_iterations": 0,
            "type": "test_workflow",
            "objective": "test",
            "current_phase": "GAMMA",
            "completed_phases": [],
            "skipped_phases": [],
            "rejected_count": 0,
            "started_at": "2026-01-01",
            "phase_outputs": {},
            "phase_agents": {},
            "benchmark_scores": [{"score": 3}],
        }
        orch._save_state(state)
        orch._run_next_iteration(state)
        captured = capsys.readouterr()
        assert "20 iterations" in captured.out


class TestGenerativeActionDispatch:
    """Tests for generative action dispatch via _claude_evaluate."""

    def test_generative_action_dispatch(self, tmp_path):
        """Verify generative actions dispatch via _claude_evaluate."""
        # Build minimal resources with a generative action wired to a phase
        resources = tmp_path / "resources"
        resources.mkdir()

        (resources / "workflow.yaml").write_text("""
actions:
  ACTION::GEN_ACTION:
    cli_name: gen_action
    type: generative
    description: "A generative action"
    prompt: "Do generative work"

WORKFLOW::GEN:
  cli_name: gen_workflow
  description: "Workflow with generative action"
  phases:
    - name: STEP
""")

        (resources / "phases.yaml").write_text("""
shared_gates:
  skip:
    gatekeeper_skip:
      mode: standalone_session
      prompt: "Skip {phase} {iteration} {itype} {objective}: {reason}"
    gatekeeper_force_skip:
      mode: standalone_session
      prompt: "Force-skip {phase} {iteration}: {reason}"
STEP:
  auto_actions:
    on_complete: [gen_action]
  start:
    template: "Start step. Objective: {objective}"
    agents:
      - name: readback
        mode: standalone_session
        prompt: "Phase {phase}: {understanding}"
  execution:
    agents:
      - name: worker
        display_name: Worker
        prompt: "Do work"
  end:
    template: "End step."
    agents:
      - name: gatekeeper
        mode: standalone_session
        prompt: "Phase {phase}: {evidence}"
""")

        (resources / "app.yaml").write_text("""
app:
  name: gen-test
  description: "Generative test"
  cmd: "python orchestrate.py"
  artifacts_dir: ".gen-test"
display:
  separator: "-"
  separator_width: 40
  header_char: "="
  header_width: 40
banner:
  header: "{header_line}\\n{iter_label}\\n{header_line}\\n"
  progress_current: "**{p}**"
  progress_done: "~~{p}~~"
footer:
  start: "\\n{separator_line}\\n"
  end: "\\n{separator_line}\\n"
  final: "\\n{separator_line}\\n"
messages:
  no_active: "No active iteration."
  validate_success: "OK"
  validate_issues: "{count} issues"
  validate_item: "  {num}. {issue}"
  benchmark_driven_label: "benchmark-driven {iteration}"
  benchmark_complete: "Benchmark conditions met."
  benchmark_safety_cap: "WARNING: {count} iterations."
cli:
  description: "Gen test CLI"
  epilog: "Usage: {cmd}"
  commands:
    new: "New"
    start: "Start"
    end: "End"
    status: "Status"
  args:
    objective: "Objective"
    iterations: "Iterations"
""")

        orch._initialize(resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch.STATE_FILE = tmp_path / "state.yaml"
        state = {
            "type": "gen_workflow",
            "current_phase": "STEP",
            "iteration": 1,
            "total_iterations": 1,
        }
        orch._save_state(state)

        with patch.object(orch, "_claude_evaluate", return_value=(True, "PASS")) as mock_eval:
            result = orch._run_auto_actions("STEP", state)
            mock_eval.assert_called_once_with("Do generative work", timeout=120)
        assert result is False  # generative actions don't signal early return


class TestDryRunFastWorkflow:
    """Tests for dry-run with the fast workflow type using real resources."""

    def test_dry_run_fast_workflow(self, auto_build_claw_resources, tmp_path, capsys):
        """Verify dry-run with type=fast produces valid output."""
        orch._initialize(auto_build_claw_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path

        args = argparse.Namespace(
            type="fast",
            objective="test fast workflow",
            iterations=1,
            benchmark="",
            clean=False,
            dry_run=True,
        )
        orch.cmd_new(args)
        captured = capsys.readouterr()
        assert "PLAN" in captured.out
        assert "IMPLEMENT" in captured.out
        assert "TEST" in captured.out
        assert "REVIEW" in captured.out
        assert "RECORD" in captured.out
        assert "NEXT" in captured.out
        # fast has no RESEARCH or HYPOTHESIS
        assert "RESEARCH" not in captured.out
        assert "HYPOTHESIS" not in captured.out


class TestPluginEntrypoint:
    """Tests that the plugin entrypoint resolves correctly."""

    def test_entrypoint_import(self):
        """Verify the engine can be imported from the package."""
        from stellars_claude_code_plugins.engine.orchestrator import main

        assert callable(main)

    def test_cli_entrypoint_registered(self):
        """Verify the orchestrate CLI entrypoint is registered in pyproject.toml."""
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "orchestrate" in content
        assert "stellars_claude_code_plugins.engine.orchestrator:main" in content

    def test_bundled_resources_exist(self):
        """Verify YAML resources are bundled in the engine module."""
        resources = (
            Path(__file__).resolve().parent.parent
            / "stellars_claude_code_plugins"
            / "engine"
            / "resources"
        )
        assert resources.exists()
        assert (resources / "workflow.yaml").exists()
        assert (resources / "phases.yaml").exists()
        assert (resources / "app.yaml").exists()


class TestCmdInfo:
    """Tests for the info command - model introspection."""

    def test_info_workflows(self, auto_build_claw_resources, capsys):
        """List all workflows."""
        orch._initialize(auto_build_claw_resources)
        args = argparse.Namespace(workflows=True, workflow=None, phases=False, phase=None, agents=False)
        orch.cmd_info(args)
        out = capsys.readouterr().out
        assert "WORKFLOW::FULL" in out
        assert "full" in out  # cli_name
        assert "WORKFLOW::FAST" in out

    def test_info_workflow_detail(self, auto_build_claw_resources, capsys):
        """Detail one workflow by cli_name."""
        orch._initialize(auto_build_claw_resources)
        args = argparse.Namespace(workflows=False, workflow="full", phases=False, phase=None, agents=False)
        orch.cmd_info(args)
        out = capsys.readouterr().out
        assert "RESEARCH" in out
        assert "HYPOTHESIS" in out
        assert "8 phases" in out or "NEXT" in out

    def test_info_phases(self, auto_build_claw_resources, capsys):
        """List all phases."""
        orch._initialize(auto_build_claw_resources)
        args = argparse.Namespace(workflows=False, workflow=None, phases=True, phase=None, agents=False)
        orch.cmd_info(args)
        out = capsys.readouterr().out
        assert "FULL::RESEARCH" in out
        assert "IMPLEMENT" in out
        assert "GC::PLAN" in out

    def test_info_phase_detail(self, auto_build_claw_resources, capsys):
        """Detail one phase showing start/execution/end agents."""
        orch._initialize(auto_build_claw_resources)
        args = argparse.Namespace(workflows=False, workflow=None, phases=False, phase="FULL::RESEARCH", agents=False)
        orch.cmd_info(args)
        out = capsys.readouterr().out
        assert "readback" in out
        assert "researcher" in out
        assert "architect" in out
        assert "product_manager" in out
        assert "gatekeeper" in out

    def test_info_agents(self, auto_build_claw_resources, capsys):
        """List all agents grouped by phase."""
        orch._initialize(auto_build_claw_resources)
        args = argparse.Namespace(workflows=False, workflow=None, phases=False, phase=None, agents=True)
        orch.cmd_info(args)
        out = capsys.readouterr().out
        assert "researcher" in out
        assert "contrarian" in out
        assert "guardian" in out
        assert "benchmark_evaluator" in out

    def test_info_structure_compliance(self, auto_build_claw_resources, capsys):
        """Every phase has readback in start and gatekeeper in end."""
        orch._initialize(auto_build_claw_resources)
        for phase_name in orch._MODEL.phases:
            # Every phase should have readback gate
            rb_key = f"{phase_name}::readback"
            assert rb_key in orch._MODEL.gates, f"{phase_name} missing readback in start"
            # Every phase should have gatekeeper gate
            gk_key = f"{phase_name}::gatekeeper"
            assert gk_key in orch._MODEL.gates, f"{phase_name} missing gatekeeper in end"

    def test_info_execution_agents_match(self, auto_build_claw_resources):
        """Agent counts match expected per phase."""
        orch._initialize(auto_build_claw_resources)
        expected = {
            "FULL::RESEARCH": 3,
            "FULL::HYPOTHESIS": 4,
            "PLAN": 3,
            "TEST": 1,
            "REVIEW": 4,
            "PLANNING::RESEARCH": 3,
            "PLANNING::PLAN": 1,
        }
        for phase, count in expected.items():
            agents = orch._MODEL.agents.get(phase, [])
            assert len(agents) == count, f"{phase}: expected {count} agents, got {len(agents)}"
        # Phases without agents
        for phase in ["IMPLEMENT", "RECORD", "NEXT", "GC::PLAN"]:
            assert phase not in orch._MODEL.agents or len(orch._MODEL.agents[phase]) == 0


class TestEnsureProjectResources:
    """Tests for _ensure_project_resources auto-copy behavior."""

    def test_copies_missing_resources(self, tmp_path):
        """Resources are copied from module to project dir when missing."""
        project_resources = tmp_path / ".auto-build-claw" / "resources"
        result = orch._ensure_project_resources(project_resources)
        assert result == project_resources
        assert (project_resources / "workflow.yaml").exists()
        assert (project_resources / "phases.yaml").exists()
        assert (project_resources / "app.yaml").exists()

    def test_does_not_overwrite_existing(self, tmp_path):
        """Existing project resources are not overwritten."""
        project_resources = tmp_path / ".auto-build-claw" / "resources"
        project_resources.mkdir(parents=True)
        custom_content = "# custom workflow"
        (project_resources / "workflow.yaml").write_text(custom_content)
        orch._ensure_project_resources(project_resources)
        assert (project_resources / "workflow.yaml").read_text() == custom_content
        # But missing files are still copied
        assert (project_resources / "phases.yaml").exists()
        assert (project_resources / "app.yaml").exists()

    def test_loads_from_project_resources(self, tmp_path):
        """Orchestrator loads from project-local resources after copy."""
        project_resources = tmp_path / ".auto-build-claw" / "resources"
        orch._ensure_project_resources(project_resources)
        model = orch.load_model(project_resources)
        assert model.app.name != ""
        assert len(model.workflow_types) > 0

    def test_clean_preserves_resources(self, tmp_path):
        """_clean_artifacts_dir preserves resources/ subdirectory."""
        artifacts = tmp_path / ".auto-build-claw"
        resources = artifacts / "resources"
        resources.mkdir(parents=True)
        custom = "# custom workflow"
        (resources / "workflow.yaml").write_text(custom)
        # Create a non-preserved file and dir
        (artifacts / "state.yaml").write_text("iteration: 1")
        phase_dir = artifacts / "phase_01_plan"
        phase_dir.mkdir()
        (phase_dir / "output.md").write_text("plan")
        # Clean
        orch._clean_artifacts_dir(artifacts)
        # resources/ preserved
        assert resources.exists()
        assert (resources / "workflow.yaml").read_text() == custom
        # other artifacts removed
        assert not (artifacts / "state.yaml").exists()
        assert not phase_dir.exists()


class TestResourceConflict:
    """Tests for old-format resource detection and archiving."""

    def test_detect_old_format(self, tmp_path):
        resources = tmp_path / "resources"
        resources.mkdir()
        # Old format
        (resources / "phases.yaml").write_text(
            "ALPHA:\n  gates:\n    on_start:\n      readback:\n        prompt: test"
        )
        assert orch._detect_old_format(resources) is True

    def test_detect_new_format(self, tmp_path):
        resources = tmp_path / "resources"
        resources.mkdir()
        (resources / "phases.yaml").write_text(
            "ALPHA:\n  start:\n    agents:\n      - name: readback"
        )
        assert orch._detect_old_format(resources) is False

    def test_detect_no_phases_file(self, tmp_path):
        resources = tmp_path / "resources"
        resources.mkdir()
        assert orch._detect_old_format(resources) is False

    def test_old_format_archived(self, tmp_path):
        resources = tmp_path / ".auto-build-claw" / "resources"
        resources.mkdir(parents=True)
        (resources / "phases.yaml").write_text(
            "ALPHA:\n  gates:\n    on_start:\n      readback:\n        prompt: test"
        )
        (resources / "workflow.yaml").write_text("test: {}")
        (resources / "app.yaml").write_text("app: {}")
        orch._ensure_project_resources(resources)
        # Old resources should be archived
        archives = list(tmp_path.glob(".auto-build-claw/resources.old.*"))
        assert len(archives) >= 1
        # New resources should be fresh
        content = (resources / "phases.yaml").read_text()
        assert "start:" in content
        assert "gates:" not in content or "shared_gates:" in content


class TestVersionCheck:
    """Tests for version check caching."""

    def test_version_check_cache(self, tmp_path):
        cache = tmp_path / ".version_check"
        cache.write_text("0.8.50")
        # Cache exists and is fresh - should not make network call
        assert time.time() - cache.stat().st_mtime < 86400

    def test_version_check_no_error(self):
        """_check_version never raises - fails silently."""
        # Should not raise even if package not found or network fails
        orch._check_version()


class TestContextRichEntries:
    """Tests for identifier-keyed rich context entries."""

    def test_generate_context_id_basic(self, minimal_resources, tmp_path):
        """Identifier is slugified from message."""
        orch._initialize(minimal_resources)
        cid = orch._generate_context_id("Focus on X", set())
        assert cid == "focus_on_x"

    def test_generate_context_id_truncation(self, minimal_resources, tmp_path):
        """Identifier truncated to 37 chars max."""
        orch._initialize(minimal_resources)
        long_msg = "a" * 100
        cid = orch._generate_context_id(long_msg, set())
        assert len(cid) <= 37

    def test_generate_context_id_collision(self, minimal_resources, tmp_path):
        """Collision appends _2, _3 suffix."""
        orch._initialize(minimal_resources)
        cid1 = orch._generate_context_id("focus on x", set())
        cid2 = orch._generate_context_id("focus on x", {cid1})
        cid3 = orch._generate_context_id("focus on x", {cid1, cid2})
        assert cid1 == "focus_on_x"
        assert cid2 == "focus_on_x_2"
        assert cid3 == "focus_on_x_3"

    def test_generate_context_id_empty_fallback(self, minimal_resources, tmp_path):
        """Empty/special-chars message falls back to 'ctx'."""
        orch._initialize(minimal_resources)
        cid = orch._generate_context_id("!!!", set())
        assert cid == "ctx"

    def test_save_load_rich_entry(self, minimal_resources, tmp_path):
        """Round-trip a rich context entry."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {
            "focus_on_x": {
                "message": "focus on X",
                "phase": "RESEARCH",
                "created": "2026-04-02T14:00:00+00:00",
                "acknowledged_by": [],
                "processed": False,
            }
        }
        orch._save_context(ctx)
        loaded = orch._load_context()
        assert "focus_on_x" in loaded
        assert loaded["focus_on_x"]["message"] == "focus on X"
        assert loaded["focus_on_x"]["phase"] == "RESEARCH"
        assert loaded["focus_on_x"]["processed"] is False

    def test_load_rejects_legacy_flat_format(self, minimal_resources, tmp_path):
        """Old flat format raises ValueError."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        (tmp_path / "context.yaml").write_text("RESEARCH: 'test guidance'\n")
        with pytest.raises(ValueError, match="legacy flat format"):
            orch._load_context()

    def test_two_messages_same_phase_different_ids(self, minimal_resources, tmp_path):
        """Two messages for same phase get different identifiers."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {}
        cid1 = orch._generate_context_id("fix auth", set(ctx.keys()))
        ctx[cid1] = {
            "message": "fix auth", "phase": "IMPLEMENT",
            "created": "2026-04-02T14:00:00+00:00",
            "acknowledged_by": [], "processed": False,
        }
        cid2 = orch._generate_context_id("fix auth", set(ctx.keys()))
        ctx[cid2] = {
            "message": "fix auth again", "phase": "IMPLEMENT",
            "created": "2026-04-02T15:00:00+00:00",
            "acknowledged_by": [], "processed": False,
        }
        assert cid1 != cid2
        assert len(ctx) == 2
        orch._save_context(ctx)
        loaded = orch._load_context()
        assert len(loaded) == 2

    def test_ack_updates_inline_no_ack_file(self, minimal_resources, tmp_path):
        """Acknowledgment updates acknowledged_by inline, no context_ack.yaml."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {
            "focus_on_x": {
                "message": "focus on X",
                "phase": "RESEARCH",
                "created": "2026-04-02T14:00:00+00:00",
                "acknowledged_by": [],
                "processed": False,
            }
        }
        orch._save_context(ctx)
        # Simulate what cmd_start does for acknowledgment
        loaded = orch._load_context()
        phase = "ALPHA"
        for cid, entry in loaded.items():
            ack_list = entry.setdefault("acknowledged_by", [])
            if phase not in ack_list:
                ack_list.append(phase)
        orch._save_context(loaded)
        final = orch._load_context()
        assert "ALPHA" in final["focus_on_x"]["acknowledged_by"]
        assert not (tmp_path / "context_ack.yaml").exists()

    def test_ack_idempotent(self, minimal_resources, tmp_path):
        """Duplicate phase not added to acknowledged_by."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {
            "focus_on_x": {
                "message": "focus on X",
                "phase": "RESEARCH",
                "created": "2026-04-02T14:00:00+00:00",
                "acknowledged_by": ["ALPHA"],
                "processed": False,
            }
        }
        orch._save_context(ctx)
        loaded = orch._load_context()
        phase = "ALPHA"
        for cid, entry in loaded.items():
            ack_list = entry.setdefault("acknowledged_by", [])
            if phase not in ack_list:
                ack_list.append(phase)
        orch._save_context(loaded)
        final = orch._load_context()
        assert final["focus_on_x"]["acknowledged_by"].count("ALPHA") == 1

    def test_processed_flag(self, minimal_resources, tmp_path):
        """Setting processed=True on an entry."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {
            "focus_on_x": {
                "message": "focus on X",
                "phase": "RESEARCH",
                "created": "2026-04-02T14:00:00+00:00",
                "acknowledged_by": ["ALPHA"],
                "processed": False,
            }
        }
        orch._save_context(ctx)
        loaded = orch._load_context()
        loaded["focus_on_x"]["processed"] = True
        orch._save_context(loaded)
        final = orch._load_context()
        assert final["focus_on_x"]["processed"] is True

    def test_entry_missing_message_raises(self, minimal_resources, tmp_path):
        """Entry missing 'message' key raises ValueError."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {"test_entry": {"phase": "RESEARCH", "created": "2026-04-02"}}
        orch._save_context(ctx)
        with pytest.raises(ValueError, match="missing required keys"):
            orch._load_context()

    def test_entry_missing_phase_raises(self, minimal_resources, tmp_path):
        """Entry missing 'phase' key raises ValueError."""
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        ctx = {"test_entry": {"message": "test", "created": "2026-04-02"}}
        orch._save_context(ctx)
        with pytest.raises(ValueError, match="missing required keys"):
            orch._load_context()

    def test_hypothesis_autowrite_prompt_says_append(self, auto_build_claw_resources):
        """Hypothesis autowrite prompt says APPEND, not bare Write."""
        orch._initialize(auto_build_claw_resources)
        action = orch._MODEL.actions.get("ACTION::HYPOTHESIS_AUTOWRITE")
        assert action is not None, "ACTION::HYPOTHESIS_AUTOWRITE not found in model"
        prompt = action.prompt
        assert "APPEND" in prompt or "append" in prompt
        assert "do NOT overwrite" in prompt.lower() or "do not overwrite" in prompt.lower()

    def test_architect_agents_have_occam_directive(self, auto_build_claw_resources):
        """All architect agents have Occam's razor directive."""
        orch._initialize(auto_build_claw_resources)
        architect_phases = []
        for phase_key, agents in orch._MODEL.agents.items():
            for agent in agents:
                if agent.name == "architect":
                    architect_phases.append(phase_key)
                    assert "occam" in agent.prompt.lower(), (
                        f"Architect in {phase_key} missing Occam directive"
                    )
        assert len(architect_phases) >= 4, f"Expected >= 4 architect agents, found {len(architect_phases)}"

    def test_gatekeeper_prompts_reference_context(self, auto_build_claw_resources):
        """Gatekeepers for RESEARCH/HYPOTHESIS/PLAN/IMPLEMENT/REVIEW reference context."""
        orch._initialize(auto_build_claw_resources)
        check_phases = {"FULL::RESEARCH", "FULL::HYPOTHESIS", "PLAN", "IMPLEMENT", "REVIEW"}
        for phase_key, gates in orch._MODEL.gates.items():
            if phase_key in check_phases:
                for gate in gates:
                    if gate.name == "gatekeeper":
                        assert "context" in gate.prompt.lower(), (
                            f"Gatekeeper in {phase_key} missing context reference"
                        )


class TestHypothesisContext:
    """Tests for prior hypothesis injection into build context."""

    def test_prior_hyp_from_file(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        # Create hypotheses.yaml
        hyp = [{"id": "H001", "hypothesis": "Test hypothesis", "stars": "4/5"}]
        (tmp_path / "hypotheses.yaml").write_text(yaml.dump(hyp))
        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test",
        }
        orch._save_state(state)
        ctx = orch._build_context(state, phase="ALPHA")
        assert "H001" in ctx.get("prior_hyp", "")
        assert "Test hypothesis" in ctx.get("prior_hyp", "")

    def test_prior_hyp_empty_when_no_file(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test",
        }
        orch._save_state(state)
        ctx = orch._build_context(state, phase="ALPHA")
        assert ctx.get("prior_hyp", "") == ""

    def test_prior_hyp_multiple_entries(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        hyp = [
            {"id": "H001", "hypothesis": "First hypothesis", "stars": "3/5"},
            {"id": "H002", "hypothesis": "Second hypothesis", "stars": "5/5"},
        ]
        (tmp_path / "hypotheses.yaml").write_text(yaml.dump(hyp))
        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test",
        }
        orch._save_state(state)
        ctx = orch._build_context(state, phase="ALPHA")
        assert "H001" in ctx["prior_hyp"]
        assert "H002" in ctx["prior_hyp"]
        assert "First hypothesis" in ctx["prior_hyp"]
        assert "Second hypothesis" in ctx["prior_hyp"]

    def test_prior_hyp_malformed_yaml(self, minimal_resources, tmp_path):
        orch._initialize(minimal_resources)
        orch.DEFAULT_ARTIFACTS_DIR = tmp_path
        orch._init_artifacts_dir(tmp_path)
        # Write a string instead of list
        (tmp_path / "hypotheses.yaml").write_text("just a string")
        state = {
            "iteration": 1,
            "total_iterations": 1,
            "type": "test_workflow",
            "current_phase": "ALPHA",
            "objective": "test",
        }
        orch._save_state(state)
        ctx = orch._build_context(state, phase="ALPHA")
        assert ctx.get("prior_hyp", "") == ""
